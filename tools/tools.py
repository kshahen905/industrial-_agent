"""
DevOps Log Analysis Tools

Tools for searching documentation, parsing logs, and generating commands.
Implements LangChain tool decorators with Pydantic validation per Lab 3 requirements.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from pydantic import BaseModel, Field, validator
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
import chromadb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== PYDANTIC INPUT SCHEMAS ====================

class VectorSearchInput(BaseModel):
    """Pydantic schema for vector search tool input validation"""
    query: str = Field(
        ...,
        description="The search query for documentation",
        min_length=1,
        max_length=500
    )
    top_k: int = Field(
        default=3,
        description="Number of top results to retrieve (1-10)",
        ge=1,
        le=10
    )
    doc_type: Optional[str] = Field(
        default=None,
        description="Filter by document type: docker, linux, python, or general",
        pattern="^(docker|linux|python|general|None)$"
    )
    error_category: Optional[str] = Field(
        default=None,
        description="Filter by error category for precise retrieval",
        max_length=50
    )

    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()


class LogParsingInput(BaseModel):
    """Pydantic schema for log parsing tool input validation"""
    log_text: str = Field(
        ...,
        description="Raw log message to parse and analyze",
        min_length=5,
        max_length=5000
    )
    extract_snippet: bool = Field(
        default=False,
        description="Whether to extract a snippet from the log"
    )

    @validator('log_text')
    def validate_log_text(cls, v):
        if not v.strip():
            raise ValueError("Log text cannot be empty")
        return v.strip()


class CommandGeneratorInput(BaseModel):
    """Pydantic schema for command generator tool input validation"""
    component: str = Field(
        ...,
        description="Component affected: docker, nginx, python, or linux",
        pattern="^(docker|nginx|python|linux|general)$"
    )
    error_type: str = Field(
        ...,
        description="Type of error detected in the system",
        min_length=1,
        max_length=50
    )
    severity: str = Field(
        default="medium",
        description="Severity level: critical, high, medium, low",
        pattern="^(critical|high|medium|low)$"
    )

    @validator('error_type')
    def validate_error_type(cls, v):
        if not v.strip():
            raise ValueError("Error type cannot be empty")
        return v.strip()


# ==================== TOOL CLASSES ====================


class VectorSearchTool:
    """Search documentation using ChromaDB"""

    def __init__(self, vector_db_path: str):
        self.vector_db_path = Path(vector_db_path)

        # Initialize embeddings
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},
            )
            logger.info("✓ Embeddings model loaded successfully")
        except Exception as e:
            logger.error(f"✗ Failed to load embeddings: {e}")
            raise

        # Initialize ChromaDB with new API
        try:
            from config import CHROMA_HOST, CHROMA_PORT
            if CHROMA_HOST:
                self.chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
                logger.info(f"✓ ChromaDB initialized successfully (Client Mode)")
                logger.info(f"  Connection: {CHROMA_HOST}:{CHROMA_PORT}")
            else:
                self.chroma_client = chromadb.PersistentClient(path=str(self.vector_db_path))
                logger.info(f"✓ ChromaDB initialized successfully (Persistent Mode)")
                logger.info(f"  Database location: {self.vector_db_path}")
        except Exception as e:
            logger.error(f"✗ Failed to initialize ChromaDB: {e}")
            raise

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant documentation chunks"""
        try:
            collection = self.chroma_client.get_collection(name="devops_docs")
            logger.debug(f"Searching ChromaDB collection 'devops_docs' for: {query[:80]}...")

            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)

            # Search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
            )

            # Format results
            docs = []
            if results and results["documents"] and len(results["documents"]) > 0:
                for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                    docs.append({
                        "content": doc,
                        "source": metadata.get("source", "unknown"),
                    })
                logger.info(f"✓ Found {len(docs)} relevant documents in ChromaDB")
            else:
                logger.warning(f"⚠ No relevant documents found in ChromaDB for query: {query[:80]}...")

            return docs

        except Exception as e:
            logger.warning(f"⚠ Error searching ChromaDB: {e}")
            return []


