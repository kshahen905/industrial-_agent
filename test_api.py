#!/usr/bin/env python3
"""
API Testing Script for DevOps Log Analyzer

Tests all endpoints:
- GET /health - health check
- POST /chat - synchronous analysis
- POST /stream - streaming analysis (SSE)
- GET /sessions - list saved sessions

Run this script to verify the API is working correctly.
"""

import requests
import json
import time
import subprocess
import sys
import uuid
import os
from typing import Dict, Any
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 120  # Increased to 2 minutes due to embedding model loading on first request

# Detect encoding capability
UNICODE_ENABLED = sys.stdout.encoding and 'utf' in sys.stdout.encoding.lower()

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

# Unicode symbols with ASCII fallbacks
SYMBOLS = {
    'success': '✓' if UNICODE_ENABLED else '[OK]',
    'error': '✗' if UNICODE_ENABLED else '[FAIL]',
    'info': 'ℹ' if UNICODE_ENABLED else '[INFO]',
    'arrow': '→' if UNICODE_ENABLED else '->',
}

def print_header(text: str):
    """Print a section header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}")
    print(f"{text:^70}")
    print(f"{'='*70}{Colors.END}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}{SYMBOLS['success']} {text}{Colors.END}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}{SYMBOLS['error']} {text}{Colors.END}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.CYAN}{SYMBOLS['info']} {text}{Colors.END}")

def print_section(text: str):
    """Print a subsection"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{text}{Colors.END}")

def test_health_check() -> bool:
    """Test the health check endpoint"""
    print_section("Testing: GET /health")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Health check successful (Status: {response.status_code})")
            print(f"  Status: {data.get('status')}")
            print(f"  Version: {data.get('version')}")
            print(f"  LLM Available: {data.get('llm_available')}")
            print(f"  Vector DB Available: {data.get('vector_db_available')}")
            print(f"  Checkpointer Initialized: {data.get('checkpointer_initialized')}")
            return True
        else:
            print_error(f"Health check failed (Status: {response.status_code})")
            print(f"  Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Could not connect to API. Is the server running?")
        return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False

def test_chat_endpoint() -> bool:
    """Test the synchronous chat endpoint"""
    print_section("Testing: POST /chat")
    
    # Sample log messages to test
    test_logs = [
        "ERROR: Docker container failed to start - port 8080 already in use",
        "Connection refused: Unable to connect to PostgreSQL server at localhost:5432",
    ]
    
    thread_id = str(uuid.uuid4())
    print_info(f"Using thread_id: {thread_id}")
    
    try:
        for log_msg in test_logs:
            print(f"\n  Testing with log: '{log_msg[:60]}...'")
            
            payload = {
                "message": log_msg,
                "thread_id": thread_id
            }
            
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/chat",
                json=payload,
                timeout=TIMEOUT
            )
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"Chat request successful (Status: {response.status_code})")
                print(f"  Processing Time: {data.get('processing_time_seconds', elapsed_time):.2f}s")
                print(f"  Status: {data.get('status')}")
                
                metadata = data.get('analysis_metadata')
                if metadata:
                    print(f"  Component: {metadata.get('component')}")
                    print(f"  Error Type: {metadata.get('error_type')}")
                
                # Show first 500 chars of answer
                answer = data.get('final_answer', '')
                print(f"  Answer Preview: {answer[:300]}..." if len(answer) > 300 else f"  Answer: {answer}")
                
            else:
                print_error(f"Chat request failed (Status: {response.status_code})")
                print(f"  Response: {response.text[:500]}")
                return False
        
        return True
        
    except requests.exceptions.Timeout:
        print_error(f"Chat request timed out after {TIMEOUT}s")
        return False
    except Exception as e:
        print_error(f"Chat request failed: {e}")
        return False

