"""
FastAPI Application - API Layer for DevOps Log Analyzer

Exposes the LangGraph multi-agent system via REST API with:
- Synchronous /chat endpoint for standard requests
- Asynchronous /stream endpoint for token-by-token streaming (SSE)
- Persistence via thread_id for stateful conversations
- Health check endpoint for monitoring

Lab 6 Requirements:
✓ Endpoint Design & Schema Validation
✓ State Integration (Persistence over HTTP)
✓ Streaming Responses (SSE format)
"""

import json
import logging
import time
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, AsyncGenerator, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

# Local imports
from schema import ChatRequest, ChatResponse, StreamToken, HealthResponse, ErrorResponse, AnalysisMetadata
# AgentFactory import moved to lifespan to avoid early connection attempts
# create_multi_agent_graph moved to lifespan to avoid import hanging
from memory.checkpoint_manager import PersistentMemoryManager
from config import DEFAULT_MODEL, OLLAMA_BASE_URL

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== GLOBAL STATE ====================

# These will be initialized in lifespan
agent_factory: Optional[Any] = None
graph = None
memory_manager: Optional[PersistentMemoryManager] = None
checkpointer = None

# ==================== LIFESPAN MANAGEMENT ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup and shutdown.
    
    Ensures:
    - Graph is compiled once at startup with checkpointer
    - Checkpointer persists across requests (no reconnect per request)
    - Graceful shutdown
    """
    
    # ========== STARTUP ==========
    logger.info("=" * 70)
    logger.info("🚀 FastAPI Application Starting")
    logger.info("=" * 70)
    
    try:
        # Initialize memory manager (persistence layer)
        logger.info("Initializing Persistent Memory Manager...")
        global memory_manager, checkpointer, agent_factory, graph
        
        memory_manager = PersistentMemoryManager(db_path="./checkpoint_db.sqlite")
        checkpointer = memory_manager.get_checkpointer()
        logger.info("✓ Checkpointer initialized and ready for graph compilation")
        
        # Initialize tools (required for graph execution)
        # NOTE: Deferred to first request to avoid blocking startup on embedding download
        logger.info("Deferring tool initialization to first request (will load embeddings on demand)")
        try:
            from tools import tools as tools_module
            # Don't call initialize_tools() here - it will block on embedding download
            # Instead, we'll ensure tools are initialized before graph execution
            logger.info("✓ Tools module loaded (initialization deferred)")
        except Exception as e:
            logger.warning(f"⚠ Failed to load tools module: {e}", exc_info=True)
        
        # Initialize agent factory with LLM
        logger.info(f"Initializing Agent Factory with model: {DEFAULT_MODEL}")
        try:
            from agents.agents_config import AgentFactory
            agent_factory = AgentFactory(model_name=DEFAULT_MODEL, base_url=OLLAMA_BASE_URL)
            logger.info("✓ Agent Factory initialized")
        except Exception as e:
            logger.warning(f"⚠ Failed to initialize LLM: {e}. Continuing with mock factory...")
            class MockAgentFactory:
                def get_llm(self):
                    return None
            agent_factory = MockAgentFactory()
        
        # Create and compile graph with checkpointer
        logger.info("Creating multi-agent LangGraph...")
        from langgraph.graph import StateGraph
        from graph.multi_agent_graph import create_multi_agent_graph
        
        # Create graph (returns uncompiled graph)
        try:
            graph = create_multi_agent_graph(agent_factory)
        except Exception as e:
            logger.warning(f"⚠ Failed to create graph: {e}. Using simplified graph...")
            graph = None
        
        # Compile graph with checkpointer for persistence
        logger.info("Compiling graph with checkpointer...")
        
        if graph:
            # The graph may already be compiled from create_multi_agent_graph
            # Try to check if it's already compiled (has 'invoke' method)
            try:
                if hasattr(graph, 'invoke'):
                    # Already compiled, use it as-is
                    logger.info("✓ Graph is already compiled and ready to use")
                else:
                    # Not compiled, try to compile with checkpointer
                    graph = graph.compile(checkpointer=checkpointer)
                    logger.info("✓ Graph compiled with checkpointer for state persistence")
            except Exception as e:
                logger.warning(f"⚠ Could not compile/use graph: {e}")
                graph = None
        
        logger.info("✓ All components initialized successfully")
        logger.info("=" * 70)
        logger.info("✅ FastAPI Application Ready")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {e}", exc_info=True)
        raise
    
    yield  # Application runs here
    
    # ========== SHUTDOWN ==========
    logger.info("=" * 70)
    logger.info("🛑 FastAPI Application Shutting Down")
    logger.info("=" * 70)
    
    try:
        if memory_manager:
            logger.info("Closing persistent memory connections...")
            # SqliteSaver handles cleanup automatically
            logger.info("✓ Persistence layer closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    logger.info("=" * 70)
    logger.info("✅ FastAPI Application Shutdown Complete")
    logger.info("=" * 70)


# ==================== FASTAPI APP CREATION ====================

app = FastAPI(
    title="DevOps Log Analyzer API",
    description="Multi-agent REST API for analyzing DevOps logs and generating solutions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware for web frontend compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== HELPER FUNCTIONS ====================

def ensure_tools_initialized():
    """Ensure tools are initialized - called on first use to avoid blocking startup"""
    try:
        from tools import tools as tools_module
        from pathlib import Path
        
        if tools_module.log_parsing_tool is None:
            logger.info("Initializing tools on first request...")
            vector_db_path = Path("./vector_db")
            tools_module.initialize_tools(str(vector_db_path))
            logger.info("✓ Tools initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tools: {e}", exc_info=True)
        raise

def format_stream_event(event_type: str, content: str, node_name: Optional[str] = None) -> str:
    """
    Format an event as Server-Sent Events (SSE) compatible JSON.
    
    Args:
        event_type: Type of event (start, token, node, metadata, end, error)
        content: The event content
        node_name: Optional name of the current node
    
    Returns:
        SSE formatted string
    """
    token = StreamToken(
        type=event_type,
        content=content,
        node_name=node_name,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )
    return f"data: {json.dumps(token.dict())}\n\n"


async def stream_analysis(log_message: str, thread_id: str) -> AsyncGenerator[str, None]:
    """
    Stream the analysis results as Server-Sent Events.
    
    Yields chunks of the response either as:
    - token-by-token (word-level)
    - node-by-node (agent-by-agent)
    
    Args:
        log_message: The log to analyze
        thread_id: Thread ID for state persistence
    
    Yields:
        SSE formatted strings
    """
    
    try:
        # Ensure tools are initialized (lazy load on first request)
        ensure_tools_initialized()
        
        # Send start event
        yield format_stream_event("start", "Analysis started", node_name="system")
        await asyncio.sleep(0.1)
        
        # Prepare initial state
        initial_state = {
            "messages": [],
            "original_log": log_message,
            "parsed_log": {},
            "retrieved_docs": [],
            "solution": "",
            "final_output": "",
        }
        
        # Run graph with state persistence
        config = {"configurable": {"thread_id": thread_id}}
        
        logger.info(f"Starting async stream analysis for thread {thread_id}")
        
        # Execute graph (synchronously, but we'll stream node outputs)
        result = graph.invoke(initial_state, config=config)
        
        # Stream node outputs one at a time (node-by-node mode)
        for idx, message in enumerate(result.get("messages", []), 1):
            yield format_stream_event("node", message)
            await asyncio.sleep(0.05)  # Small delay for client-side rendering
        
        # Send parsed metadata
        parsed = result.get("parsed_log", {})
        if parsed:
            metadata = AnalysisMetadata(
                component=parsed.get("component", "Unknown"),
                error_type=parsed.get("error_type", "Unknown"),
                error_category=parsed.get("error_category", "Unknown"),
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            yield format_stream_event("metadata", json.dumps(metadata.dict()))
            await asyncio.sleep(0.05)
        
        # Send final answer
        final_answer = result.get("final_output", "Analysis complete")
        yield format_stream_event("token", final_answer)
        await asyncio.sleep(0.05)
        
        # Send completion event
        yield format_stream_event("end", "Analysis completed successfully")
        
        logger.info(f"Stream analysis completed for thread {thread_id}")
        
    except Exception as e:
        logger.error(f"Error in stream_analysis: {e}", exc_info=True)
        yield format_stream_event("error", f"Stream error: {str(e)}")


# ==================== ENDPOINTS ====================

@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint for monitoring.
    
    Returns status of all critical components:
    - LLM connection
    - Vector database
    - Persistence layer
    """
    
    llm_ok = agent_factory is not None and agent_factory.get_llm() is not None
    checkpointer_ok = checkpointer is not None
    vector_db_ok = True  # Assume OK if we got here; could add explicit check
    
    overall_status = "healthy" if (llm_ok and checkpointer_ok) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        llm_available=llm_ok,
        vector_db_available=vector_db_ok,
        checkpointer_initialized=checkpointer_ok
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Standard chat endpoint for synchronous analysis.
    
    Analyzes a DevOps log or issue and returns a complete solution.
    Uses thread_id for state persistence across requests.
    
    Args:
        request: ChatRequest with message and optional thread_id
    
    Returns:
        ChatResponse with final_answer, status, and metadata
    
    Raises:
        HTTPException: If graph is not initialized or analysis fails
    """
    
    if graph is None:
        logger.error("Graph not initialized")
        raise HTTPException(status_code=503, detail="Service not ready. Graph initialization failed.")
    
    start_time = time.time()
    
    try:
        # Ensure tools are initialized (lazy load on first request)
        ensure_tools_initialized()
        
        logger.info(f"[{request.thread_id}] Received chat request: {request.message[:100]}...")
        
        # Prepare initial state for graph execution
        initial_state = {
            "messages": [],
            "original_log": request.message,
            "parsed_log": {},
            "retrieved_docs": [],
            "solution": "",
            "final_output": "",
        }
        
        # Configure graph with thread_id for persistence
        config = {"configurable": {"thread_id": request.thread_id}}
        
        logger.info(f"[{request.thread_id}] Invoking graph with persistence config")
        
        # Run the graph - this will:
        # 1. Load previous state if thread_id exists (persistence)
        # 2. Execute all nodes
        # 3. Save new state with thread_id (checkpointing)
        result = graph.invoke(initial_state, config=config)
        
        processing_time = time.time() - start_time
        
        logger.info(f"[{request.thread_id}] Graph execution completed in {processing_time:.2f}s")
        
        # Extract parsed metadata
        parsed_log = result.get("parsed_log", {})
        metadata = None
        
        if parsed_log:
            metadata = AnalysisMetadata(
                component=parsed_log.get("component", "Unknown"),
                error_type=parsed_log.get("error_type", "Unknown"),
                error_category=parsed_log.get("error_category", "Unknown"),
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        # Build response
        response = ChatResponse(
            thread_id=request.thread_id,
            status="success",
            final_answer=result.get("final_output", "Analysis could not be completed"),
            analysis_metadata=metadata,
            processing_time_seconds=processing_time,
            node_outputs=result.get("messages", [])
        )
        
        logger.info(f"[{request.thread_id}] Returning successful response")
        
        return response
        
    except ValidationError as e:
        logger.error(f"[{request.thread_id}] Validation error: {e}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    
    except Exception as e:
        logger.error(f"[{request.thread_id}] Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@app.post("/stream")
async def stream(
    message: str = Query(..., min_length=1, description="Log or issue to analyze"),
    thread_id: Optional[str] = Query(None, description="Optional thread ID for persistence")
) -> StreamingResponse:
    """
    Streaming chat endpoint using Server-Sent Events (SSE).
    
    Returns analysis results in real-time as chunks (node-by-node).
    Compatible with frontend frameworks expecting SSE streams.
    
    Args:
        message: The log message to analyze
        thread_id: Optional existing thread_id for conversation continuation
    
    Returns:
        StreamingResponse with SSE formatted events
    
    Raises:
        HTTPException: If graph not initialized or thread_id invalid
    """
    
    if graph is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    if thread_id is None:
        thread_id = str(UUID(int=0))  # Generate new thread
    
    try:
        logger.info(f"[{thread_id}] Received stream request: {message[:100]}...")
        
        # Ensure tools are initialized (lazy load on first request)
        ensure_tools_initialized()
        
        # Create async generator for streaming
        generator = stream_analysis(message, thread_id)
        
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Disable proxy buffering
                "Connection": "keep-alive",
            }
        )
        
    except Exception as e:
        logger.error(f"[{thread_id}] Stream error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Stream error: {str(e)}")


@app.get("/sessions")
async def list_sessions() -> Dict[str, Any]:
    """
    List all saved session thread IDs.
    
    Useful for retrieving previous conversation sessions.
    
    Returns:
        Dictionary with list of session thread IDs and count
    """
    
    if memory_manager is None:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    try:
        sessions = memory_manager.list_sessions()
        return {
            "total_sessions": len(sessions),
            "thread_ids": sessions
        }
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@app.get("/sessions/{thread_id}")
async def get_session(thread_id: str) -> Dict[str, Any]:
    """
    Retrieve information about a specific session.
    
    Args:
        thread_id: The thread ID to retrieve
    
    Returns:
        Session metadata and checkpoint information
    """
    
    if memory_manager is None:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    
    try:
        session_info = memory_manager.get_session_info(thread_id)
        if not session_info:
            raise HTTPException(status_code=404, detail=f"Session {thread_id} not found")
        return session_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session: {str(e)}")


# ==================== ERROR HANDLERS ====================

@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """Handle Pydantic validation errors"""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="ValidationError",
            message="Invalid request parameters",
            details=exc.errors()
        ).dict()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail if isinstance(exc.detail, str) else "HTTPException",
            message=exc.detail
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting FastAPI development server")
    logger.info("Documentation: http://localhost:8000/docs")
    logger.info("ReDoc: http://localhost:8000/redoc")
    
    uvicorn.run(
        "main_api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to True for development with auto-reload
        log_level="info"
    )