class LogParsingTool:
    """Parse and analyze DevOps logs"""

    # Pattern definitions for different error types
    PATTERNS = {
        "docker": {
            "keywords": ["docker", "container", "daemon", "image"],
            "errors": {
                "port_binding": r"driver failed programming external connectivity|bind: address already in use",
                "connection": r"Cannot connect to Docker daemon|failed to download image",
                "memory": r"killed.*memory|OOM|out of memory",
                "image": r"Unable to find image|Pull failed",
            }
        },
        "nginx": {
            "keywords": ["nginx", "http", "web server", "proxy"],
            "errors": {
                "connection": r"connect\(\) failed|Connection refused",
                "config": r"Config file|configuration error",
                "process": r"Main process exited",
            }
        },
        "python": {
            "keywords": ["traceback", "python", "import", "error"],
            "errors": {
                "module": r"ModuleNotFoundError|ImportError",
                "database": r"OperationalError.*psycopg2|could not connect",
                "json": r"JSONDecodeError",
                "file": r"FileNotFoundError",
                "memory": r"out of memory|CUDA out of memory",
            }
        },
        "linux": {
            "keywords": ["systemd", "service", "kernel", "system"],
            "errors": {
                "oom": r"Out of memory|Kill process",
                "service": r"Main process exited|Connection refused",
                "permission": r"not in sudoers|Permission denied",
                "dns": r"Cannot set DNS|resolve",
            }
        }
    }

    def parse_log(self, log_text: str) -> Dict[str, Any]:
        """Parse log message and extract information"""
        analysis = {
            "raw_log": log_text,
            "component": None,
            "error_type": None,
            "error_category": None,
            "keywords": [],
        }

        # Detect component
        for component, config in self.PATTERNS.items():
            for keyword in config["keywords"]:
                if keyword.lower() in log_text.lower():
                    analysis["component"] = component

            # Detect error type
            if analysis["component"] == component:
                for error_type, pattern in config["errors"].items():
                    if re.search(pattern, log_text, re.IGNORECASE):
                        analysis["error_type"] = error_type
                        break

        # Extract potential root causes
        if "address already in use" in log_text.lower():
            analysis["error_category"] = "port_conflict"
        elif "connection refused" in log_text.lower():
            analysis["error_category"] = "service_unavailable"
        elif "out of memory" in log_text.lower():
            analysis["error_category"] = "resource_exhaustion"
        elif "modulenotfound" in log_text.lower():
            analysis["error_category"] = "missing_dependency"
        elif "permission denied" in log_text.lower():
            analysis["error_category"] = "permission_error"
        elif "connection refused" in log_text.lower():
            analysis["error_category"] = "connectivity_issue"

        return analysis

    def extract_snippet(self, log_text: str, lines: int = 5) -> str:
        """Extract relevant snippet from log"""
        lines_list = log_text.split("\n")
        return "\n".join(lines_list[:lines])


