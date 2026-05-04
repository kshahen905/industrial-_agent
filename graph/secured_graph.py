"""
Secured LangGraph Workflow with Guardrails

Implements security-first multi-agent orchestration:
1. Input Guardrail Node: Intercepts and validates user input
2. Alert Node: Returns standardized refusal for unsafe inputs
3. Agent Nodes: Process only safe inputs
4. Output Sanitization: Cleans responses before returning to user

Graph Flow:
    User Input
        ↓
    [GUARDRAIL NODE] ← First line of defense
        ├→ UNSAFE → [ALERT NODE] → Refusal Message → User
        └→ SAFE → [LOG ANALYSIS] → [RETRIEVAL] → [GENERATION] → [VALIDATION] → User
"""

import logging
from typing import Any, Dict

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel

from tools.tools import (
    get_log_parsing_tool,
    get_vector_search_tool,
    get_command_generator_tool,
)
from agents.agents_config import AgentFactory, MultiAgentState
from security.guardrails_config import (
    ForbiddenPatterns,
    GuardrailRules,
    RefusalMessages,
    OutputSanitizer,
    SecurityAuditLog,
    SecurityLevel,
    AttackType,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== GUARDRAIL NODE ====================

def guardrail_node(state: dict) -> dict:
    """
    NODE 0: INPUT SECURITY VALIDATION

    First line of defense - intercepts user input before it reaches the LLM.

    Checks for:
    1. Persona hijacking (DAN, roleplay requests)
    2. Instruction override attempts
    3. Payload smuggling (hidden commands)
    4. Dangerous command patterns
    5. Jailbreak attempts

    If unsafe: Routes to alert_node
    If safe: Continues to log_analysis_node
    """
    logger.info("\n" + "="*70)
    logger.info("🔒 SECURITY: Guardrail Node - Input Validation")
    logger.info("="*70)

    user_input = state.get("original_log", "")

    if not user_input:
        logger.warning("⚠ Empty input received")
        state["security_status"] = "BLOCKED"
        state["block_reason"] = "Empty input"
        return state

    # ==================== STEP 1: Check for adversarial patterns ====================
    logger.info(f"\n[1/3] Checking for adversarial patterns...")
    security_level, attack_type, description = ForbiddenPatterns.check_input(user_input)

    logger.info(f"  Security Level: {security_level.value}")
    logger.info(f"  Attack Type:    {attack_type.value}")
    logger.info(f"  Description:    {description}")

    if security_level in [SecurityLevel.UNSAFE, SecurityLevel.BLOCKED]:
        logger.error(f"  ✗ BLOCKED: {description}")
        state["security_status"] = "BLOCKED"
        state["block_reason"] = description
        state["attack_type"] = attack_type
        state["messages"].append(f"🔒 Security: BLOCKED - {attack_type.value}")

        # Log security event
        SecurityAuditLog.log_event(
            event_type="adversarial_input_detected",
            severity=security_level,
            attack_type=attack_type,
            user_input=user_input,
            action_taken="INPUT_BLOCKED"
        )
        return state

    # ==================== STEP 2: Check topic allowance ====================
    logger.info(f"\n[2/3] Checking if topic is allowed...")
    is_allowed, reason = GuardrailRules.is_topic_allowed(user_input)

    logger.info(f"  Topic Allowed: {is_allowed}")
    logger.info(f"  Reason:        {reason}")

    if not is_allowed:
        logger.error(f"  ✗ TOPIC BLOCKED: {reason}")
        state["security_status"] = "BLOCKED"
        state["block_reason"] = reason
        state["attack_type"] = AttackType.COMMAND_INJECTION
        state["messages"].append(f"🔒 Security: Topic not allowed - {reason}")

        SecurityAuditLog.log_event(
            event_type="forbidden_topic_requested",
            severity=SecurityLevel.UNSAFE,
            attack_type=AttackType.COMMAND_INJECTION,
            user_input=user_input,
            action_taken="TOPIC_BLOCKED"
        )
        return state

    # ==================== STEP 3: Final safety check ====================
    logger.info(f"\n[3/3] Final safety validation...")

    # Verify input length
    if len(user_input) > 5000:
        logger.error("  ✗ Input exceeds maximum length (5000 chars)")
        state["security_status"] = "BLOCKED"
        state["block_reason"] = "Input too long"
        return state

    # Verify it's not just suspicious patterns
    if security_level == SecurityLevel.SUSPICIOUS:
        logger.warning(f"  ⚠ Input marked as SUSPICIOUS but continuing (limit check enabled)")
        state["security_status"] = "FLAGGED"
        state["messages"].append("⚠ Warning: Input contains suspicious patterns but was allowed")

        SecurityAuditLog.log_event(
            event_type="suspicious_input_allowed",
            severity=SecurityLevel.SUSPICIOUS,
            attack_type=attack_type,
            user_input=user_input,
            action_taken="ALLOWED_WITH_WARNING"
        )

    # ==================== ALL CHECKS PASSED ====================
    logger.info(f"  ✓ ALL SECURITY CHECKS PASSED")
    state["security_status"] = "SAFE"
    state["block_reason"] = None
    state["attack_type"] = None
    state["messages"].append("✓ Security: Input passed all checks")

    logger.info("✓ Input safe to process → Proceeding to Log Analysis\n")
    return state


# ==================== ALERT NODE ====================

def alert_node(state: dict) -> dict:
    """
    NODE: SECURITY ALERT & REFUSAL

    Triggered when input fails guardrail checks.

    Returns:
    - Standardized refusal message appropriate to attack type
    - Security event logging
    - Safe prompt for user to try again
    """
    logger.info("\n" + "="*70)
    logger.info("⛔ SECURITY: Alert Node - Request Blocked")
    logger.info("="*70)

    attack_type = state.get("attack_type", AttackType.UNKNOWN)
    block_reason = state.get("block_reason", "Unknown security issue")

    logger.error(f"✗ Request blocked for reason: {block_reason}")
    logger.error(f"✗ Attack type: {attack_type.value if attack_type else 'UNKNOWN'}")

    # Get appropriate refusal message
    refusal_message = RefusalMessages.get_refusal(attack_type) if attack_type else RefusalMessages.GENERIC_UNSAFE

    # Format alert output
    alert_output = f"""
╔════════════════════════════════════════════════════════════════╗
║                   🔒 SECURITY ALERT 🔒                        ║
╚════════════════════════════════════════════════════════════════╝

Your request has been blocked by security guardrails.

Reason: {block_reason}
Attack Type: {attack_type.value if attack_type else 'UNKNOWN'}

{refusal_message}

════════════════════════════════════════════════════════════════
"""

    state["final_output"] = alert_output
    state["messages"].append(f"Alert: {block_reason}")

    return state


# ==================== ORIGINAL AGENT NODES (with output sanitization) ====================

def log_analysis_node(state: dict) -> dict:
    """NODE 1: Log Analysis Agent (with output sanitization)"""
    logger.info("\n" + "="*70)
    logger.info("📋 LOG ANALYSIS: Parsing and identifying error")
    logger.info("="*70)

    log_parsing_tool = get_log_parsing_tool()
    original_log = state.get("original_log", "")

    parsed = log_parsing_tool.parse_log(original_log)
    state["parsed_log"] = parsed

    logger.info(f"  Component:      {parsed.get('component')}")
    logger.info(f"  Error Type:     {parsed.get('error_type')}")
    logger.info(f"  Error Category: {parsed.get('error_category')}")

    analysis_prompt = f"""Analyze this log message and provide your professional assessment:

Log: {original_log}

Identified Component: {parsed.get('component')}
Error Type: {parsed.get('error_type')}
Error Category: {parsed.get('error_category')}

Please provide a brief, professional summary of what this error indicates and why it occurred."""

    if state.get("llm"):
        try:
            response = state["llm"].invoke([HumanMessage(content=analysis_prompt)])
            analysis = response if isinstance(response, str) else getattr(response, 'content', str(response))
        except Exception as e:
            logger.warning(f"LLM error: {e}")
            analysis = f"Analysis: Component={parsed.get('component')}, Error={parsed.get('error_type')}"
    else:
        analysis = f"Analysis: Component={parsed.get('component')}, Error={parsed.get('error_type')}"

    # Sanitize analysis before storing
    analysis = OutputSanitizer.sanitize_response(analysis)
    state["messages"].append(f"Log Analyzer: {analysis}")
    return state


def retrieval_node(state: dict) -> dict:
    """NODE 2: Documentation Retriever (with sanitized results)"""
    logger.info("\n" + "="*70)
    logger.info("📚 RETRIEVAL: Searching documentation")
    logger.info("="*70)

    parsed_log = state.get("parsed_log", {})
    component = parsed_log.get("component", "")
    error_type = parsed_log.get("error_type", "")

    search_query = f"{component} {error_type}".strip()
    if not search_query:
        search_query = state.get("original_log", "")[:100]

    logger.info(f"  Query: {search_query}")

    vector_search_tool = get_vector_search_tool()
    docs = vector_search_tool.search(search_query, top_k=3)

    # Sanitize retrieved documents
    sanitized_docs = []
    for doc in docs:
        sanitized = {
            "content": OutputSanitizer.sanitize_response(doc["content"]),
            "source": doc.get("source", "unknown").split("/")[-1]  # Only filename, not full path
        }
        sanitized_docs.append(sanitized)

    state["retrieved_docs"] = sanitized_docs

    logger.info(f"  Found: {len(sanitized_docs)} relevant documents")
    if sanitized_docs:
        doc_summary = "\n".join([f"  • {doc['source']}" for doc in sanitized_docs[:3]])
        logger.info(f"  Sources:\n{doc_summary}")

    state["messages"].append(f"Retriever: Found {len(sanitized_docs)} documents")
    return state


def solution_generation_node(state: dict) -> dict:
    """NODE 3: Solution Generator (with sanitized output)"""
    logger.info("\n" + "="*70)
    logger.info("🔧 SOLUTION: Generating fix recommendations")
    logger.info("="*70)

    parsed_log = state.get("parsed_log", {})
    retrieved_docs = state.get("retrieved_docs", [])

    component = parsed_log.get("component", "")
    error_type = parsed_log.get("error_type", "")

    command_generator = state.get("command_generator_tool")
    if not command_generator:
        from tools.tools import get_command_generator_tool
        command_generator = get_command_generator_tool()

    commands = command_generator.generate_commands(component, error_type or "general")

    docs_context = "\n".join([
        f"Documentation: {doc['source']}\n{doc['content'][:300]}..."
        for doc in retrieved_docs
    ]) if retrieved_docs else "No documentation available"

    solution_prompt = f"""Based on the analysis, generate a solution:

Component: {component}
Error Type: {error_type}

Documentation:
{docs_context[:1000]}

Suggested Commands:
{chr(10).join(commands[:5])}

Please provide root cause analysis and solution steps."""

    if state.get("llm"):
        try:
            response = state["llm"].invoke([HumanMessage(content=solution_prompt)])
            solution = response if isinstance(response, str) else getattr(response, 'content', str(response))
        except Exception as e:
            logger.warning(f"LLM error: {e}")
            solution = f"Solution for {error_type} in {component}"
    else:
        solution = f"Solution for {error_type} in {component}"

    # Sanitize solution
    solution = OutputSanitizer.sanitize_response(solution)
    state["solution"] = solution
    state["messages"].append("Solution Generator: Generated solution")

    return state


def validation_node(state: dict) -> dict:
    """NODE 4: Validation Agent (with output sanitization)"""
    logger.info("\n" + "="*70)
    logger.info("✅ VALIDATION: Reviewing solution quality")
    logger.info("="*70)

    solution = state.get("solution", "")
    parsed_log = state.get("parsed_log", {})

    validation_prompt = f"""Review this proposed solution for accuracy and safety:

Problem: {parsed_log.get('error_type', 'Unknown')} in {parsed_log.get('component', 'Unknown')}

Proposed Solution:
{solution}

Verify: accuracy, safety, clarity, completeness"""

    if state.get("llm"):
        try:
            response = state["llm"].invoke([HumanMessage(content=validation_prompt)])
            final_output = response if isinstance(response, str) else getattr(response, 'content', str(response))
        except Exception as e:
            logger.warning(f"LLM error: {e}")
            final_output = solution
    else:
        final_output = solution

    # FINAL OUTPUT SANITIZATION - most important step
    final_output = OutputSanitizer.sanitize_response(final_output, allow_metadata=False)

    # Format final output
    output = f"""
╔════════════════════════════════════════════════════════════════╗
║           DevOps Log Analysis - Final Recommendation           ║
╚════════════════════════════════════════════════════════════════╝

Component: {parsed_log.get('component', 'Unknown')}
Error Type: {parsed_log.get('error_type', 'Unknown')}

{final_output}

════════════════════════════════════════════════════════════════
"""

    state["final_output"] = output
    state["messages"].append("✓ Validation: Solution ready")

    return state


# ==================== CONDITIONAL ROUTING ====================

def should_route_to_alert(state: dict) -> str:
    """
    Router: Determine if input should go to alert_node or continue to processing

    Returns:
    - "ALERT" if security check failed
    - "PROCESS" if security check passed
    """
    security_status = state.get("security_status", "UNKNOWN")

    if security_status == "BLOCKED":
        logger.info("🔄 Routing to: ALERT NODE (security blocked)")
        return "ALERT"
    else:
        logger.info("🔄 Routing to: LOG ANALYSIS NODE (security passed)")
        return "PROCESS"


# ==================== CREATE SECURED GRAPH ====================

def create_secured_multi_agent_graph(agent_factory):
    """
    Create the secured multi-agent workflow with guardrails.

    Graph Structure:
    ```
    User Input
        ↓
    [GUARDRAIL_NODE] - Input validation
        ├→ UNSAFE → [ALERT_NODE] → Return refusal
        └→ SAFE → [LOG_ANALYSIS] → [RETRIEVAL] → [SOLUTION] → [VALIDATION] → User
    ```

    Key Features:
    ✓ Input sanitization before LLM processing
    ✓ Conditional routing based on security checks
    ✓ Output sanitization before returning to user
    ✓ Security audit logging for all events
    """

    workflow = StateGraph(dict)

    # Get LLM
    llm = agent_factory.get_llm()

    # Update agents to use LLM from factory
    def create_analysis_node(llm):
        def node(state):
            state["llm"] = llm
            return log_analysis_node(state)
        return node

    def create_retrieval_node():
        def node(state):
            return retrieval_node(state)
        return node

    def create_solution_node():
        def node(state):
            state["llm"] = llm
            from tools.tools import get_command_generator_tool
            state["command_generator_tool"] = get_command_generator_tool()
            return solution_generation_node(state)
        return node

    def create_validation_node():
        def node(state):
            state["llm"] = llm
            return validation_node(state)
        return node

    # ==================== ADD NODES ====================

    workflow.add_node("guardrail", guardrail_node)
    workflow.add_node("alert", alert_node)
    workflow.add_node("log_analysis", create_analysis_node(llm))
    workflow.add_node("retrieval", create_retrieval_node())
    workflow.add_node("solution_generation", create_solution_node())
    workflow.add_node("validation", create_validation_node())

    # ==================== ADD EDGES ====================

    # Start with guardrail check
    workflow.set_entry_point("guardrail")

    # Conditional routing after guardrail
    workflow.add_conditional_edges(
        "guardrail",
        should_route_to_alert,
        {
            "ALERT": "alert",
            "PROCESS": "log_analysis"
        }
    )

    # Both paths end
    workflow.add_edge("alert", END)

    # Normal processing flow
    workflow.add_edge("log_analysis", "retrieval")
    workflow.add_edge("retrieval", "solution_generation")
    workflow.add_edge("solution_generation", "validation")
    workflow.add_edge("validation", END)

    # Compile graph
    graph = workflow.compile()

    logger.info("\n" + "="*70)
    logger.info("🔒 SECURED GRAPH CREATED")
    logger.info("="*70)
    logger.info("Graph Flow:")
    logger.info("  1. GUARDRAIL_NODE - Input validation (first line of defense)")
    logger.info("  2. Branch:")
    logger.info("     • UNSAFE → ALERT_NODE → Refusal message")
    logger.info("     • SAFE → LOG_ANALYSIS → RETRIEVAL → SOLUTION → VALIDATION → Output")
    logger.info("  3. OUTPUT_SANITIZATION - Remove sensitive data before returning")
    logger.info("  4. SECURITY_AUDIT_LOG - Log all security events")
    logger.info("="*70 + "\n")

    return graph


def run_secured_analysis(graph, log_input: str) -> Dict[str, Any]:
    """Run analysis with security guardrails enabled"""

    initial_state = {
        "messages": [],
        "original_log": log_input,
        "parsed_log": {},
        "retrieved_docs": [],
        "solution": "",
        "final_output": "",
        "security_status": "UNKNOWN",
        "block_reason": None,
        "attack_type": None,
    }

    logger.info(f"🚀 Starting secured analysis...")
    logger.info(f"Input length: {len(log_input)} chars\n")

    try:
        result = graph.invoke(initial_state)
        return result
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return {
            "final_output": f"Error during analysis: {str(e)}",
            "security_status": "ERROR"
        }
