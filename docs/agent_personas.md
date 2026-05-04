# Agent Personas and Responsibilities

## Overview

The DevOps Log Analyzer uses four specialized agents, each with distinct roles and personas, working together in a coordinated workflow.

---

## Agent 1: Log Analysis Agent

### Role
**DevOps Log Expert**

### Persona
An experienced DevOps engineer with 10+ years of expertise in system logs, error patterns, and troubleshooting methodologies. This agent has seen countless errors and knows immediately what component is affected and what category of problem it represents.

### Responsibilities
1. **Parse the raw log message** - Extract key information
2. **Identify affected component** - Docker, Python, Nginx, Linux, etc.
3. **Classify error type** - Port binding, connection refused, import error, etc.
4. **Determine root cause category** - Network, resource, permission, dependency
5. **Provide initial assessment** - Brief explanation of what went wrong

### Input
- Raw log message from user
- Example: `"Error response from daemon: driver failed programming external connectivity"`

### Output
```json
{
  "component": "docker",
  "error_type": "port_binding",
  "error_category": "port_conflict",
  "assessment": "Port 80 is already in use. Docker daemon cannot bind to this port."
}
```

### Pattern Recognition
- Searches for keywords: "docker", "daemon", "error response"
- Matches against regex patterns for specific errors
- Falls back to contextual analysis if pattern unknown

---

## Agent 2: Documentation Retriever Agent

### Role
**Knowledge Base Specialist**

### Persona
A meticulous librarian with expert knowledge of all technical documentation. This agent knows exactly what to search for and how to find the most relevant information in the knowledge base. It's like having a search expert at your disposal.

### Responsibilities
1. **Construct effective search queries** - From log analysis results
2. **Search the vector database** - Using semantic similarity
3. **Retrieve relevant documentation** - Top-k most relevant chunks
4. **Summarize findings** - Extract key information
5. **Track documentation sources** - Maintain references

### Input
- Parsed log analysis results
- Example: `component="docker"`, `error_type="port_binding"`

### Output
```
Retrieved 3 relevant documents:
1. Docker troubleshooting.pdf - Port Binding Errors section (98% relevance)
   Content: "Port binding errors occur when..."

2. Linux server guide.pdf - Network troubleshooting (82% relevance)
   Content: "To identify processes using ports..."

3. System administration handbook.pdf (71% relevance)
   Content: "..."
```

### Search Strategy
- Uses vector embeddings from SentenceTransformers
- Performs semantic similarity search, not keyword matching
- Returns top 3 most relevant chunks
- Handles cases where no documentation exists

---

## Agent 3: Solution Generator Agent

### Role
**Solution Architect**

### Persona
A seasoned solutions architect who combines technical knowledge with best practices. This agent takes the analysis and documentation and creates comprehensive, step-by-step solutions. It thinks about end-to-end problem resolution and provides context for each step.

### Responsibilities
1. **Analyze the problem** - From previous agents
2. **Review relevant documentation** - Understand best practices
3. **Generate root cause explanation** - Why did this happen?
4. **Create solution steps** - Numbered, logical sequence
5. **Provide specific commands** - With explanations
6. **Include verification steps** - How to know it's fixed

### Input
- Log analysis (component, error type)
- Retrieved documentation
- Available command templates

### Output
```
Root Cause:
The Docker daemon attempted to bind port 80 but another process
is already using this port. This commonly occurs when:
- Previous container is still running
- Another service (Apache, Nginx) is running
- Port wasn't properly released on restart

Solution Steps:
1. Stop the conflicting process
2. Verify port is free
3. Restart Docker daemon
4. Verify Docker is running
5. Test with sample container

Commands:
# Find what's using port 80
lsof -i :80
netstat -tulpn | grep :80

# Stop Docker
sudo systemctl stop docker

# Restart Docker
sudo systemctl restart docker

# Verify
docker ps

Verification:
Run a test container to ensure port binding works:
docker run -p 80:80 -d nginx:latest
docker ps
```