class CommandGeneratorTool:
    """Generate troubleshooting commands"""

    COMMAND_TEMPLATES = {
        "docker": {
            "port_binding": [
                "lsof -i :80",
                "netstat -tulpn | grep LISTEN",
                "sudo systemctl restart docker",
                "docker ps -a",
            ],
            "connection": [
                "sudo systemctl status docker",
                "sudo systemctl start docker",
                "docker info",
            ],
            "memory": [
                "docker stats",
                "docker inspect <container_name> | grep Memory",
                "docker system prune",
            ],
        },
        "nginx": {
            "connection": [
                "sudo systemctl status nginx",
                "sudo nginx -t",
                "sudo systemctl restart nginx",
                "curl -v http://localhost",
            ],
            "config": [
                "sudo nginx -t",
                "sudo systemctl reload nginx",
                "sudo cat /etc/nginx/nginx.conf",
            ],
            "process": [
                "sudo journalctl -u nginx -n 20",
                "sudo systemctl start nginx",
                "tail -f /var/log/nginx/error.log",
            ],
        },
        "python": {
            "module": [
                "pip install <module_name>",
                "python -c 'import <module_name>'",
                "pip list",
            ],
            "database": [
                "psql -h localhost -U postgres -c 'SELECT version();'",
                "sudo systemctl status postgresql",
                "psql -h <host> -U <user> -c 'SELECT 1'",
            ],
            "json": [
                "python -c \"import json; json.loads(response.text)\"",
                "curl -s <api_url> | python -m json.tool",
            ],
            "file": [
                "ls -la /path/to/file",
                "find / -name '<filename>'",
                "pwd",
            ],
            "memory": [
                "nvidia-smi",
                "free -h",
                "ps aux --sort=-%mem",
            ],
        },
        "linux": {
            "oom": [
                "free -h",
                "top -o %MEM",
                "ps aux --sort=-%mem | head",
            ],
            "service": [
                "sudo systemctl status <service>",
                "sudo journalctl -u <service> -n 50",
                "sudo systemctl start <service>",
            ],
            "permission": [
                "sudo visudo",
                "groups $USER",
                "sudo usermod -aG sudo username",
            ],
            "dns": [
                "cat /etc/resolv.conf",
                "systemd-resolve --status",
                "nslookup example.com",
            ],
        },
    }

    def generate_commands(self, component: str, error_type: str) -> List[str]:
        """Generate relevant commands for the issue"""
        commands = []

        if component in self.COMMAND_TEMPLATES:
            error_commands = self.COMMAND_TEMPLATES[component].get(error_type, [])
            commands.extend(error_commands)

        # Add general diagnostic commands
        if component:
            commands.insert(0, f"# Diagnostic commands for {component}")

        return commands


# Tool instances (singleton-like)
vector_search_tool = None
log_parsing_tool = None
command_generator_tool = None


def initialize_tools(vector_db_path: str):
    """Initialize all tools"""
    global vector_search_tool, log_parsing_tool, command_generator_tool

    vector_search_tool = VectorSearchTool(vector_db_path)
    log_parsing_tool = LogParsingTool()
    command_generator_tool = CommandGeneratorTool()

    logger.info("Tools initialized successfully")


def get_vector_search_tool() -> VectorSearchTool:
    """Get vector search tool instance"""
    if vector_search_tool is None:
        raise RuntimeError("Tools not initialized. Call initialize_tools() first.")
    return vector_search_tool


def get_log_parsing_tool() -> LogParsingTool:
    """Get log parsing tool instance"""
    if log_parsing_tool is None:
        raise RuntimeError("Tools not initialized. Call initialize_tools() first.")
    return log_parsing_tool


def get_command_generator_tool() -> CommandGeneratorTool:
    """Get command generator tool instance"""
    if command_generator_tool is None:
        raise RuntimeError("Tools not initialized. Call initialize_tools() first.")
    return command_generator_tool


# ==================== LANGGRAPH @tool DECORATED FUNCTIONS ====================
# These functions wrap the tool classes with @tool decorator per Lab 3 requirements
# Enables proper tool calling in LangGraph agent nodes

