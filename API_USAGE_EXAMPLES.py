"""
API Usage Examples

This file demonstrates how to use the DevOps Log Analyzer API
from different programming contexts.
"""

# ============================================================================
# Example 1: Simple curl request (bash)
# ============================================================================

"""
Health Check:
    curl http://localhost:8000/health

Synchronous Request:
    curl -X POST http://localhost:8000/chat \
      -H "Content-Type: application/json" \
      -d '{
        "message": "ERROR: Docker container failed - port 8080 already in use",
        "thread_id": "550e8400-e29b-41d4-a716-446655440000"
      }'

Streaming Request:
    curl -N 'http://localhost:8000/stream?message=ERROR:%20connection%20refused'
"""

# ============================================================================
# Example 2: Python synchronous client
# ============================================================================

import requests
import json
from uuid import uuid4

def analyze_log_sync(log_message: str) -> dict:
    """
    Analyze a log using synchronous request.
    Waits for complete response before returning.
    """
    
    base_url = "http://localhost:8000"
    
    # Generate unique thread ID for conversation tracking
    thread_id = str(uuid4())
    
    # Prepare request
    payload = {
        "message": log_message,
        "thread_id": thread_id
    }
    
    # Send request
    response = requests.post(
        f"{base_url}/chat",
        json=payload,
        timeout=60  # May take 10-30 seconds
    )
    
    # Check response
    if response.status_code == 200:
        result = response.json()
        
        print(f"Status: {result['status']}")
        print(f"Processing time: {result['processing_time_seconds']:.2f}s")
        print(f"Thread ID: {result['thread_id']}")
        print("\nFinal Answer:")
        print(result['final_answer'])
        
        if result['analysis_metadata']:
            print(f"\nComponent: {result['analysis_metadata']['component']}")
            print(f"Error Type: {result['analysis_metadata']['error_type']}")
        
        return result
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

# Usage
if __name__ == "__main__":
    log = "ERROR: PostgreSQL connection failed - too many connections"
    analyze_log_sync(log)

# ============================================================================
# Example 3: Python streaming client
# ============================================================================

import requests
import json
import sys
from typing import Generator

def analyze_log_stream(log_message: str) -> Generator:
    """
    Analyze a log using streaming (SSE).
    Yields results as they arrive.
    """
    
    base_url = "http://localhost:8000"
    current_thread = None
    
    params = {
        "message": log_message,
        # Optional: add thread_id to resume conversation
        # "thread_id": "550e8400-e29b-41d4-a716-446655440000"
    }
    
    # Stream request
    response = requests.get(
        f"{base_url}/stream",
        params=params,
        stream=True
    )
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return
    
    # Parse SSE events
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        
        try:
            # Parse JSON from SSE format
            data = json.loads(line[6:])
            
            event_type = data.get('type')
            content = data.get('content')
            node_name = data.get('node_name', '')
            
            # Handle different event types
            if event_type == 'start':
                print("🔄 Starting analysis...\n")
            
            elif event_type == 'node':
                print(f"📊 [{node_name}]:")
                print(f"   {content[:200]}...\n")
                yield {'type': 'node', 'content': content, 'node': node_name}
            
            elif event_type == 'metadata':
                metadata = json.loads(content)
                print(f"📋 Analysis Metadata:")
                print(f"   Component: {metadata['component']}")
                print(f"   Error Type: {metadata['error_type']}\n")
            
            elif event_type == 'token':
                print(f"✅ Final Answer:")
                print(f"{content}\n")
                yield {'type': 'answer', 'content': content}
            
            elif event_type == 'end':
                print("✓ Analysis complete")
                yield {'type': 'complete'}
            
            elif event_type == 'error':
                print(f"❌ Error: {content}")
                yield {'type': 'error', 'content': content}
        
        except json.JSONDecodeError:
            continue

# Usage
if __name__ == "__main__":
    log = "ERROR: Nginx failed - Connection reset by peer"
    for event in analyze_log_stream(log):
        print(f"[{event['type']}] Received")