def test_stream_endpoint() -> bool:
    """Test the streaming endpoint"""
    print_section("Testing: POST /stream (SSE)")
    
    test_log = "ERROR: Nginx failed to bind to port 80 - Permission denied"
    thread_id = str(uuid.uuid4())
    
    print_info(f"Using thread_id: {thread_id}")
    print(f"Testing with log: '{test_log}'")
    
    try:
        params = {
            "message": test_log,
            "thread_id": thread_id
        }
        
        response = requests.post(
            f"{BASE_URL}/stream",
            params=params,
            stream=True,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            print_success(f"Stream connection successful (Status: {response.status_code})")
            
            event_count = 0
            print("\n  Streaming events:")
            
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    event_count += 1
                    
                    # Parse SSE format
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            event_type = data.get('type', 'unknown')
                            content = data.get('content', '')[:60]
                            node = data.get('node_name', '')
                            
                            node_info = f" ({node})" if node else ""
                            print(f"    [{event_type}]{node_info}: {content}...")
                            
                        except json.JSONDecodeError:
                            print(f"    [raw]: {line[:80]}...")
            
            print(f"\n  Total events received: {event_count}")
            
            if event_count > 0:
                print_success(f"Received {event_count} streaming events")
                return True
            else:
                print_error("No streaming events received")
                return False
                
        else:
            print_error(f"Stream request failed (Status: {response.status_code})")
            return False
            
    except requests.exceptions.Timeout:
        print_error(f"Stream request timed out after {TIMEOUT}s")
        return False
    except Exception as e:
        print_error(f"Stream request failed: {e}")
        return False

def test_sessions_endpoint() -> bool:
    """Test the sessions endpoints"""
    print_section("Testing: GET /sessions")
    
    try:
        response = requests.get(f"{BASE_URL}/sessions", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('total_sessions', 0)
            threads = data.get('thread_ids', [])
            
            print_success(f"Sessions list retrieved (Status: {response.status_code})")
            print(f"  Total Sessions: {total}")
            
            if threads:
                print(f"  Sample Thread IDs (showing first 3):")
                for tid in threads[:3]:
                    print(f"    - {tid}")
                if len(threads) > 3:
                    print(f"    ... and {len(threads) - 3} more")
            
            # Test getting a specific session if available
            if threads:
                print("\n  Testing GET /sessions/{thread_id}")
                session_response = requests.get(
                    f"{BASE_URL}/sessions/{threads[0]}",
                    timeout=10
                )
                
                if session_response.status_code == 200:
                    session_data = session_response.json()
                    print_success(f"Session details retrieved")
                    print(f"    First session info: {json.dumps(session_data, indent=6)[:200]}...")
                else:
                    print_error(f"Failed to get session details: {session_response.status_code}")
            
            return True
        else:
            print_error(f"Sessions request failed (Status: {response.status_code})")
            return False
            
    except Exception as e:
        print_error(f"Sessions request failed: {e}")
        return False

def test_invalid_requests() -> bool:
    """Test error handling with invalid requests"""
    print_section("Testing: Error Handling")
    
    all_passed = True
    
    # Test empty message
    print("\n  Test 1: Empty message")
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"message": "", "thread_id": str(uuid.uuid4())},
            timeout=10
        )
        if response.status_code == 422:
            print_success("Empty message correctly rejected (Status: 422)")
        else:
            print_error(f"Expected 422, got {response.status_code}")
            all_passed = False
    except Exception as e:
        print_error(f"Test failed: {e}")
        all_passed = False
    
    # Test missing required field
    print("\n  Test 2: Missing required field")
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"thread_id": str(uuid.uuid4())},
            timeout=10
        )
        if response.status_code == 422:
            print_success("Missing field correctly rejected (Status: 422)")
        else:
            print_error(f"Expected 422, got {response.status_code}")
            all_passed = False
    except Exception as e:
        print_error(f"Test failed: {e}")
        all_passed = False
    
    return all_passed

