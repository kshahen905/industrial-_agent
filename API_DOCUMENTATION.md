# API Layer Documentation - Lab 6

## Overview

The API Layer transforms the local DevOps Log Analyzer into a production-ready Web Service using **FastAPI** and **LangServe**. This allows external applications (web frontends, mobile apps, other services) to communicate with the multi-agent system via REST API.

## Architecture

```
External Client (Web/Mobile/API)
        ↓ HTTP(S)
    FastAPI Server
        ↓
    Endpoint Handler
        ↓
    Graph Invocation (with thread_id)
        ↓
    LangGraph Multi-Agent System
        ↓
    SQLite Checkpointer (Persistence)
        ↓
    Return Response
        ↓
    Client receives:
    - Synchronous: Complete ChatResponse
    - Streaming: Server-Sent Events (SSE)
```

## Key Features

### 1. **RESTful Architecture**
- Standard HTTP methods (GET, POST)
- Proper status codes (200, 400, 422, 500, 503)
- Resource-based endpoints
- Clear request/response contracts

### 2. **State Persistence (Stateful HTTP)**
- Thread-based session management using `thread_id`
- SQLiteSaver checkpointer maintains conversation history
- Resume sessions by providing previous `thread_id`
- Graph configured with persistence layer at startup

### 3. **Asynchronous Streaming**
- **Server-Sent Events (SSE)** for real-time updates
- Node-by-node streaming of agent outputs
- Compatible with modern web frameworks
- Solves latency problem (10-30s → progressive updates)

### 4. **Production Ready**
- CORS middleware for web frontend compatibility
- Error handling with structured responses
- Health checks for monitoring
- Comprehensive logging

## Installation

### Prerequisites
- Python 3.8+
- Ollama running locally (`ollama serve`)
- DevOps Log Analyzer dependencies

### Install API Dependencies

```bash
cd ai-devops-log-analyzer

# Install FastAPI and related packages
pip install -r requirements.txt

# Should include:
# - fastapi>=0.104.0
# - uvicorn>=0.24.0
# - python-multipart>=0.0.6
# - aiofiles>=23.2.0
```

## Running the Server

### Development Mode

```bash
# Using uvicorn directly
python -m uvicorn main_api:app --host 0.0.0.0 --port 8000 --reload

# Or using Python script entry point
python main_api.py
```

### Production Mode

```bash
# Using gunicorn with multiple workers
gunicorn main_api:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 60
```

### Startup Output

```
======================================================================
🚀 FastAPI Application Starting
======================================================================
Initializing Persistent Memory Manager...
✓ Checkpointer initialized and ready for graph compilation
Initializing Agent Factory with model: orca-mini
Creating multi-agent LangGraph...
Compiling graph with SQLiteSaver checkpointer...
✓ All components initialized successfully
======================================================================
✅ FastAPI Application Ready
======================================================================
```

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Purpose:** Monitor system status and component availability

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "llm_available": true,
  "vector_db_available": true,
  "checkpointer_initialized": true
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

### 2. Synchronous Chat

**Endpoint:** `POST /chat`

**Purpose:** Synchronous analysis (wait for complete response)

**Request:**
```json
{
  "message": "ERROR: Docker container failed to start - port 8080 already in use",
  "thread_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "final_answer": "╔════════════════════════════════════════╗\n║ DevOps Log Analysis - Final Recommendation ║\n╚════════════════════════════════════════╝\n\nComponent: Docker\nError Type: Port binding error\n\nRoot Cause: Port 8080 is already in use by another process\n\nSolution Steps:\n1. Identify the process using port 8080\n   lsof -i :8080\n2. Kill the existing process\n   kill -9 <PID>\n3. Verify port is free\n   netstat -an | grep 8080\n4. Restart Docker container",
  "analysis_metadata": {
    "component": "Docker",
    "error_type": "Port binding error",
    "error_category": "Resource conflict",
    "timestamp": "2024-04-27T10:30:00Z"
  },
  "processing_time_seconds": 12.5,
  "node_outputs": [
    "Log Analyzer: Identified Docker component...",
    "Retriever: Retrieved 3 relevant Docker documentation files",
    "Solution Generator: Generated step-by-step solution",
    "Validator: Solution validated and formatted"
  ]
}
```

**Response Time:** 10-30 seconds (full analysis)

**Example:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "ERROR: Docker container failed - port 8080 already in use",
    "thread_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

---

### 3. Streaming Chat (SSE)

**Endpoint:** `POST /stream`

**Purpose:** Stream analysis results in real-time using Server-Sent Events

