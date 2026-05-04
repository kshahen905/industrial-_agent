# Product Requirements Document (PRD)

## Overview

**DevOps Multi-Agent Log Analyzer** is an AI-powered system that analyzes DevOps logs and generates actionable solutions using a multi-agent architecture with Retrieval-Augmented Generation (RAG).

## Problem Statement

DevOps engineers spend significant time:
1. Parsing complex log messages
2. Searching documentation for relevant solutions
3. Manually piecing together troubleshooting steps
4. Generating commands and testing solutions

This system automates these tasks while running entirely locally and offline.

## Solution

A multi-agent AI system using LangGraph orchestration that:
- **Analyzes** logs to identify component, error type, and root causes
- **Retrieves** relevant technical documentation using vector embeddings
- **Generates** step-by-step solutions with specific commands
- **Validates** solutions for accuracy and completeness

## System Architecture

```
User Input (Log Message)
    ↓
Log Analysis Agent (Parse & Identify)
    ↓
Documentation Retriever Agent (Vector Search)
    ↓
Solution Generator Agent (Combine & Generate)
    ↓
Validation Agent (Review & Format)
    ↓
Structured Output (Actions & Commands)
```

## Core Components

### 1. Data Ingestion Pipeline (`ingestion/ingest_data.py`)
- Loads PDF/text documentation
- Splits into chunks
- Generates embeddings using SentenceTransformers
- Stores in ChromaDB vector database

### 2. Tools Module (`tools/tools.py`)
- **VectorSearchTool**: Search ChromaDB for relevant docs
- **LogParsingTool**: Extract component, error type, root cause
- **CommandGeneratorTool**: Generate diagnostic and fix commands

### 3. Agents (`agents/agents_config.py`)
- **Log Analysis Agent**: Parse logs, identify issues
- **Retriever Agent**: Search documentation
- **Solution Generator Agent**: Create solutions
- **Validation Agent**: Verify and format output

### 4. Multi-Agent Graph (`graph/multi_agent_graph.py`)
- LangGraph workflow orchestration
- State passing between agents
- Sequential execution: Analysis → Retrieval → Generation → Validation

### 5. Entry Point (`main.py`)
- Interactive and demo modes
- Environment setup and verification
- System initialization

## Key Features

- ✅ Fully local execution (no internet required)
- ✅ Offline LLM using Ollama
- ✅ Multi-agent collaboration
- ✅ RAG-based information retrieval
- ✅ Structured, actionable output
- ✅ Support for Docker, Python, Linux, Nginx errors
- ✅ Extensible command database
- ✅ Memory persistence with SQLite

## Supported Components

1. **Docker** - Container errors, networking, image pulls
2. **Python** - Import errors, database connections, memory issues
3. **Linux/Systemd** - Service errors, OOM, DNS, SSH
4. **Nginx/Apache** - Connection refused, configuration, processes

## Data Flow

1. **Input**: Raw log message from user
2. **Analyze**: Log Analysis Agent identifies component and error
3. **Retrieve**: Retriever searches vector DB for relevant docs
4. **Generate**: Solution Generator creates solution with commands
5. **Validate**: Validation Agent reviews and formats
6. **Output**: Structured solution with root cause and fix steps

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| LLM | Ollama (local) |
| Orchestration | LangGraph |
| Vector DB | ChromaDB |
| Embeddings | SentenceTransformers |
| Memory | SQLite |
| Testing | PyTest |

## Expected Output Format

```
╔════════════════════════════════════════════════════════════════╗
║           DevOps Log Analysis - Final Recommendation           ║
╚════════════════════════════════════════════════════════════════╝

Component: Docker
Error Type: Port Binding Error

Root Cause:
The port 80 is already in use by another process. Docker cannot bind to this port.

Solution Steps:
1. Identify the process using port 80
2. Determine if it needs to be running
3. Either stop the conflicting process or use a different port
4. Restart the Docker daemon

Commands:
1. List processes using port 80:
   lsof -i :80

2. Restart Docker:
   sudo systemctl restart docker

3. Verify Docker is running:
   docker ps

Documentation Reference: Docker troubleshooting guide - Port Binding Errors

════════════════════════════════════════════════════════════════
```

## Usage Modes

### Interactive Mode
```bash
python main.py
# User enters logs interactively
```

### Demo Mode
```bash
python main.py --demo
# Runs analysis on sample logs
```

### CLI Mode
```bash
python main.py --analyze "Error message here"
# Analyzes specific log
```

## Testing Strategy

1. **Unit Tests** - Individual tool and agent functionality
2. **Integration Tests** - Agent collaboration
3. **Retrieval Tests** - Vector DB accuracy
4. **End-to-End Tests** - Full workflow

## Future Enhancements

- [ ] Multi-language support for logs
- [ ] Real-time log streaming
- [ ] Web UI for visualization
- [ ] Machine learning model training
- [ ] Integration with incident tracking systems
- [ ] Custom documentation upload
- [ ] Feedback loop for model improvement

## Constraints

- Must run on 8 GB RAM + 1 GB GPU locally
- No paid APIs allowed
- Fully offline capability
- Open-source components only
- 5-second response time target

## Success Metrics

- ✓ Correctly identifies issue component
- ✓ Retrieves relevant documentation
- ✓ Generates actionable solutions
- ✓ Solutions resolve the described problem
- ✓ Runs within resource constraints
- ✓ User satisfaction with recommendations