# ============================================================================
# Example 4: JavaScript frontend integration
# ============================================================================

"""
<!-- HTML -->
<div id="analyze-form">
  <textarea id="log-input" placeholder="Paste your log here..."></textarea>
  <button id="analyze-btn">Analyze</button>
  <button id="stream-btn">Stream Analysis</button>
</div>

<div id="results">
  <div id="stream-output"></div>
</div>

<script>
// Synchronous request
async function analyzeLog() {
  const message = document.getElementById('log-input').value;
  const threadId = generateOrGetThreadId();
  
  const response = await fetch('/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message, thread_id: threadId})
  });
  
  const result = await response.json();
  displayResults(result);
}

// Streaming request
async function analyzeLogStream() {
  const message = document.getElementById('log-input').value;
  
  const response = await fetch('/stream?message=' + encodeURIComponent(message));
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    processStreamChunk(chunk);
  }
}

function processStreamChunk(chunk) {
  const lines = chunk.split('\\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      try {
        const event = JSON.parse(line.substring(6));
        
        if (event.type === 'node') {
          appendOutput(`[${event.node_name}] ${event.content}`);
        } else if (event.type === 'token') {
          appendOutput(event.content);
        }
      } catch (e) {
        console.error('Parse error:', e);
      }
    }
  }
}

function appendOutput(text) {
  const output = document.getElementById('stream-output');
  output.innerHTML += `<p>${escapeHtml(text)}</p>`;
  output.scrollTop = output.scrollHeight;
}

// Attach event listeners
document.getElementById('analyze-btn').onclick = analyzeLog;
document.getElementById('stream-btn').onclick = analyzeLogStream;
</script>
"""

# ============================================================================
# Example 5: Conversation continuation with thread_id
# ============================================================================

def conversation_example():
    """
    Example of maintaining a conversation using thread_id.
    """
    
    import requests
    from uuid import uuid4
    
    base_url = "http://localhost:8000"
    thread_id = str(uuid4())  # Create new conversation
    
    print("=== Multi-Turn Conversation Example ===\n")
    
    # Turn 1: Initial issue
    log_1 = "ERROR: Docker container exit code 1 - /bin/sh not found"
    print(f"Turn 1: {log_1}")
    
    response_1 = requests.post(
        f"{base_url}/chat",
        json={"message": log_1, "thread_id": thread_id},
        timeout=60
    ).json()
    
    print(f"Response: {response_1['final_answer'][:200]}...\n")
    
    # Turn 2: Follow-up question with same thread_id
    log_2 = "Follow-up: Can you explain the root cause in more detail?"
    print(f"Turn 2: {log_2}")
    
    response_2 = requests.post(
        f"{base_url}/chat",
        json={"message": log_2, "thread_id": thread_id},
        timeout=60
    ).json()
    
    print(f"Response: {response_2['final_answer'][:200]}...\n")
    
    # The API maintains state across requests via thread_id and checkpoints

# ============================================================================
# Example 6: Batch processing multiple logs
# ============================================================================

import concurrent.futures