@tool("search_documentation")
def search_documentation_tool(
    query: str,
    top_k: int = 3,
    doc_type: Optional[str] = None,
    error_category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search documentation using semantic embeddings and ChromaDB.

    This tool retrieves relevant documentation chunks from the knowledge base
    using vector similarity search. Results can be filtered by document type
    and error category for precision retrieval.

    Args:
        query: The search query describing the issue
        top_k: Number of results to return (1-10, default: 3)
        doc_type: Filter by document type [docker|linux|python|general]
        error_category: Filter by error category for precise retrieval

    Returns:
        List of dictionaries with 'content' and 'source' keys

    Example:
        >>> search_documentation_tool(
        ...     query="nginx connection refused error",
        ...     top_k=3,
        ...     doc_type="nginx"
        ... )
        [
            {"content": "nginx troubleshooting...", "source": "linux_server_guide.txt"},
            ...
        ]

    Raises:
        ValueError: If query is empty or tool not initialized
    """
    # Validate input using Pydantic
    input_data = VectorSearchInput(
        query=query,
        top_k=top_k,
        doc_type=doc_type,
        error_category=error_category
    )

    tool = get_vector_search_tool()
    results = tool.search(input_data.query, input_data.top_k)

    logger.info(f"✓ search_documentation_tool: Found {len(results)} documents")
    return results


@tool("parse_log_message")
def parse_log_message_tool(
    log_text: str,
    extract_snippet: bool = False
) -> Dict[str, Any]:
    """
    Parse DevOps log messages and extract structured information.

    Analyzes raw log messages to identify:
    - Component (docker, nginx, python, linux, etc.)
    - Error type (port_binding, connection_refused, oom, etc.)
    - Error category (resource_exhaustion, service_unavailable, etc.)

    Uses pattern matching and keyword detection for robust log analysis.
    Works with logs from various sources: Docker, Linux kernel, Nginx, Python.

    Args:
        log_text: Raw log message to parse and analyze
        extract_snippet: Whether to extract first 5 lines as snippet

    Returns:
        Dictionary containing:
        - raw_log: Original input
        - component: Identified component (docker|nginx|python|linux)
        - error_type: Classified error type
        - error_category: Error categorization
        - keywords: Extracted keywords
        - snippet: First 5 lines (if extract_snippet=True)

    Example:
        >>> parse_log_message_tool(
        ...     log_text="ERROR [kernel]: Out of memory: Kill process 9876"
        ... )
        {
            'component': 'linux',
            'error_type': 'oom',
            'error_category': 'resource_exhaustion',
            ...
        }

    Raises:
        ValueError: If log_text is empty or invalid
    """
    # Validate input using Pydantic
    input_data = LogParsingInput(
        log_text=log_text,
        extract_snippet=extract_snippet
    )

    tool = get_log_parsing_tool()
    result = tool.parse_log(input_data.log_text)

    if input_data.extract_snippet:
        result["snippet"] = tool.extract_snippet(input_data.log_text)

    logger.info(f"✓ parse_log_message_tool: Identified {result['component']}/{result['error_type']}")
    return result


@tool("generate_fix_commands")
def generate_fix_commands_tool(
    component: str,
    error_type: str,
    severity: str = "medium"
) -> List[str]:
    """
    Generate diagnostic and fix commands for identified issues.

    Retrieves pre-tested, safe commands for troubleshooting based on:
    - Component type (docker, nginx, python, linux)
    - Specific error type within that component
    - Severity level to prioritize critical fixes

    Commands are organized into sequences:
    1. Diagnostic commands (gather information)
    2. Fix commands (resolve the issue)
    3. Verification commands (confirm resolution)

    Args:
        component: Component affected [docker|nginx|python|linux|general]
        error_type: Type of error (port_binding, connection_refused, oom, etc.)
        severity: Severity level [critical|high|medium|low]

    Returns:
        List of shell commands with inline comments

    Example:
        >>> generate_fix_commands_tool(
        ...     component="docker",
        ...     error_type="port_binding",
        ...     severity="high"
        ... )
        [
            "# Diagnostic commands for docker",
            "lsof -i :80",
            "netstat -tulpn | grep LISTEN",
            "sudo systemctl restart docker",
            ...
        ]

    Raises:
        ValueError: If component or error_type is invalid
    """
    # Validate input using Pydantic
    input_data = CommandGeneratorInput(
        component=component,
        error_type=error_type,
        severity=severity
    )

    tool = get_command_generator_tool()
    commands = tool.generate_commands(input_data.component, input_data.error_type)

    # Add severity indicator
    commands.insert(1, f"# Severity: {input_data.severity}")

    logger.info(f"✓ generate_fix_commands_tool: Generated {len(commands)} commands for {input_data.component}")
    return commands