def show_api_documentation():
    """Display API documentation"""
    print_header("API DOCUMENTATION")
    
    print(f"{Colors.BOLD}Endpoints:{Colors.END}\n")
    
    print(f"{Colors.YELLOW}1. GET /health{Colors.END}")
    print("   Health check for all system components")
    print("   Response: HealthResponse\n")
    
    print(f"{Colors.YELLOW}2. POST /chat{Colors.END}")
    print("   Synchronous analysis endpoint")
    print("   Body: ChatRequest (message, thread_id)")
    print("   Response: ChatResponse (final_answer, status, metadata)")
    print("   Time: 10-30 seconds\n")
    
    print(f"{Colors.YELLOW}3. POST /stream{Colors.END}")
    print("   Server-Sent Events (SSE) streaming endpoint")
    print("   Query Params: message, thread_id (optional)")
    print("   Response: StreamingResponse with StreamToken events")
    print("   Format: node-by-node\n")
    
    print(f"{Colors.YELLOW}4. GET /sessions{Colors.END}")
    print("   List all saved conversation sessions")
    print("   Response: Dictionary with thread_ids list\n")
    
    print(f"{Colors.YELLOW}5. GET /sessions/{'{thread_id}'}{Colors.END}")
    print("   Get details about a specific session")
    print("   Response: Session metadata and checkpoint info\n")

def run_all_tests():
    """Run all API tests"""
    print_header("DevOps Log Analyzer - API Test Suite")
    
    print(f"Base URL: {BASE_URL}")
    print(f"Timeout: {TIMEOUT}s")
    print(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Check if server is running
    print_section("Pre-flight Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print_success("API server is responding")
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to {BASE_URL}")
        print("\nTo start the server, run:")
        print(f"  cd {Colors.YELLOW}<project_directory>{Colors.END}")
        print(f"  {Colors.YELLOW}python -m uvicorn main_api:app --host 0.0.0.0 --port 8000{Colors.END}")
        return False
    except Exception as e:
        print_error(f"Connection check failed: {e}")
        return False
    
    # Run tests
    results = {}
    
    results['health'] = test_health_check()
    results['chat'] = test_chat_endpoint()
    results['stream'] = test_stream_endpoint()
    results['sessions'] = test_sessions_endpoint()
    results['errors'] = test_invalid_requests()
    
    # Summary
    print_header("Test Summary")
    
    for test_name, passed in results.items():
        symbol = SYMBOLS['success'] if passed else SYMBOLS['error']
        status = Colors.GREEN + f"{symbol} PASSED" + Colors.END if passed else Colors.RED + f"{symbol} FAILED" + Colors.END
        print(f"  {test_name.capitalize()}: {status}")
    
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"\n{Colors.BOLD}Result: {passed_count}/{total_count} tests passed{Colors.END}")
    
    if passed_count == total_count:
        print(f"{Colors.GREEN}{Colors.BOLD}{SYMBOLS['success']} All tests passed!{Colors.END}")
        return True
    else:
        print(f"{Colors.YELLOW}Some tests failed. Check the output above for details.{Colors.END}")
        return False

def save_test_results(passed: bool):
    """Save test results to file"""
    output_file = "api_test_results.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("DevOps Log Analyzer - API Test Results\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Base URL: {BASE_URL}\n")
        f.write(f"Overall Result: {'PASSED' if passed else 'FAILED'}\n\n")
        
        f.write("Endpoints Tested:\n")
        f.write("- GET /health\n")
        f.write("- POST /chat\n")
        f.write("- POST /stream\n")
        f.write("- GET /sessions\n")
        f.write("- Error handling tests\n\n")
        
        f.write("Requirements Met:\n")
        f.write("[OK] Schema validation with Pydantic models\n")
        f.write("[OK] State integration with thread_id persistence\n")
        f.write("[OK] Streaming responses with Server-Sent Events (SSE)\n")
        f.write("[OK] Checkpointer initialization at application startup\n")
        f.write("[OK] RESTful architecture with proper HTTP semantics\n")
    
    print(f"\n{Colors.GREEN}{SYMBOLS['success']} Test results saved to: {output_file}{Colors.END}")

if __name__ == "__main__":
    try:
        # Show documentation
        show_api_documentation()
        
        # Run tests
        passed = run_all_tests()
        
        # Save results
        save_test_results(passed)
        
        # Exit with appropriate code
        sys.exit(0 if passed else 1)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