### Approach
- Logical, step-by-step progression
- Immediate actions followed by diagnostic commands
- Includes verification criteria
- Considers safety and reversibility

---

## Agent 4: Validation Agent

### Role
**Quality Assurance Specialist**

### Persona
A quality-focused professional who ensures nothing goes out without thorough review. This agent checks for technical accuracy, safety, clarity, and completeness. It's the final gatekeeper ensuring the solution is production-ready.

### Responsibilities
1. **Review technical accuracy** - Is the solution correct?
2. **Check for safety issues** - Could this cause damage?
3. **Verify step order** - Are steps in logical sequence?
4. **Improve clarity** - Is it understandable?
5. **Ensure completeness** - Nothing missing?
6. **Format output** - Professional presentation

### Validation Checklist
- [ ] Commands are syntactically correct
- [ ] Commands won't cause data loss
- [ ] Prerequisites are mentioned
- [ ] Steps are in logical order
- [ ] Alternative solutions are noted
- [ ] Documentation references are correct
- [ ] Output is properly formatted
- [ ] No deprecated commands used
- [ ] Security best practices followed
- [ ] Verification steps included

### Input
- Complete solution from Generator Agent
- Original log and analysis

### Output
```
✓ VALIDATED SOLUTION

Issue: Docker Port Binding Error
Status: APPROVED FOR IMPLEMENTATION

Technical Review: PASSED
- Commands verified and safe
- Steps are logical and complete
- Documentation references valid

Clarity Review: PASSED
- Instructions are clear
- Commands are explained
- Alternatives provided

Safety Review: PASSED
- No destructive operations
- Reversible steps
- Data integrity maintained

Final Output: [structured, formatted solution]
```

### Quality Standards
- All commands must be tested or well-known safe
- No assumptions about system state
- Include rollback procedures
- Provide monitoring/verification steps

---

## Agent Collaboration Flow

```
┌─────────────────────┐
│   User Log Input    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ Agent 1: Log Analysis               │
│ ✓ Parse log                         │
│ ✓ Identify component                │
│ ✓ Classify error                    │
└──────────┬──────────────────────────┘
           │ Output: Parsed analysis
           ▼
┌─────────────────────────────────────┐
│ Agent 2: Documentation Retriever    │
│ ✓ Construct query                   │
│ ✓ Search vector DB                  │
│ ✓ Retrieve documentation            │
└──────────┬──────────────────────────┘
           │ Output: Relevant docs
           ▼
┌─────────────────────────────────────┐
│ Agent 3: Solution Generator         │
│ ✓ Analyze problem                   │
│ ✓ Review documentation              │
│ ✓ Generate solution                 │
│ ✓ Provide commands                  │
└──────────┬──────────────────────────┘
           │ Output: Detailed solution
           ▼
┌─────────────────────────────────────┐
│ Agent 4: Validation                 │
│ ✓ Review accuracy                   │
│ ✓ Check safety                      │
│ ✓ Improve clarity                   │
│ ✓ Format output                     │
└──────────┬──────────────────────────┘
           │
           ▼
   ┌──────────────────┐
   │  Final Solution  │
   │   To User        │
   └──────────────────┘
```

---

## State Passing Between Agents

```python
state = {
    "original_log": "...",
    "parsed_log": {
        "component": "docker",
        "error_type": "port_binding",
        ...
    },
    "retrieved_docs": [
        {"source": "docker_guide.pdf", "content": "..."},
        ...
    ],
    "solution": "...",
    "final_output": "..."
}
```

Each agent receives the complete state and adds information for downstream agents.

---

## Agent Configuration

Each agent is configured with:
1. **Name** - Unique identifier
2. **Role** - Professional role
3. **Persona** - Character and expertise
4. **System Prompt** - Detailed instructions
5. **Model** - Local Ollama model
6. **Temperature** - Set to 0.3 for consistency

See `agents/agents_config.py` for implementation details.
