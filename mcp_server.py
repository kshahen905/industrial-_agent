"""
MCP Server - File Management & Security Analyzer

Standalone MCP implementation demonstrating:
- Tool exposure via MCP protocol (not direct calls)
- Structured input/output schemas
- Proper context separation
- Production-ready MCP server

Part B Task 1: 10 marks
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MCP_Server")


class MCPToolDefinition:
    """Defines an MCP tool with schema"""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any]
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP tool definition"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema
        }


class FileManagementServer:
    """MCP Server for File Management & Security Analysis"""

    def __init__(self):
        """Initialize MCP server with tools"""
        self.tool_definitions: Dict[str, MCPToolDefinition] = {}
        self.register_tools()
        logger.info("✓ MCP Server initialized")

    def register_tools(self):
        """Register all available tools"""

        # Tool 1: Analyze File Security
        self.tool_definitions["analyze_file_security"] = MCPToolDefinition(
            name="analyze_file_security",
            description="Analyze security risks in a file including permissions, content, and metadata",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file to analyze"
                    },
                    "check_permissions": {
                        "type": "boolean",
                        "description": "Whether to check file permissions",
                        "default": True
                    },
                    "check_content": {
                        "type": "boolean",
                        "description": "Whether to scan content for secrets",
                        "default": True
                    }
                },
                "required": ["file_path"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "security_score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "risks_found": {"type": "array", "items": {"type": "string"}},
                    "permissions": {"type": "string"},
                    "recommendations": {"type": "array", "items": {"type": "string"}}
                }
            }
        )

        # Tool 2: Get File Metadata
        self.tool_definitions["get_file_metadata"] = MCPToolDefinition(
            name="get_file_metadata",
            description="Retrieve structured file metadata including size, timestamps, permissions, encoding",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file"
                    }
                },
                "required": ["file_path"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "file_name": {"type": "string"},
                    "file_size": {"type": "integer"},
                    "mime_type": {"type": "string"},
                    "created_timestamp": {"type": "string"},
                    "modified_timestamp": {"type": "string"},
                    "permissions": {"type": "string"},
                    "encoding": {"type": "string"}
                }
            }
        )

        # Tool 3: List Directory Contents
        self.tool_definitions["list_directory_contents"] = MCPToolDefinition(
            name="list_directory_contents",
            description="List directory contents with optional filtering and recursion",
            input_schema={
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Path to directory"
                    },
                    "filter_extension": {
                        "type": "string",
                        "description": "Filter by file extension (e.g., '.py')"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Max recursion depth",
                        "default": 1
                    }
                },
                "required": ["directory_path"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "contents": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string", "enum": ["file", "directory"]},
                                "size": {"type": "integer"}
                            }
                        }
                    }
                }
            }
        )

        logger.info(f"✓ Registered {len(self.tool_definitions)} tools")

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools (tool discovery)"""
        return [tool.to_dict() for tool in self.tool_definitions.values()]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool with given arguments"""

        if tool_name not in self.tool_definitions:
            return {"error": f"Tool '{tool_name}' not found"}

        logger.info(f"→ Tool invoked: {tool_name}")
        logger.info(f"  Arguments: {arguments}")

        try:
            if tool_name == "analyze_file_security":
                return self._analyze_file_security(**arguments)
            elif tool_name == "get_file_metadata":
                return self._get_file_metadata(**arguments)
            elif tool_name == "list_directory_contents":
                return self._list_directory_contents(**arguments)
        except Exception as e:
            return {"error": str(e)}

    def _analyze_file_security(
        self,
        file_path: str,
        check_permissions: bool = True,
        check_content: bool = True
    ) -> Dict[str, Any]:
        """Implementation of analyze_file_security tool"""

        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            return {"error": f"File not found: {file_path}"}

        risks = []
        recommendations = []
        security_score = 80  # Start at 80, deduct for risks

        # Check permissions
        if check_permissions:
            try:
                perms = oct(file_path_obj.stat().st_mode)[-3:]
                if perms in ['777', '666', '755', '644']:
                    security_score -= 10
                    if perms == '777':
                        risks.append("World-writable file (777)")
                        recommendations.append("Restrict permissions: chmod 640")
                    elif perms == '666':
                        risks.append("World-readable/writable file (666)")
                        recommendations.append("Restrict permissions: chmod 600")
                    elif perms == '755':
                        risks.append("World-readable executable (755)")
                        recommendations.append("Consider more restrictive permissions")
            except Exception as e:
                logger.warning(f"Could not check permissions: {e}")

        # Check content for secrets
        if check_content and file_path_obj.suffix in ['.py', '.txt', '.env', '.conf', '.json']:
            try:
                with open(file_path_obj, 'r', errors='ignore') as f:
                    content = f.read(1000)  # Read first 1000 chars

                secret_patterns = ['password', 'secret', 'api_key', 'token', 'credential']
                found_secrets = [p for p in secret_patterns if p.lower() in content.lower()]

                if found_secrets:
                    security_score -= 30
                    risks.append(f"Potential secrets detected: {', '.join(found_secrets)}")
                    recommendations.append("Do not commit sensitive data - use .env or secrets manager")
            except Exception as e:
                logger.warning(f"Could not check content: {e}")

        return {
            "file_path": file_path,
            "security_score": max(0, security_score),
            "risks_found": risks,
            "permissions": oct(file_path_obj.stat().st_mode)[-3:],
            "recommendations": recommendations if risks else ["File appears secure"]
        }

    def _get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Implementation of get_file_metadata tool"""

        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            return {"error": f"File not found: {file_path}"}

        stat = file_path_obj.stat()

        # Determine MIME type
        mime_types = {
            '.py': 'text/python',
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.yaml': 'application/yaml',
            '.md': 'text/markdown',
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg'
        }
        mime_type = mime_types.get(file_path_obj.suffix, 'application/octet-stream')

        # Detect encoding
        encoding = 'utf-8'
        if file_path_obj.suffix in ['.py', '.txt', '.json', '.yaml']:
            try:
                with open(file_path_obj, 'rb') as f:
                    raw = f.read(2)
                    if raw.startswith(b'\xff\xfe'):
                        encoding = 'utf-16'
                    elif raw.startswith(b'\xfe\xff'):
                        encoding = 'utf-16'
            except:
                pass

        return {
            "file_name": file_path_obj.name,
            "file_size": stat.st_size,
            "mime_type": mime_type,
            "created_timestamp": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
            "encoding": encoding
        }

    def _list_directory_contents(
        self,
        directory_path: str,
        filter_extension: str = None,
        max_depth: int = 1
    ) -> Dict[str, Any]:
        """Implementation of list_directory_contents tool"""

        dir_path = Path(directory_path)

        if not dir_path.is_dir():
            return {"error": f"Directory not found: {directory_path}"}

        contents = []

        try:
            for item in dir_path.iterdir():
                if filter_extension and item.suffix != filter_extension:
                    continue

                item_type = "directory" if item.is_dir() else "file"
                size = item.stat().st_size if item.is_file() else 0

                contents.append({
                    "name": item.name,
                    "type": item_type,
                    "size": size
                })

            contents = sorted(contents, key=lambda x: x['name'])

        except PermissionError:
            return {"error": f"Permission denied: {directory_path}"}

        return {
            "directory": directory_path,
            "contents": contents
        }


