"""
Persistent Memory & Checkpointing Module

Implements SqliteSaver for state persistence and thread-based session recovery.
Enables agent to remember conversations across sessions and application restarts.

Lab 5 Requirements:
- Checkpointer implementation: SqliteSaver
- Thread ID support for session identification
- State save/load on each graph execution
- Recovery of previous sessions
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    # Preferred: SqliteSaver for persistent checkpoints
    from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore
    CHECKPOINTER_TYPE = "sqlite"
except Exception:
    # Fallback to in-memory saver provided by langgraph
    try:
        from langgraph.checkpoint.memory import MemorySaver as SqliteSaver  # type: ignore
        CHECKPOINTER_TYPE = "memory"
    except Exception:
        SqliteSaver = None  # type: ignore
        CHECKPOINTER_TYPE = "none"

from langgraph.graph import StateGraph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PersistentMemoryManager:
    """Manages persistent state storage using SQLiteSaver"""

    def __init__(self, db_path: str = "./checkpoint_db.sqlite"):
        """
        Initialize persistent memory manager

        Args:
            db_path: Path to SQLite database for checkpoints
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create checkpointer (prefer sqlite; fall back to memory saver)
        if SqliteSaver is None:
            logger.warning("⚠ No compatible checkpointer found in langgraph; persistence disabled.")
            self.checkpointer = None
        else:
            try:
                if CHECKPOINTER_TYPE == "sqlite":
                    # SqliteSaver expects a file path
                    self.checkpointer = SqliteSaver(str(self.db_path))
                else:
                    # MemorySaver does not take a path
                    try:
                        self.checkpointer = SqliteSaver()
                    except TypeError:
                        # Some implementations may accept a path; try anyway
                        self.checkpointer = SqliteSaver(str(self.db_path))

                logger.info(f"✓ Persistent Memory initialized ({CHECKPOINTER_TYPE})")
                if CHECKPOINTER_TYPE == "sqlite":
                    logger.info(f"  Database: {self.db_path}")
                logger.info(f"  Status: Ready for checkpoint saving")
            except Exception as e:
                logger.warning(f"✗ Failed to initialize checkpointer: {e}")
                self.checkpointer = None

    def get_checkpointer(self) -> SqliteSaver:
        """Get the checkpointer instance for graph compilation"""
        return self.checkpointer

    def list_sessions(self) -> list:
        """
        List all saved session thread IDs

        Returns:
            List of thread IDs that have saved checkpoints
        """
        # If using sqlite checkpointer, try to read directly from DB file
        if CHECKPOINTER_TYPE == "sqlite" and self.db_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()

                # Query unique thread IDs from checkpoints
                cursor.execute("""
                    SELECT DISTINCT thread_id FROM checkpoints
                    ORDER BY created_ts DESC
                """)

                sessions = [row[0] for row in cursor.fetchall()]
                conn.close()

                logger.info(f"✓ Found {len(sessions)} saved sessions")
                return sessions
            except Exception as e:
                logger.warning(f"⚠ Could not list sessions from sqlite DB: {e}")

        # If using a memory saver, try to inspect it if possible
        try:
            if self.checkpointer is None:
                return []

            # MemorySaver may expose a method or attribute to list checkpoints
            if hasattr(self.checkpointer, "list_checkpoints"):
                return list(self.checkpointer.list_checkpoints())
            if hasattr(self.checkpointer, "_store"):
                # internal dict-like store
                try:
                    return list(self.checkpointer._store.keys())
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"⚠ Could not list sessions from checkpointer: {e}")

        return []

    def get_session_info(self, thread_id: str) -> Dict[str, Any]:
        """
        Get metadata about a saved session

        Args:
            thread_id: Thread ID to retrieve

        Returns:
            Dictionary with session metadata
        """
        # If sqlite-based checkpointer is available, read from DB
        if CHECKPOINTER_TYPE == "sqlite" and self.db_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT checkpoint, created_ts, updated_ts
                    FROM checkpoints
                    WHERE thread_id = ?
                    ORDER BY created_ts DESC
                    LIMIT 1
                """, (thread_id,))

                row = cursor.fetchone()
                conn.close()

                if row:
                    return {
                        "thread_id": thread_id,
                        "checkpoint": row[0],
                        "created": row[1],
                        "updated": row[2],
                        "status": "Recoverable"
                    }
                else:
                    return {"thread_id": thread_id, "status": "Not found"}
            except Exception as e:
                logger.warning(f"⚠ Error retrieving session info from sqlite: {e}")

        # If using memory saver, attempt to extract info if supported
        try:
            if self.checkpointer is None:
                return {"thread_id": thread_id, "status": "Persistence unavailable"}

            # Try common method names for getting a checkpoint
            for method in ("get", "get_checkpoint", "load_checkpoint", "read_checkpoint"):
                if hasattr(self.checkpointer, method):
                    try:
                        cp = getattr(self.checkpointer, method)(thread_id)
                        return {"thread_id": thread_id, "checkpoint": cp, "status": "Recoverable"}
                    except Exception:
                        continue

        except Exception as e:
            logger.warning(f"⚠ Error retrieving session info from checkpointer: {e}")

        return {"thread_id": thread_id, "status": "Not found or unsupported"}

    def clear_session(self, thread_id: str) -> bool:
        """
        Clear checkpoints for a specific thread ID

        Args:
            thread_id: Thread ID to clear

        Returns:
            True if successful, False otherwise
        """
        # If sqlite-based, delete from DB
        if CHECKPOINTER_TYPE == "sqlite" and self.db_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()

                cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
                conn.commit()
                conn.close()

                logger.info(f"✓ Cleared session: {thread_id}")
                return True
            except Exception as e:
                logger.warning(f"⚠ Error clearing session from sqlite: {e}")

        # If memory saver, try to remove entry
        try:
            if self.checkpointer is None:
                return False
            if hasattr(self.checkpointer, "delete"):
                try:
                    getattr(self.checkpointer, "delete")(thread_id)
                    return True
                except Exception:
                    pass
            if hasattr(self.checkpointer, "_store"):
                try:
                    del self.checkpointer._store[thread_id]
                    return True
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"⚠ Error clearing session from checkpointer: {e}")

        return False


class HighRiskActionIdentifier:
    """Identifies and tracks high-risk actions requiring human approval"""

    # High-risk action patterns
    HIGH_RISK_ACTIONS = {
        "delete": {
            "patterns": ["delete", "rm ", "DROP TABLE", "TRUNCATE"],
            "risk_level": "critical",
            "description": "Data deletion - irreversible"
        },
        "restart": {
            "patterns": ["restart", "stop", "shutdown", "kill -9"],
            "risk_level": "high",
            "description": "Service/process termination"
        },
        "modify_permissions": {
            "patterns": ["chmod", "chown", "sudo visudo", "usermod"],
            "risk_level": "high",
            "description": "Security permission changes"
        },
        "external_call": {
            "patterns": ["curl", "wget", "POST", "API call"],
            "risk_level": "high",
            "description": "External API/network calls"
        },
        "config_change": {
            "patterns": ["edit", "modify", "config", "nginx.conf"],
            "risk_level": "medium",
            "description": "System configuration modification"
        }
    }

    @classmethod
    def is_high_risk(cls, action_text: str) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if an action is high-risk and requires human approval

        Args:
            action_text: The proposed action command or description

        Returns:
            Tuple of (is_risky: bool, risk_info: Optional[Dict])
        """
        action_lower = action_text.lower()

        for action_type, config in cls.HIGH_RISK_ACTIONS.items():
            for pattern in config["patterns"]:
                if pattern.lower() in action_lower:
                    return True, {
                        "action_type": action_type,
                        "risk_level": config["risk_level"],
                        "description": config["description"],
                        "action": action_text,
                        "requires_human_approval": True
                    }

        return False, None

    @classmethod
    def get_risk_level(cls, action_text: str) -> str:
        """Get risk level for an action"""
        is_risky, info = cls.is_high_risk(action_text)
        if is_risky:
            return info["risk_level"]
        return "low"


