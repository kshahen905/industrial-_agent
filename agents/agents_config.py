"""
Agent Configuration and Personas

Defines all agents in the multi-agent system with their roles and behaviors.
"""

import logging
from typing import Any, Dict
from langchain_ollama import OllamaLLM
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentConfig(BaseModel):
    """Configuration for an agent"""
    name: str
    role: str
    persona: str
    system_prompt: str


class AgentFactory:
    """Factory for creating and configuring agents"""

    def __init__(self, model_name: str = "neural-chat", base_url: str = "http://localhost:11434"):
        """Initialize agent factory with LLM"""
        try:
            from config import MODEL_NUM_PREDICT, MODEL_TEMPERATURE

            self.llm = OllamaLLM(
                model=model_name,
                base_url=base_url,
                temperature=MODEL_TEMPERATURE,
                num_predict=MODEL_NUM_PREDICT,
            )
            logger.info(f"✓ LLM successfully initialized")
            logger.info(f"  - Model: {model_name}")
            logger.info(f"  - Base URL: {base_url}")
            logger.info(f"  - Temperature: {MODEL_TEMPERATURE} (consistency mode)")
            logger.info(f"  - Max tokens: {MODEL_NUM_PREDICT}")
        except Exception as e:
            logger.warning(f"✗ Failed to initialize Ollama LLM: {e}")
            logger.warning("  Make sure Ollama is running: 'ollama serve'")
            logger.warning(f"  Make sure model exists: 'ollama pull {model_name}'")
            logger.warning("  Continuing without LLM (will use fallback mode)")
            self.llm = None

    def get_llm(self):
        """Get LLM instance"""
        return self.llm

    @staticmethod
    def get_log_analyzer_config() -> AgentConfig:
        """Get Log Analysis Agent configuration"""
        return AgentConfig(
            name="Log Analyzer Agent",
            role="DevOps Log Expert",
            persona="You are a DevOps expert who specializes in analyzing system logs and identifying issues.",
            system_prompt="""You are a DevOps Log Analysis Expert. Your role is to:
1. Analyze raw log messages from various systems (Docker, Linux, Python, etc.)
2. Identify the affected component (e.g., Docker, Nginx, PostgreSQL)
3. Classify the error type (e.g., port binding error, connection refused)
4. Determine potential root cause categories
5. Extract key information from the log for further analysis

You must provide clear, structured analysis that can be acted upon by downstream agents.

Format your output as:
- Component: <identified component>
- Error Type: <error classification>
- Root Cause Category: <potential cause category>
- Summary: <brief explanation>
""",
        )

    @staticmethod
    def get_retriever_config() -> AgentConfig:
        """Get Documentation Retriever Agent configuration"""
        return AgentConfig(
            name="Documentation Retriever Agent",
            role="Knowledge Base Specialist",
            persona="You are a specialized AI that retrieves relevant technical documentation from a knowledge base.",
            system_prompt="""You are a Documentation Retrieval Specialist. Your role is to:
1. Receive parsed error information from the Log Analyzer
2. Construct effective search queries to find relevant documentation
3. Retrieve the most relevant troubleshooting guides
4. Summarize key points from the retrieved documentation
5. Identify step-by-step solutions from the documentation

Always acknowledge when you're retrieving documentation and provide source information.
""",
        )

    @staticmethod
    def get_solution_generator_config() -> AgentConfig:
        """Get Solution Generator Agent configuration"""
        return AgentConfig(
            name="Solution Generator Agent",
            role="Solution Architect",
            persona="You are a solution architect who combines technical analysis with documented best practices.",
            system_prompt="""You are a Solution Generation Specialist. Your role is to:
1. Combine log analysis from the Log Analyzer Agent
2. Incorporate relevant documentation from the Retriever Agent
3. Generate actionable, step-by-step solutions
4. Provide specific commands to resolve the issue
5. Include clear explanations of what each command does
6. Consider safety and best practices

Your output must include:
- Root Cause: Clear explanation of why this happened
- Solution Steps: Numbered, detailed steps to fix the issue
- Commands: Specific commands to run (with explanations)
- Documentation Reference: Source materials used
""",
        )

    @staticmethod
    def get_validator_config() -> AgentConfig:
        """Get Validation Agent configuration"""
        return AgentConfig(
            name="Validation Agent",
            role="Quality Assurance Specialist",
            persona="You are a quality specialist who ensures all solutions are correct, safe, and practical.",
            system_prompt="""You are a Solution Validation Specialist. Your role is to:
1. Review the proposed solution from Solution Generator Agent
2. Verify technical accuracy and completeness
3. Check for safety and best practice compliance
4. Ensure the output is clear and actionable
5. Refine presentation and structure
6. Provide final, polished recommendations

Verify:
- Commands are correct and safe
- Steps are in logical order
- All prerequisites are mentioned
- Troubleshooting tips are helpful
- Output is properly formatted and clear
""",
        )

    @staticmethod
    def get_all_agents() -> Dict[str, AgentConfig]:
        """Get all agent configurations"""
        return {
            "log_analyzer": AgentFactory.get_log_analyzer_config(),
            "retriever": AgentFactory.get_retriever_config(),
            "solution_generator": AgentFactory.get_solution_generator_config(),
            "validator": AgentFactory.get_validator_config(),
        }


class MultiAgentState:
    """Shared state passed between agents"""

    def __init__(self):
        self.original_log = None
        self.parsed_log = None
        self.retrieved_docs = []
        self.solution = None
        self.final_output = None
        self.messages = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        return {
            "original_log": self.original_log,
            "parsed_log": self.parsed_log,
            "retrieved_docs": self.retrieved_docs,
            "solution": self.solution,
            "final_output": self.final_output,
            "messages": self.messages,
        }

    def __repr__(self) -> str:
        return f"MultiAgentState({self.to_dict()})"


def init_agents(model_name: str = None, base_url: str = "http://localhost:11434") -> AgentFactory:
    """Initialize and return agent factory"""
    # Use config model if not specified
    if model_name is None:
        from config import DEFAULT_MODEL
        model_name = DEFAULT_MODEL

    factory = AgentFactory(model_name=model_name, base_url=base_url)

    # Log agent configurations
    for agent_name, config in factory.get_all_agents().items():
        logger.info(f"  ✓ Agent configured: {config.name} ({config.role})")

    return factory