**Query Parameters:**
- `message` (required): Log or issue to analyze
- `thread_id` (optional): Resume existing session; auto-generated if omitted

**Response Format:** Server-Sent Events (SSE)

Each event is JSON formatted:
```
data: {"type": "start", "content": "Analysis started", "node_name": "system"}
data: {"type": "node", "content": "Log Analyzer: Identified Docker...", "node_name": "log_analysis"}
data: {"type": "token", "content": "Root Cause: Port 8080..."}
data: {"type": "end", "content": "Analysis completed successfully"}
```

**Event Types:**
- `start`: Analysis initialized
- `node`: Agent node output
- `token`: Chunk of final answer
- `metadata`: Analysis metadata
- `end`: Analysis complete
- `error`: Stream error

**Example:**
```bash
# Using curl with SSE support
curl -N http://localhost:8000/stream \
  "?message=ERROR:%20Docker%20port%20binding&thread_id=550e8400-e29b-41d4-a716-446655440000"

# Using JavaScript (frontend)
const eventSource = new EventSource('/stream?message=...');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`[${data.type}] ${data.content}`);
};
```

---

### 4. List Sessions

**Endpoint:** `GET /sessions`

**Purpose:** List all saved conversation threads

**Response:**
```json
{
  "total_sessions": 5,
  "thread_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001",
    "770e8400-e29b-41d4-a716-446655440002"
  ]
}
```

**Example:**
```bash
curl http://localhost:8000/sessions
```

---

### 5. Get Session Details

**Endpoint:** `GET /sessions/{thread_id}`

**Purpose:** Retrieve checkpoint and metadata for a specific session

**Response:**
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-04-27T10:00:00Z",
  "last_updated": "2024-04-27T10:30:00Z",
  "checkpoint_count": 3,
  "messages": [...]
}
```

**Example:**
```bash
curl http://localhost:8000/sessions/550e8400-e29b-41d4-a716-446655440000
```

---

## Schema Documentation

### ChatRequest

**Fields:**
- `message` (string, required): DevOps log or issue description
  - Min length: 1
  - Max length: 5000
  - Example: "ERROR: Docker container failed to start"

- `thread_id` (string, optional): Unique conversation ID
  - Auto-generated UUID if not provided
  - Use existing thread_id to continue conversation
  - Example: "550e8400-e29b-41d4-a716-446655440000"

### ChatResponse

**Fields:**
- `thread_id` (string): The thread ID for follow-up requests
- `status` (string): "success" | "processing" | "error"
- `final_answer` (string): Complete solution from multi-agent system
- `analysis_metadata` (AnalysisMetadata): Parsed issue details
  - `component`: Identified system component
  - `error_type`: Classified error type
  - `error_category`: Category for solutions
  - `timestamp`: When analysis was performed
- `processing_time_seconds` (float): Total execution time
- `node_outputs` (array): Messages from each agent in workflow

### StreamToken

**Fields:**
- `type` (string): Event type (start, token, node, metadata, end, error)
- `content` (string): Event content
- `node_name` (string, optional): Name of executing agent node
- `timestamp` (string): ISO format timestamp

### HealthResponse

**Fields:**
- `status` (string): "healthy" | "degraded"
- `version` (string): API version
- `llm_available` (boolean): LLM connection status
- `vector_db_available` (boolean): Vector database status
- `checkpointer_initialized` (boolean): Persistence layer status

## State Persistence & Thread Management

### How It Works

1. **Initial Request:**
   ```python
   POST /chat
   {
     "message": "ERROR: port 8080 in use",
     "thread_id": "thread-123"  # Can be UUIv4
   }
   ```

2. **Graph Execution with Config:**
   ```python
   config = {"configurable": {"thread_id": "thread-123"}}
   result = graph.invoke(initial_state, config=config)
   ```

3. **SQLiteSaver Checkpointing:**
   - Loads previous state if thread exists
   - Executes all nodes with current state
   - Saves final state with thread_id checkpoint

4. **Resume Session:**
   ```python
   # Next request with same thread_id
   POST /chat
   {
     "message": "Follow-up question",
     "thread_id": "thread-123"
   }
   # Graph loads previous state from checkpoint database
   ```

### Thread ID Best Practices

**Generate new UUID:**
```python
from uuid import uuid4
thread_id = str(uuid4())
```

**Resume conversation:**
```python
# Use the same thread_id from previous response
thread_id = response["thread_id"]
# Send follow-up request with same thread_id
```

**Retrieve previous sessions:**
```bash
curl http://localhost:8000/sessions
# List all threads with saved checkpoints
```

## Testing

### Run Test Suite

```bash
# Install test dependencies
pip install requests