class HITLInterruptionHandler:
    """Manages HITL interruption checkpoints and approval workflow"""

    def __init__(self, memory_manager: PersistentMemoryManager):
        """
        Initialize HITL handler

        Args:
            memory_manager: PersistentMemoryManager instance
        """
        self.memory_manager = memory_manager
        self.pending_approvals = {}  # thread_id -> {action, timestamp, state}

        logger.info("✓ HITL Interruption Handler initialized")

    def request_approval(
        self,
        thread_id: str,
        action: str,
        proposed_state: Dict[str, Any],
        risk_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Request human approval before executing high-risk action

        Args:
            thread_id: Session thread ID
            action: Action to be executed
            proposed_state: Full state at interruption point
            risk_info: Risk assessment information

        Returns:
            Dictionary with approval request details
        """
        approval_request = {
            "thread_id": thread_id,
            "timestamp": datetime.now().isoformat(),
            "action_type": risk_info.get("action_type"),
            "risk_level": risk_info.get("risk_level"),
            "description": risk_info.get("description"),
            "proposed_action": action,
            "full_state": proposed_state,
            "status": "WAITING_FOR_APPROVAL",
            "editable": True,  # User can edit before approval
        }

        self.pending_approvals[thread_id] = approval_request

        logger.warning("⚠ ┌─ HIGH-RISK ACTION DETECTED")
        logger.warning(f"⚠ │  Action Type: {approval_request['action_type']}")
        logger.warning(f"⚠ │  Risk Level: {approval_request['risk_level']}")
        logger.warning(f"⚠ │  Description: {approval_request['description']}")
        logger.warning(f"⚠ │  Status: AWAITING HUMAN APPROVAL")
        logger.warning("⚠ └─ Use handle_approval() to proceed")

        return approval_request

    def handle_approval(
        self,
        thread_id: str,
        approved: bool,
        edited_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle human approval/rejection of high-risk action

        Args:
            thread_id: Session thread ID
            approved: Whether action was approved
            edited_action: Optional edited version of action

        Returns:
            Result dictionary
        """
        if thread_id not in self.pending_approvals:
            return {
                "status": "error",
                "message": f"No pending approval for thread: {thread_id}"
            }

        approval = self.pending_approvals[thread_id]

        if approved:
            action_to_execute = edited_action or approval["proposed_action"]

            result = {
                "status": "✓ APPROVED",
                "thread_id": thread_id,
                "action_type": approval["action_type"],
                "original_action": approval["proposed_action"],
                "executed_action": action_to_execute,
                "edited": edited_action is not None,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info("✓ ┌─ ACTION APPROVED BY HUMAN")
            logger.info(f"✓ │  Action Type: {approval['action_type']}")
            logger.info(f"✓ │  Original: {approval['proposed_action'][:60]}...")
            if edited_action:
                logger.info(f"✓ │  Edited:   {edited_action[:60]}...")
            logger.info(f"✓ │  Status: EXECUTING NOW")
            logger.info("✓ └─ Proceeding with execution")

        else:
            result = {
                "status": "✗ REJECTED",
                "thread_id": thread_id,
                "action_type": approval["action_type"],
                "proposed_action": approval["proposed_action"],
                "reason": "Human rejected execution",
                "timestamp": datetime.now().isoformat(),
            }

            logger.warning("✗ ┌─ ACTION REJECTED BY HUMAN")
            logger.warning(f"✗ │  Action Type: {approval['action_type']}")
            logger.warning(f"✗ │  Status: EXECUTION CANCELLED")
            logger.warning("✗ └─ Continuing without high-risk operation")

        # Clean up
        del self.pending_approvals[thread_id]

        return result


# Global instances
_memory_manager: Optional[PersistentMemoryManager] = None
_hitl_handler: Optional[HITLInterruptionHandler] = None


def init_persistent_memory(db_path: str = "./checkpoint_db.sqlite"):
    """Initialize persistent memory and HITL systems"""
    global _memory_manager, _hitl_handler

    _memory_manager = PersistentMemoryManager(db_path)
    _hitl_handler = HITLInterruptionHandler(_memory_manager)

    logger.info("✓ Persistent memory system initialized")
    logger.info("✓ HITL interruption handler ready")


def get_memory_manager() -> PersistentMemoryManager:
    """Get the persistent memory manager instance"""
    if _memory_manager is None:
        raise RuntimeError("Memory system not initialized. Call init_persistent_memory() first.")
    return _memory_manager


def get_hitl_handler() -> HITLInterruptionHandler:
    """Get the HITL handler instance"""
    if _hitl_handler is None:
        raise RuntimeError("HITL handler not initialized. Call init_persistent_memory() first.")
    return _hitl_handler
