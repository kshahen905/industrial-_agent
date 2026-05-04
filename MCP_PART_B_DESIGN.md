# MCP Implementation - Part B Documentation

## Overview

This document outlines the standalone MCP (Model Context Protocol) implementation for Part B of the mid-exam.

**Requirement**: Design and implement MCP in an independent use-case of your choice, completely separate from Part A (DevOps Log Analyzer).

**Use Case Selected**: **File Management & Security Analyzer**

A Model Context Protocol server that exposes file analysis tools with clear separation between:
- Model (LLM)
- Context (File metadata and content)
- Tools (File operations)
- Execution Layer (MCP protocol)

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│          MCP CLIENT (Model)                            │
│                                                         │
│  "Analyze security risks in /home/user/documents"      │
└────────────────────────────────────────────────────────┘
                          │
                          │ MCP Protocol
                          │ (JSON-RPC over stdio)
                          ▼
┌────────────────────────────────────────────────────────┐
│          MCP SERVER                                    │
│  (File Management & Security Analyzer)                │
│                                                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Tool 1: analyze_file_security                   │ │
│  │  • Scan for sensitive patterns                  │ │
│  │  • Check permissions                            │ │
│  │  • Detect risky content                        │ │
│  │  • Return security report                       │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Tool 2: get_file_metadata                       │ │
│  │  • File size, creation date, permissions        │ │
│  │  • MIME type detection                          │ │
│  │  • File encoding analysis                       │ │
│  │  • Return metadata JSON                         │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Tool 3: list_directory_contents                 │ │
│  │  • List files in directory                      │ │
│  │  • Filter by type/pattern                       │ │
│  │  • Generate inventory                           │ │
│  │  • Return structured listing                    │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
└────────────────────────────────────────────────────────┘
                          ▲
                          │ MCP Protocol Response
                          │
                          ▼
┌────────────────────────────────────────────────────────┐
│  TOOL EXECUTION LAYER                                 │
│  • Runs actual file operations                        │
│  • OS interaction                                      │
│  • Security checks                                    │
│  • Returns results                                    │
└────────────────────────────────────────────────────────┘
```

---

## Key Design Principles

### **1. Complete Separation of Concerns**

```
┌─────────────────────────────────┐
│ MODEL LAYER                     │
│ • LLM requests tool invocation  │
│ • Understands tool results      │
│ • Makes decisions               │
└─────────────────────────────────┘
           ▲                ▼
           │ MCP Protocol   │
           │                │
┌─────────────────────────────────┐
│ CONTEXT LAYER                   │
│ • Tool definitions              │
│ • Input/output schemas          │
│ • Tool metadata                 │
│ • Structured data formats       │
└─────────────────────────────────┘
           ▲                ▼
           │ MCP Protocol   │
           │                │
┌─────────────────────────────────┐
│ TOOLS LAYER                     │
│ • Concrete tool implementations │
│ • Business logic                │
│ • File operations               │
│ • Error handling                │
└─────────────────────────────────┘
           ▲                ▼
           │ MCP Protocol   │
           │                │
┌─────────────────────────────────┐
│ EXECUTION LAYER                 │
│ • Actual OS operations          │
│ • File system access            │
│ • System calls                  │
│ • Resource management           │
└─────────────────────────────────┘
```

### **2. Tool Exposure via MCP**

**NOT Direct Function Calls**:
```python
# ❌ Direct (what we DON'T do)
from tools import analyze_file_security
result = analyze_file_security("/path/to/file")
```

**INSTEAD - MCP Protocol**:
```python
# ✅ MCP-based (what we DO)
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "analyze_file_security",
        "arguments": {"file_path": "/path/to/file"}
    }
}
```

---

## Tools Definition

### **Tool 1: analyze_file_security**

**Purpose**: Analyze security risks in a file

**Input Schema**:
```json
{
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "Path to file to analyze"
        },
        "check_permissions": {
            "type": "boolean",
            "description": "Whether to check file permissions",
            "default": true
        },
        "check_content": {
            "type": "boolean",
            "description": "Whether to scan content for secrets",
            "default": true
        }
    },
    "required": ["file_path"]
}
```

**Output Schema**:
```json
{
    "type": "object",
    "properties": {
        "file_path": {"type": "string"},
        "security_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "risks_found": {"type": "array", "items": {"type": "string"}},
        "permissions": {"type": "string"},
        "recommendations": {"type": "array", "items": {"type": "string"}}
    }
}
```

---

### **Tool 2: get_file_metadata**

**Purpose**: Retrieve structured file metadata

**Input Schema**:
```json
{
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "Path to file"
        }
    },
    "required": ["file_path"]
}
```

**Output Schema**:
```json
{
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
```

---

### **Tool 3: list_directory_contents**

**Purpose**: List directory contents with filtering

**Input Schema**:
```json
{
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
}
```

**Output Schema**:
```json
{
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
```

---

## Implementation Files to Create

```
Part B MCP Implementation:
├── mcp_server.py
│   └── MCP Server implementation
│       • StdioServerTransport
│       • Tool definitions
│       • Handler functions
│
├── mcp_client.py
│   └── MCP Client implementation
│       • Connection to server
│       • Tool discovery
│       • Tool invocation
│       • Response handling
│
├── tools_impl.py
│   └── Tool implementations
│       • analyze_file_security()
│       • get_file_metadata()
│       • list_directory_contents()
│
├── test_mcp_integration.py
│   └── Integration tests
│       • Server startup
│       • Tool discovery
│       • Tool execution
│       • Protocol compliance
│
└── MCP_TECHNICAL_COMPARISON.md
    └── Comparison document
        • Direct vs LangGraph vs MCP
        • Security, scalability, abstraction
```

---

## Why This Design Matters

### **Direct Invocation (❌ Poor)**
```python
result = analyze_file_security("/home/user/.env")  # Direct call
# Model can call ANY function
# No sandboxing
# Tight coupling
# Hard to scale
```

### **LangGraph Orchestration (✅ Good)**
```
LangGraph manages agent nodes with tools
# Better organization
# Still tight coupling between agent and tools
# Good for single domain
```

### **MCP Protocol (✅✅ Excellent)**
```
Model → MCP Protocol → Server → Tools
# Complete decoupling
# Protocol-based communication
# Server can run anywhere (same machine, remote, cloud)
# Multiple models can share same server
# Easy sandboxing and security
# Production-ready pattern
```

---

## Next Steps

1. ✅ [This Document] Design & planning
2. ⏳ Implement MCP Server (10 marks)
3. ⏳ Implement MCP Client (10 marks)
4. ⏳ Write Technical Comparison (10 marks)

**Total remaining**: 30 marks