# Run comprehensive API tests
python test_api.py
```

### Manual Testing with curl

**Health Check:**
```bash
curl http://localhost:8000/health | python -m json.tool
```

**Synchronous Request:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "ERROR: Connection refused to database",
    "thread_id": "test-thread-123"
  }' | python -m json.tool
```

**Streaming Request:**
```bash
curl -N 'http://localhost:8000/stream?message=ERROR:%20port%2080%20in%20use'
```

### Test Results File

After running tests, results are saved to `api_test_results.txt`:

```
DevOps Log Analyzer - API Test Results
======================================================================

Test Date: 2024-04-27 10:30:00
Base URL: http://localhost:8000
Overall Result: PASSED

Endpoints Tested:
- GET /health
- POST /chat
- POST /stream
- GET /sessions
- Error handling tests

Requirements Met:
✓ Schema validation with Pydantic models
✓ State integration with thread_id persistence
✓ Streaming responses with Server-Sent Events (SSE)
✓ Checkpointer initialization at application startup
✓ RESTful architecture with proper HTTP semantics
```

## Error Handling

### Validation Errors (422)

```json
{
  "error": "ValidationError",
  "message": "Invalid request parameters",
  "details": [
    {
      "loc": ["message"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any.min_length"
    }
  ]
}
```

### Not Found (404)

```json
{
  "error": "NotFound",
  "message": "Session thread-123 not found"
}
```

### Service Unavailable (503)

```json
{
  "error": "ServiceUnavailable",
  "message": "Service not ready. Graph initialization failed."
}
```

### Server Error (500)

```json
{
  "error": "InternalServerError",
  "message": "Analysis failed: <details>"
}
```

## Performance Considerations

### Latency

- **Synchronous (/chat):** 10-30 seconds
  - Log parsing: ~1s
  - Vector search: ~2s
  - LLM inference (3 agents): ~15-25s
  - Total: ~10-30s

- **Streaming (/stream):** Same total, but progressive updates
  - Client sees results as they appear
  - Better user experience for long-running tasks

### Concurrency

- FastAPI supports async/await throughout
- Each request is independent with its own thread_id
- Multiple concurrent requests are supported
- SQLiteSaver handles concurrent checkpointing

### Memory

- Model loaded once at startup
- Vector DB in memory (Chromadb)
- Checkpoints stored in SQLite file (~small constant memory)
- Each request: ~50-100MB temporary memory

## Advanced Usage

### Frontend Integration

**Streaming with JavaScript:**
```javascript
async function analyzeLog(log) {
  const response = await fetch('/stream', {
    method: 'POST',
    body: new URLSearchParams({
      message: log,
      thread_id: generateOrReusThreadId()
    })
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    // Parse SSE and update UI
    updateUI(chunk);
  }
}
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "uvicorn", "main_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### Server won't start

**Issue:** Port 8000 already in use
```bash
# Use different port
python -m uvicorn main_api:app --port 8001
```

**Issue:** LLM not available
```bash
# Start Ollama service
ollama serve

# In another terminal, pull a model
ollama pull orca-mini
```

### Requests timing out

**Issue:** LLM inference takes >30s
```bash
# Solution 1: Increase timeout
curl --max-time 60 http://localhost:8000/chat ...

# Solution 2: Use a faster model
# Edit config.py: DEFAULT_MODEL = "orca-mini"
```

### Persistence not working

**Issue:** States not saved across requests
```bash
# Check database file exists
ls -la checkpoint_db.sqlite

# Verify checkpointer is initialized
# Check startup logs for "✓ Checkpointer initialized"
```

## Submission Checklist

✓ **schema.py** - Pydantic models for ChatRequest and ChatResponse
✓ **main_api.py** - FastAPI script with POST /chat and POST /stream endpoints
✓ **api_test_results.txt** - Output of successful curl/test requests
✓ **State Integration** - Thread_id passed to graph.invoke() with config
✓ **Persistence** - Checkpointer initialized via lifespan, compiled with graph
✓ **Streaming** - SSE format with node-by-node updates
✓ **Documentation** - This file with architecture, examples, and troubleshooting

## Files Modified

- `schema.py` (new) - Request/response validation schemas
- `main_api.py` (new) - FastAPI server with all endpoints
- `requirements.txt` - Added FastAPI dependencies
- `test_api.py` (new) - Comprehensive test suite

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [LangGraph Checkpointing](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [RESTful API Design](https://restfulapi.net/)

---

**Lab 6 Complete!** ✅