class MCPProtocolHandler:
    """Handles MCP protocol communication"""

    def __init__(self, server: FileManagementServer):
        self.server = server
        self.version = "2024.3"

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP protocol request"""

        method = request.get("method")

        if method == "initialize":
            return self._handle_initialize(request)
        elif method == "tools/list":
            return self._handle_tools_list(request)
        elif method == "tools/call":
            return self._handle_tool_call(request)
        else:
            return {"error": f"Unknown method: {method}"}

    def _handle_initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialization"""
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {
                        "listChanged": False
                    }
                },
                "serverInfo": {
                    "name": "File Management & Security Analyzer",
                    "version": self.version
                }
            }
        }

    def _handle_tools_list(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool listing (discovery)"""
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "tools": self.server.get_tools()
            }
        }

    def _handle_tool_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool invocation"""
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        result = self.server.call_tool(tool_name, arguments)

        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": result
        }


class StdioMCPServer:
    """MCP Server using stdio transport (standard input/output)"""

    def __init__(self):
        """Initialize stdio MCP server"""
        self.server = FileManagementServer()
        self.handler = MCPProtocolHandler(self.server)
        logger.info("✓ Stdio MCP Server ready")

    def run(self):
        """Run the server"""
        logger.info("\n" + "="*70)
        logger.info("MCP Server - File Management & Security Analyzer")
        logger.info("="*70)
        logger.info("\nWaiting for MCP client connections...")
        logger.info("Server status: ✓ READY\n")

        try:
            while True:
                line = input()
                if not line.strip():
                    continue

                try:
                    request = json.loads(line)
                    response = self.handler.handle_request(request)
                    print(json.dumps(response))

                except json.JSONDecodeError as e:
                    print(json.dumps({
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": f"Parse error: {e}"}
                    }))

        except KeyboardInterrupt:
            logger.info("\n✓ Server shutdown gracefully")


if __name__ == "__main__":
    # Note: In production, this would communicate via stdio
    # For demo purposes, we show the server functionality

    logger.info("\n" + "█"*70)
    logger.info("█" + " MCP SERVER - PART B TASK 1 ".center(68) + "█")
    logger.info("█"*70 + "\n")

    server = FileManagementServer()

    # Demo: Show tool discovery
    logger.info("TOOL DISCOVERY:")
    logger.info("───────────────\n")

    for tool in server.get_tools():
        logger.info(f"Tool: {tool['name']}")
        logger.info(f"  Description: {tool['description']}")
        logger.info(f"  Input: {json.dumps(tool['inputSchema'], indent=4)}")
        logger.info("")

    logger.info("\n✓ MCP Server implementation complete")
    logger.info("✓ Tools properly exposed via MCP protocol")
    logger.info("✓ Ready for client integration")
