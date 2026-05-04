"""
Approval Logic & Safety Mechanism Configuration

High-Risk Action Interruption & Human-in-the-Loop Implementation
Implements safety checkpoints before executing critical operations.

Lab 5 Requirement: Demonstrate that a human can approve/reject and edit
proposed actions before execution.
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class ActionRiskLevel(Enum):
    """Risk severity levels for actions"""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalWorkflow:
    """
    Manages the complete approval workflow for high-risk actions

    Flow:
    1. Agent proposes action
    2. Risk assessment check
    3. If high-risk: Request human approval
    4. Human: Review, potentially edit
    5. Human: Approve or reject
    6. Proceed or abort based on decision
    """

    # Action categories and their required approval levels
    APPROVAL_REQUIREMENTS = {
        "data_deletion": {
            "actions": ["delete", "drop", "truncate", "rm -rf", "remove"],
            "risk_level": ActionRiskLevel.CRITICAL,
            "requires_approval": True,
            "requires_confirmation": True,
            "allows_edit": True,
            "timeout_minutes": 30,
            "description": "Irreversible data deletion operations"
        },
        "service_restart": {
            "actions": ["restart", "stop", "shutdown", "kill -9", "systemctl stop"],
            "risk_level": ActionRiskLevel.HIGH,
            "requires_approval": True,
            "requires_confirmation": False,
            "allows_edit": True,
            "timeout_minutes": 15,
            "description": "Service or process termination"
        },
        "permission_change": {
            "actions": ["chmod", "chown", "sudo visudo", "usermod"],
            "risk_level": ActionRiskLevel.HIGH,
            "requires_approval": True,
            "requires_confirmation": False,
            "allows_edit": True,
            "timeout_minutes": 20,
            "description": "System permission modifications"
        },
        "external_api_call": {
            "actions": ["curl", "wget", "POST", "api_call", "http_request"],
            "risk_level": ActionRiskLevel.HIGH,
            "requires_approval": True,
            "requires_confirmation": False,
            "allows_edit": True,
            "timeout_minutes": 10,
            "description": "External API or network calls"
        },
        "config_modification": {
            "actions": ["edit", "modify", "update", ".conf", ".yaml", ".json"],
            "risk_level": ActionRiskLevel.MEDIUM,
            "requires_approval": True,
            "requires_confirmation": False,
            "allows_edit": True,
            "timeout_minutes": 15,
            "description": "System configuration changes"
        }
    }

    def __init__(self):
        """Initialize approval workflow manager"""
        logger.info("✓ Approval Workflow initialized")
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}

    def assess_risk(self, action: str) -> Dict[str, Any]:
        """
        Assess risk level of a proposed action

        Args:
            action: The action to assess

        Returns:
            Risk assessment dictionary
        """
        action_lower = action.lower()
        risk_assessment = {
            "action": action,
            "risk_level": ActionRiskLevel.SAFE,
            "action_category": None,
            "requires_approval": False,
            "allows_edit": False,
            "reason": "No high-risk patterns detected"
        }

        # Check against known high-risk patterns
        for category, config in self.APPROVAL_REQUIREMENTS.items():
            for pattern in config["actions"]:
                if pattern.lower() in action_lower:
                    risk_assessment.update({
                        "risk_level": config["risk_level"],
                        "action_category": category,
                        "requires_approval": config["requires_approval"],
                        "allows_edit": config["allows_edit"],
                        "requires_confirmation": config["requires_confirmation"],
                        "timeout_minutes": config["timeout_minutes"],
                        "description": config["description"],
                        "reason": f"Matches pattern: {pattern}"
                    })
                    break

        return risk_assessment

    def create_approval_request(
        self,
        thread_id: str,
        action: str,
        risk_assessment: Dict[str, Any],
        full_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an approval request for human review

        Args:
            thread_id: Session identifier
            action: Proposed action
            risk_assessment: Risk assessment results
            full_state: Full agent state

        Returns:
            Approval request object
        """
        approval_request = {
            "approval_id": f"appr_{thread_id}_{len(self.pending_approvals)}",
            "thread_id": thread_id,
            "action_original": action,
            "action_edited": None,
            "risk_level": risk_assessment["risk_level"].value,
            "action_category": risk_assessment["action_category"],
            "description": risk_assessment.get("description", ""),
            "requires_confirmation": risk_assessment.get("requires_confirmation", False),
            "allows_edit": risk_assessment.get("allows_edit", False),
            "timeout_minutes": risk_assessment.get("timeout_minutes", 30),
            "status": "AWAITING_APPROVAL",
            "full_state": full_state,
            "human_notes": "",
            "decision": None,
            "decision_timestamp": None,
        }

        self.pending_approvals[thread_id] = approval_request

        logger.warning("⚠"*35)
        logger.warning(f"⚠ HIGH-RISK ACTION DETECTED - AWAITING HUMAN APPROVAL")
        logger.warning(f"⚠ Approval ID: {approval_request['approval_id']}")
        logger.warning(f"⚠ Risk Level: {approval_request['risk_level']}")
        logger.warning(f"⚠ Category: {approval_request['action_category']}")
        logger.warning(f"⚠ Action: {action[:70]}...")
        logger.warning(f"⚠ Timeout: {approval_request['timeout_minutes']} minutes")
        logger.warning("⚠"*35)

        return approval_request

    def submit_human_approval(
        self,
        thread_id: str,
        approved: bool,
        edited_action: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process human approval/rejection

        Args:
            thread_id: Session identifier
            approved: Whether action was approved
            edited_action: Optional edited version of action
            notes: Human notes on decision

        Returns:
            Approval result
        """
        if thread_id not in self.pending_approvals:
            return {
                "status": "error",
                "message": f"No pending approval for thread: {thread_id}"
            }

        request = self.pending_approvals[thread_id]

        if approved:
            status = "✓ APPROVED"
            decision = "APPROVED"

            if edited_action:
                logger.info(f"✓ Action APPROVED with EDITS by human")
                logger.info(f"  Original: {request['action_original'][:60]}...")
                logger.info(f"  Edited:   {edited_action[:60]}...")
                request["action_edited"] = edited_action
            else:
                logger.info(f"✓ Action APPROVED without edits by human")

        else:
            status = "✗ REJECTED"
            decision = "REJECTED"
            logger.warning(f"✗ Action REJECTED by human")
            if notes:
                logger.warning(f"  Reason: {notes}")

        result = {
            "approval_id": request["approval_id"],
            "thread_id": thread_id,
            "status": status,
            "decision": decision,
            "original_action": request["action_original"],
            "executed_action": edited_action or request["action_original"],
            "edited": edited_action is not None,
            "notes": notes or "",
            "action_category": request["action_category"],
        }

        # Update request
        request["status"] = decision
        request["decision"] = decision
        request["human_notes"] = notes or ""
        request["decision_timestamp"] = "2026-03-08T10:45:33Z"  # Would use actual timestamp

        return result

    def can_edit_action(self, thread_id: str) -> bool:
        """Check if action can be edited by human"""
        if thread_id not in self.pending_approvals:
            return False
        return self.pending_approvals[thread_id]["allows_edit"]

    def get_pending_approval(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get pending approval for a thread"""
        return self.pending_approvals.get(thread_id)

    def list_pending_approvals(self) -> List[Dict[str, Any]]:
        """List all pending approvals"""
        return list(self.pending_approvals.values())

    def clear_approval(self, thread_id: str) -> bool:
        """Clear approval after decision"""
        if thread_id in self.pending_approvals:
            del self.pending_approvals[thread_id]
            return True
        return False


class SafetyInterruptionHandler:
    """Handles safety interruption checkpoints in agent workflow"""

    def __init__(self):
        """Initialize safety handler"""
        self.approval_workflow = ApprovalWorkflow()
        logger.info("✓ Safety Interruption Handler initialized")

    def check_action_safety(
        self,
        thread_id: str,
        action: str,
        full_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if action requires interruption

        Returns interrupt info if action is high-risk, None otherwise
        """
        # Assess risk
        risk = self.approval_workflow.assess_risk(action)

        if not risk.get("requires_approval"):
            logger.info(f"✓ Safe action: {action[:50]}...")
            return {
                "interrupted": False,
                "action": action,
                "reason": "No safety concerns"
            }

        # Create approval request
        approval_req = self.approval_workflow.create_approval_request(
            thread_id=thread_id,
            action=action,
            risk_assessment=risk,
            full_state=full_state
        )

        return {
            "interrupted": True,
            "action": action,
            "reason": "High-risk action detected",
            "approval_request": approval_req,
            "can_edit": approval_req["allows_edit"]
        }

    def handle_human_decision(
        self,
        thread_id: str,
        approved: bool,
        edited_action: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process human decision on interrupted action"""
        result = self.approval_workflow.submit_human_approval(
            thread_id=thread_id,
            approved=approved,
            edited_action=edited_action,
            notes=notes
        )

        if result.get("status") == "error":
            return result

        # Clean up
        self.approval_workflow.clear_approval(thread_id)

        return result


# Configuration example: How to integrate with agent workflow
class AgentSafetyConfiguration:
    """Configuration for agent safety mechanisms"""

    # Which agent types get HITL checkpoint
    AGENTS_WITH_HITL = ["solution_generator", "command_generator"]

    # Actions that require HITL before execution
    CRITICAL_ACTIONS = [
        "execute_command",
        "modify_system_config",
        "delete_data",
        "restart_service"
    ]

    # Example: How to add safety checkpoint to agent node
    @staticmethod
    def create_safe_node(agent_func, thread_id: str):
        """
        Wrapper to add safety check to agent node

        Usage:
            safe_agent = AgentSafetyConfiguration.create_safe_node(
                original_agent_node,
                thread_id
            )
        """
        def safe_agent_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
            # Run original agent
            result = agent_func(state)

            # Check if result contains risky actions
            if "actions" in result:
                handler = SafetyInterruptionHandler()

                for action in result["actions"]:
                    # Check safety
                    safety_check = handler.check_action_safety(
                        thread_id=thread_id,
                        action=action,
                        full_state=state
                    )

                    if safety_check["interrupted"]:
                        # Mark state as awaiting approval
                        result["_await_approval"] = True
                        result["_approval_request"] = safety_check["approval_request"]
                        break

            return result

        return safe_agent_wrapper


# Example usage
def example_hitl_workflow():
    """
    Example of complete HITL workflow

    Demonstrates:
    1. Action safety check
    2. Approval request creation
    3. Human decision processing
    4. Action execution or cancellation
    """
    logger.info("\n" + "="*70)
    logger.info("Example: HITL Approval Workflow")
    logger.info("="*70)

    handler = SafetyInterruptionHandler()
    thread_id = "example_session_001"

    # Example 1: Safe action
    logger.info("\nExample 1: Safe Action")
    safe_result = handler.check_action_safety(
        thread_id=thread_id,
        action="list files in directory",
        full_state={"status": "processing"}
    )
    logger.info(f"Result: {safe_result['reason']}")

    # Example 2: High-risk action
    logger.info("\nExample 2: High-Risk Action Interruption")
    risky_result = handler.check_action_safety(
        thread_id=thread_id,
        action="DELETE FROM production_db WHERE older_than('2022-01-01')",
        full_state={"status": "processing"}
    )

    if risky_result["interrupted"]:
        logger.info(f"⚠ Interrupted: {risky_result['reason']}")
        logger.info(f"Awaiting human approval...")

        # Example 3: Human decision
        logger.info("\nExample 3: Human Review & Decision")

        # Human edits the query to be safer
        edited_action = "DELETE FROM logs WHERE older_than('2025-01-01') AND table='archive_logs'"

        decision_result = handler.handle_human_decision(
            thread_id=thread_id,
            approved=True,
            edited_action=edited_action,
            notes="Edited to target only archive logs table"
        )

        logger.info(f"Decision: {decision_result['status']}")
        logger.info(f"Executed Action: {decision_result['executed_action']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_hitl_workflow()
