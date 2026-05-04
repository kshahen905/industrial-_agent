"""
MCP Client - File Management & Security Analyzer

Standalone MCP client implementation demonstrating:
- Connection establishment to MCP server
- Tool discovery mechanism
- Tool invocation with structured parameters
- Response parsing and error handling
- Async/await patterns for protocol communication

Part B Task 2: 10 marks

Usage:
    client = MCPClient()
    await client.connect()

    # Discover available tools
    tools = await client.discover_tools()

    # Invoke a tool
    result = await client.call_tool("analyze_file_security", {
        "file_path": "/path/to/file",
        "check_permissions": True
    })
"""

import json
import asyncio
import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MCP_Client")


class MCPConnection(ABC):
    """Abstract base class for MCP connections"""

    @abstractmethod
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send request and get response"""
        pass

    @abstractmethod
    async def connect(self):
        """Establish connection"""
        pass

    @abstractmethod
    async def disconnect(self):
        """Close connection"""
        pass


class StdioMCPConnection(MCPConnection):
    """MCP connection via stdio (standard input/output)"""

    def __init__(self, command: str):
        """
        Initialize stdio connection

        Args:
            command: Command to start MCP server (e.g., "python mcp_server.py")
        """
        self.command = command
        self.process = None
        self.message_id = 0
        logger.info(f"✓ Stdio MCP Connection configured: {command}")

    async def connect(self):
        """Establish connection by starting server process"""
        try:
            import subprocess
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            logger.info("✓ Connected to MCP server via stdio")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to connect: {e}")
            return False

    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to server and receive response"""
        if not self.process:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            # Send request
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()

            # Receive response
            response_str = self.process.stdout.readline()
            if not response_str:
                raise RuntimeError("Server closed connection")

            response = json.loads(response_str)
            return response

        except Exception as e:
            logger.error(f"✗ Request failed: {e}")
            raise

    async def disconnect(self):
        """Close connection"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("✓ Disconnected from MCP server")
            except Exception as e:
                logger.error(f"✗ Error disconnecting: {e}")


class MCPClient:
    """
    MCP Client for File Management & Security Analysis

    Features:
    - Tool discovery
    - Tool invocation
    - Response parsing
    - Error handling
    """

    def __init__(self, connection: Optional[MCPConnection] = None, server_url: str = "http://localhost:8000"):
        """
        Initialize MCP client

        Args:
            connection: MCPConnection instance (optional)
            server_url: Server URL for HTTP connections
        """
        self.connection = connection
        self.server_url = server_url
        self.request_id = 0
        self.tools_cache: Dict[str, Dict[str, Any]] = {}
        self.connected = False
        logger.info("✓ MCP Client initialized")

    async def connect(self) -> bool:
        """Connect to MCP server"""
        try:
            if self.connection:
                await self.connection.connect()

            # Send initialization request
            init_response = await self._send_json_rpc_request("initialize", {})

            if "result" in init_response:
                logger.info("✓ Client connected and initialized")
                logger.info(f"  Server: {init_response['result'].get('serverInfo', {}).get('name')}")
                logger.info(f"  Version: {init_response['result'].get('serverInfo', {}).get('version')}")
                self.connected = True
                return True
            else:
                logger.error("✗ Initialization failed")
                return False

        except Exception as e:
            logger.error(f"✗ Connection failed: {e}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from MCP server"""
        try:
            if self.connection:
                await self.connection.disconnect()
            self.connected = False
            logger.info("✓ Client disconnected")
            return True
        except Exception as e:
            logger.error(f"✗ Disconnection failed: {e}")
            return False

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """
        Discover available tools from server

        Returns:
            List of tool definitions
        """
        if not self.connected:
            logger.error("✗ Not connected. Call connect() first.")
            return []

        try:
            response = await self._send_json_rpc_request("tools/list", {})

            if "result" in response:
                tools = response["result"].get("tools", [])
                self.tools_cache = {tool["name"]: tool for tool in tools}

                logger.info(f"✓ Discovered {len(tools)} tools:")
                for tool in tools:
                    logger.info(f"  • {tool['name']}: {tool['description']}")

                return tools
            else:
                logger.error("✗ Tool discovery failed")
                return []

        except Exception as e:
            logger.error(f"✗ Tool discovery error: {e}")
            return []

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call a tool with given arguments

        Args:
            tool_name: Name of tool to invoke
            arguments: Tool arguments as dictionary

        Returns:
            Tool result
        """
        if not self.connected:
            logger.error("✗ Not connected. Call connect() first.")
            return {"error": "Not connected"}

        # Validate tool exists
        if tool_name not in self.tools_cache and not self.tools_cache:
            logger.warning("⚠ Tool cache empty. Run discover_tools() first.")

        try:
            logger.info(f"→ Calling tool: {tool_name}")
            logger.info(f"  Arguments: {json.dumps(arguments, indent=2)}")

            # Send tool call request
            response = await self._send_json_rpc_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })

            if "result" in response:
                result = response["result"]
                logger.info(f"✓ Tool call successful: {tool_name}")
                return result
            elif "error" in response:
                error_msg = response["error"].get("message", "Unknown error")
                logger.error(f"✗ Tool call failed: {error_msg}")
                return {"error": error_msg}
            else:
                logger.error(f"✗ Unexpected response format")
                return {"error": "Unexpected response"}

        except Exception as e:
            logger.error(f"✗ Tool call error: {e}")
            return {"error": str(e)}

    async def _send_json_rpc_request(
        self,
        method: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send JSON-RPC 2.0 request

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            JSON-RPC response
        """
        self.request_id += 1

        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }

        if self.connection:
            response = await self.connection.send_request(request)
        else:
            # Simulate response for demo
            response = self._simulate_response(method, params)

        return response

    def _simulate_response(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate server response (for demo without server)"""
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "File Management & Security Analyzer",
                        "version": "2024.3"
                    }
                }
            }
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "result": {
                    "tools": [
                        {
                            "name": "analyze_file_security",
                            "description": "Analyze security risks in a file",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"file_path": {"type": "string"}}
                            }
                        },
                        {
                            "name": "get_file_metadata",
                            "description": "Retrieve file metadata",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"file_path": {"type": "string"}}
                            }
                        },
                        {
                            "name": "list_directory_contents",
                            "description": "List directory contents",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"directory_path": {"type": "string"}}
                            }
                        }
                    ]
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "result": {"simulated": True, "method": method}
            }


class MCPClientSession:
    """Session manager for MCP client workflows"""

    def __init__(self, client: MCPClient):
        """Initialize session"""
        self.client = client
        self.call_history: List[Dict[str, Any]] = []
        logger.info("✓ MCP Client Session created")

    async def run_workflow(self, workflow_name: str, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run a multi-step workflow

        Args:
            workflow_name: Name of workflow for logging
            steps: List of {tool_name, arguments} dicts

        Returns:
            List of results
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"Workflow: {workflow_name}")
        logger.info(f"{'='*70}\n")

        results = []

        for i, step in enumerate(steps, 1):
            tool_name = step.get("tool_name")
            arguments = step.get("arguments", {})

            logger.info(f"Step {i}: {tool_name}")
            result = await self.client.call_tool(tool_name, arguments)
            results.append(result)
            self.call_history.append({
                "step": i,
                "tool": tool_name,
                "result": result
            })

        logger.info(f"\n✓ Workflow complete: {len(results)} steps executed")
        return results

    def get_history(self) -> List[Dict[str, Any]]:
        """Get call history"""
        return self.call_history


# Example usage and demonstration
async def demo_mcp_client():
    """Demonstrate MCP client capabilities"""

    logger.info("\n" + "█" * 70)
    logger.info("█" + " MCP CLIENT - PART B TASK 2 DEMO ".center(68) + "█")
    logger.info("█" * 70 + "\n")

    # Create client (simulated for demo)
    client = MCPClient()

    # Connect
    logger.info("\n1. CONNECTION")
    logger.info("─" * 70)
    connected = await client.connect()
    if not connected:
        logger.error("Failed to connect (expected in demo mode)")
        logger.info("In production, this would connect to actual server")

    # Discover tools
    logger.info("\n2. TOOL DISCOVERY")
    logger.info("─" * 70)
    tools = await client.discover_tools()

    # Show tool schemas
    logger.info("\n3. TOOL SCHEMAS")
    logger.info("─" * 70)
    for tool in tools:
        logger.info(f"\nTool: {tool['name']}")
        logger.info(f"Description: {tool['description']}")
        logger.info(f"Input Schema: {json.dumps(tool['inputSchema'], indent=2)}")

    # Demonstrate tool calls
    logger.info("\n4. TOOL INVOCATION (Simulated)")
    logger.info("─" * 70)

    # Example 1: Analyze file security
    logger.info("\nExample 1: Analyze File Security")
    result1 = await client.call_tool("analyze_file_security", {
        "file_path": "/etc/passwd",
        "check_permissions": True,
        "check_content": True
    })
    logger.info(f"Result: {json.dumps(result1, indent=2)}")

    # Example 2: Get file metadata
    logger.info("\nExample 2: Get File Metadata")
    result2 = await client.call_tool("get_file_metadata", {
        "file_path": "/home/user/config.json"
    })
    logger.info(f"Result: {json.dumps(result2, indent=2)}")

    # Example 3: List directory contents
    logger.info("\nExample 3: List Directory Contents")
    result3 = await client.call_tool("list_directory_contents", {
        "directory_path": "/home/user",
        "filter_extension": ".py",
        "max_depth": 2
    })
    logger.info(f"Result: {json.dumps(result3, indent=2)}")

    # Demo session workflow
    logger.info("\n5. SESSION WORKFLOW")
    logger.info("─" * 70)

    session = MCPClientSession(client)

    workflow_steps = [
        {
            "tool_name": "get_file_metadata",
            "arguments": {"file_path": "/var/log/syslog"}
        },
        {
            "tool_name": "analyze_file_security",
            "arguments": {"file_path": "/var/log/syslog", "check_permissions": True}
        },
        {
            "tool_name": "list_directory_contents",
            "arguments": {"directory_path": "/var/log", "filter_extension": ".log"}
        }
    ]

    results = await session.run_workflow("Log File Analysis", workflow_steps)

    # Disconnect
    logger.info("\n6. DISCONNECTION")
    logger.info("─" * 70)
    await client.disconnect()

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("MCP Client Implementation Summary:")
    logger.info("=" * 70)
    logger.info(f"✓ Connection management (connect/disconnect)")
    logger.info(f"✓ Tool discovery via JSON-RPC 2.0")
    logger.info(f"✓ Tool invocation with validation")
    logger.info(f"✓ Structured response handling")
    logger.info(f"✓ Session workflow management")
    logger.info(f"✓ Error handling and logging")
    logger.info(f"\n✓ MCP Client implementation complete")
    logger.info(f"✓ Ready for server integration\n")


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_mcp_client())