def batch_analyze(logs: list) -> dict:
    """
    Analyze multiple logs in parallel using thread pool.
    """
    
    base_url = "http://localhost:8000"
    results = {}
    
    def process_log(log_index, log_message):
        try:
            response = requests.post(
                f"{base_url}/chat",
                json={
                    "message": log_message,
                    "thread_id": f"batch-{log_index}"
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return log_index, response.json()
            else:
                return log_index, {"status": "error", "message": response.text}
        except Exception as e:
            return log_index, {"status": "error", "message": str(e)}
    
    # Process in parallel (max 5 concurrent requests)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(process_log, idx, log)
            for idx, log in enumerate(logs)
        ]
        
        for future in concurrent.futures.as_completed(futures):
            idx, result = future.result()
            results[idx] = result
    
    return results

# Usage
if __name__ == "__main__":
    logs = [
        "ERROR: Database connection timeout",
        "ERROR: Kubernetes pod evicted due to memory pressure",
        "ERROR: SSL certificate expired"
    ]
    
    results = batch_analyze(logs)
    for idx, result in results.items():
        print(f"Log {idx}: {result['status']}")

# ============================================================================
# Example 7: Session management
# ============================================================================

def session_management_example():
    """
    Example of retrieving and managing conversation sessions.
    """
    
    import requests
    
    base_url = "http://localhost:8000"
    
    # List all sessions
    print("=== Session Management Example ===\n")
    
    sessions_response = requests.get(f"{base_url}/sessions").json()
    print(f"Total saved sessions: {sessions_response['total_sessions']}")
    
    if sessions_response['thread_ids']:
        thread_id = sessions_response['thread_ids'][0]
        print(f"Using thread: {thread_id}\n")
        
        # Get session details
        details = requests.get(f"{base_url}/sessions/{thread_id}").json()
        print(f"Session created: {details.get('created_at')}")
        print(f"Last updated: {details.get('last_updated')}")
        print(f"Checkpoints: {details.get('checkpoint_count')}")
        
        # Resume session with new question
        response = requests.post(
            f"{base_url}/chat",
            json={
                "message": "Analyze this related error...",
                "thread_id": thread_id
            }
        ).json()
        
        print(f"\nResumed session analysis...")
        print(f"Processing time: {response['processing_time_seconds']:.2f}s")

# ============================================================================
# Example 8: Error handling
# ============================================================================

def error_handling_example():
    """
    Example of proper error handling.
    """
    
    import requests
    
    base_url = "http://localhost:8000"
    
    try:
        # Empty message - validation error
        response = requests.post(
            f"{base_url}/chat",
            json={"message": "", "thread_id": "test"}
        )
        
        if response.status_code == 422:
            errors = response.json()
            print("Validation Error:")
            print(f"  {errors['message']}")
            if 'details' in errors:
                for detail in errors['details']:
                    print(f"  - {detail}")
        
        # Server error handling
        response = requests.post(
            f"{base_url}/chat",
            json={"message": "Test message"},
            timeout=5
        )
        
        if response.status_code >= 500:
            error = response.json()
            print(f"Server Error: {error['message']}")
        
        # Connection error
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to API server")
        print("Make sure the server is running: python -m uvicorn main_api:app")
    except requests.exceptions.Timeout:
        print("Error: Request timed out")
    except Exception as e:
        print(f"Unexpected error: {e}")

# ============================================================================
# Example 9: Performance testing
# ============================================================================

import time

def performance_test():
    """
    Test API performance and latency.
    """
    
    import requests
    
    base_url = "http://localhost:8000"
    test_log = "ERROR: Service failed to start - port already in use"
    
    print("=== Performance Test ===\n")
    
    # Measure latency
    start = time.time()
    
    response = requests.post(
        f"{base_url}/chat",
        json={"message": test_log},
        timeout=60
    )
    
    elapsed = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        print(f"Request latency: {elapsed:.2f}s")
        print(f"API processing time: {data['processing_time_seconds']:.2f}s")
        print(f"Network overhead: {(elapsed - data['processing_time_seconds']):.2f}s")
        
        # Check components
        print(f"\nNode outputs: {len(data['node_outputs'])} agents executed")
        for i, output in enumerate(data['node_outputs'], 1):
            print(f"  {i}. {output[:60]}...")

# ============================================================================
if __name__ == "__main__":
    print("""
API Usage Examples - Choose one:

1. Synchronous request:     python examples.py SyncExample()
2. Streaming request:        python examples.py StreamExample()
3. Batch processing:         python examples.py batch_analyze([...])
4. Session management:       python examples.py session_management_example()
5. Error handling:           python examples.py error_handling_example()
6. Performance testing:      python examples.py performance_test()

See code comments for JavaScript and curl examples.
""")
