"""
Multi-Agent LangGraph Workflow

Orchestrates the flow of data between agents for log analysis and solution generation.
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphState(BaseModel):
    """State for LangGraph"""
    messages: list
    original_log: str
    parsed_log: Dict[str, Any]
    retrieved_docs: list
    solution: str
    final_output: str


def create_multi_agent_graph(agent_factory: AgentFactory):
    """Create and return the multi-agent workflow graph"""

    # Get LLM
    llm = agent_factory.get_llm()

    # ==================== NODE FUNCTIONS ====================

    def log_analysis_node(state: dict) -> dict:
        """Node 1: Log Analysis Agent"""
        logger.info("=== Log Analysis Node ===")

        log_parsing_tool = get_log_parsing_tool()
        original_log = state.get("original_log", "")

        # Parse log
        parsed = log_parsing_tool.parse_log(original_log)
        state["parsed_log"] = parsed

        logger.info(f"Component: {parsed.get('component')}")
        logger.info(f"Error Type: {parsed.get('error_type')}")
        logger.info(f"Error Category: {parsed.get('error_category')}")

        # Create analysis message
        analysis_prompt = f"""Analyze this log message and provide your professional assessment:

Log: {original_log}

Identified Component: {parsed.get('component')}
Error Type: {parsed.get('error_type')}
Error Category: {parsed.get('error_category')}

Please provide a brief, professional summary of what this error indicates and why it occurred."""

        if llm:
            try:
                response = llm.invoke([HumanMessage(content=analysis_prompt)])
                # OllamaLLM returns string directly, not Message object
                analysis = response if isinstance(response, str) else getattr(response, 'content', str(response))
            except Exception as e:
                logger.warning(f"LLM error in log analysis: {e}")
                analysis = f"Log Analysis: Component={parsed.get('component')}, Error={parsed.get('error_type')}"
        else:
            analysis = f"Log Analysis: Component={parsed.get('component')}, Error={parsed.get('error_type')}"

        state["messages"].append(f"Log Analyzer: {analysis}")
        return state

    def retrieval_node(state: dict) -> dict:
        """Node 2: Documentation Retriever Agent"""
        logger.info("=== Documentation Retrieval Node ===")

        parsed_log = state.get("parsed_log", {})
        component = parsed_log.get("component", "")
        error_type = parsed_log.get("error_type", "")
        error_category = parsed_log.get("error_category", "")

        # Construct search query
        search_query = f"{component} {error_type} {error_category}".strip()
        if not search_query:
            search_query = state.get("original_log", "")[:100]

        logger.info(f"Searching for: {search_query}")

        vector_search_tool = get_vector_search_tool()
        docs = vector_search_tool.search(search_query, top_k=3)

        state["retrieved_docs"] = docs

        logger.info(f"Retrieved {len(docs)} relevant documents")

        # Create retrieval message
        if docs:
            doc_summary = "\n".join([f"- {doc['source']}: {doc['content'][:200]}..." for doc in docs])
            retrieval_msg = f"Retrieved {len(docs)} relevant documents:\n{doc_summary}"
        else:
            retrieval_msg = "No relevant documentation found in knowledge base"

        state["messages"].append(f"Retriever: {retrieval_msg}")
        return state

    def solution_generation_node(state: dict) -> dict:
        """Node 3: Solution Generator Agent"""
        logger.info("=== Solution Generation Node ===")

        parsed_log = state.get("parsed_log", {})
        retrieved_docs = state.get("retrieved_docs", [])
        original_log = state.get("original_log", "")

        component = parsed_log.get("component", "")
        error_type = parsed_log.get("error_type", "")

        # Get commands
        command_generator = get_command_generator_tool()
        commands = command_generator.generate_commands(component, error_type or "general")

        # Build solution prompt
        docs_context = "\n".join([
            f"Documentation: {doc['source']}\n{doc['content']}"
            for doc in retrieved_docs
        ]) if retrieved_docs else "No documentation available"

        solution_prompt = f"""Based on the following information, generate a comprehensive solution to fix this DevOps issue:

Original Log:
{original_log}

Component: {component}
Error Type: {error_type}

Retrieved Documentation:
{docs_context[:2000]}

Suggested Commands:
{chr(10).join(commands[:5])}

Please provide:
1. Root Cause: Why this error occurred
2. Solution Steps: Numbered steps to resolve
3. Commands: Specific shell commands with explanations
4. Verification: How to verify the fix works

Format your response clearly with these sections."""

        if llm:
            try:
                response = llm.invoke([HumanMessage(content=solution_prompt)])
                # OllamaLLM returns string directly, not Message object
                solution = response if isinstance(response, str) else getattr(response, 'content', str(response))
            except Exception as e:
                logger.warning(f"LLM error in solution generation: {e}")
                solution = f"""Root Cause: {error_type} in {component}
Solution Steps:
1. Run diagnostic commands
2. Check service status
3. Restart service if needed
4. Verify connectivity

Commands:
{chr(10).join(commands[:3])}"""
        else:
            solution = f"""Root Cause: {error_type} in {component}
Solution Steps:
1. Run diagnostic commands
2. Check service status
3. Restart service if needed

Commands:
{chr(10).join(commands[:3])}"""

        state["solution"] = solution
        state["messages"].append(f"Solution Generator:\n{solution}")

        return state

    def validation_node(state: dict) -> dict:
        """Node 4: Validation Agent"""
        logger.info("=== Validation Node ===")

        solution = state.get("solution", "")
        parsed_log = state.get("parsed_log", {})

        validation_prompt = f"""Review and validate this proposed solution for correctness, safety, and clarity:

Problem: {parsed_log.get('error_type', 'Unknown')} in {parsed_log.get('component', 'Unknown')}

Proposed Solution:
{solution}

Please:
1. Verify technical accuracy
2. Check for safety concerns
3. Ensure steps are in logical order
4. Improve clarity and formatting
5. Provide final recommendations

If the solution is good, refine it. If there are issues, suggest corrections."""

        if llm:
            try:
                response = llm.invoke([HumanMessage(content=validation_prompt)])
                # OllamaLLM returns string directly, not Message object
                final_output = response if isinstance(response, str) else getattr(response, 'content', str(response))
            except Exception as e:
                logger.warning(f"LLM error in validation: {e}")
                final_output = solution
        else:
            final_output = solution

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
        state["messages"].append(f"Validator: Solution validated and formatted")

        return state

    # ==================== BUILD GRAPH ====================

    # Create graph
    workflow = StateGraph(dict)

    # Add nodes
    workflow.add_node("log_analysis", log_analysis_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("solution_generation", solution_generation_node)
    workflow.add_node("validation", validation_node)

    # Add edges (sequential flow)
    workflow.set_entry_point("log_analysis")
    workflow.add_edge("log_analysis", "retrieval")
    workflow.add_edge("retrieval", "solution_generation")
    workflow.add_edge("solution_generation", "validation")
    workflow.add_edge("validation", END)

    # Compile graph
    graph = workflow.compile()

    logger.info("Multi-agent graph created successfully")
    logger.info("Flow: Log Analysis -> Retrieval -> Solution Generation -> Validation")

    return graph


def run_analysis(graph, log_input: str) -> Dict[str, Any]:
    """Run the multi-agent analysis on a log"""

    initial_state = {
        "messages": [],
        "original_log": log_input,
        "parsed_log": {},
        "retrieved_docs": [],
        "solution": "",
        "final_output": "",
    }

    logger.info(f"Starting analysis of log: {log_input[:100]}...")

    # Run graph
    result = graph.invoke(initial_state)

    return result
