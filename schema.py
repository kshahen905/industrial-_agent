"""
API Schema Definitions

Pydantic models for request/response validation and documentation.
Implements contract between client and the DevOps Log Analyzer API.

Lab 6 - API Layer Requirements:
- ChatRequest: message, thread_id
- ChatResponse: final_answer, status
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import uuid4, UUID


class ChatRequest(BaseModel):
    """
    Request model for chat endpoint.
    
    Defines the contract for incoming requests to /chat endpoint.
    """
    
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The DevOps log or issue description to analyze"
    )
    
    thread_id: Optional[str] = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this conversation thread. "
                    "Use existing thread_id to continue a conversation or retrieve history."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "ERROR: Docker container failed to start - port 8080 already in use",
                "thread_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class AnalysisMetadata(BaseModel):
    """Metadata about the analysis"""
    
    component: str = Field(description="Identified affected component")
    error_type: str = Field(description="Classified error type")
    error_category: str = Field(description="Error category for solutions")
    timestamp: str = Field(description="When analysis was performed")


class ChatResponse(BaseModel):
    """
    Response model for chat endpoint.
    
    Defines the contract for responses from /chat endpoint.
    """
    
    thread_id: str = Field(description="The thread ID for follow-up requests")
    
    status: str = Field(
        description="Response status: 'success', 'processing', or 'error'"
    )
    
    final_answer: str = Field(
        description="Final recommendation and solution from the multi-agent system"
    )
    
    analysis_metadata: Optional[AnalysisMetadata] = Field(
        default=None,
        description="Parsed information about the identified issue"
    )
    
    processing_time_seconds: float = Field(
        description="Total processing time in seconds"
    )
    
    node_outputs: List[str] = Field(
        default_factory=list,
        description="Messages from each agent in the workflow"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "success",
                "final_answer": "Root Cause: Port binding conflict\n\n" +
                               "Solution Steps:\n1. Identify process using port 8080\n" +
                               "2. Kill or restart the process\n3. Verify port is free\n\n" +
                               "Commands: lsof -i :8080",
                "processing_time_seconds": 12.5,
                "node_outputs": [
                    "Log Analyzer: Identified Docker component with port binding error",
                    "Retriever: Retrieved 3 relevant Docker documentation files"
                ]
            }
        }


class StreamToken(BaseModel):
    """
    Represents a single token or update in streaming response.
    
    SSE format wrapper for streaming data.
    """
    
    type: str = Field(
        description="Type of stream event: 'start', 'token', 'node', 'metadata', 'end', 'error'"
    )
    
    content: str = Field(
        description="The actual content or token"
    )
    
    node_name: Optional[str] = Field(
        default=None,
        description="Name of the agent node currently executing (for node-by-node mode)"
    )
    
    timestamp: Optional[str] = Field(
        default=None,
        description="ISO format timestamp of when this event occurred"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "token",
                "content": "Root Cause: Port 8080",
                "node_name": "solution_generation",
                "timestamp": "2024-04-27T10:30:00Z"
            }
        }


class HealthResponse(BaseModel):
    """Response for health check endpoint"""
    
    status: str = Field(description="Health status: 'healthy' or 'degraded'")
    version: str = Field(description="API version")
    llm_available: bool = Field(description="Whether LLM is connected")
    vector_db_available: bool = Field(description="Whether vector database is accessible")
    checkpointer_initialized: bool = Field(description="Whether persistence layer is ready")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "llm_available": True,
                "vector_db_available": True,
                "checkpointer_initialized": True
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response format"""
    
    error: str = Field(description="Error type or code")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "InvalidInput",
                "message": "Message must not be empty",
                "details": {"field": "message", "reason": "min_length"}
            }
        }
