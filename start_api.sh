#!/bin/bash
# Quick Start Script for DevOps Log Analyzer API

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}DevOps Log Analyzer - API Quick Start${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"

# 1. Check Python
echo -e "${YELLOW}[1/5] Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi
python_version=$(python3 --version)
echo -e "${GREEN}✓ ${python_version}${NC}\n"

# 2. Check Ollama
echo -e "${YELLOW}[2/5] Checking Ollama service...${NC}"
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo -e "${RED}✗ Ollama not running${NC}"
    echo -e "${YELLOW}  Start Ollama with: ollama serve${NC}\n"
else
    echo -e "${GREEN}✓ Ollama is running${NC}\n"
fi

# 3. Check dependencies
echo -e "${YELLOW}[3/5] Checking Python dependencies...${NC}"
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}✗ requirements.txt not found${NC}"
    exit 1
fi

missing_packages=()
for package in fastapi uvicorn pydantic langgraph; do
    python3 -c "import ${package}" 2>/dev/null || missing_packages+=("${package}")
done

if [ ${#missing_packages[@]} -gt 0 ]; then
    echo -e "${YELLOW}Installing missing packages: ${missing_packages[@]}${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}\n"
else
    echo -e "${GREEN}✓ All dependencies installed${NC}\n"
fi

# 4. Create necessary directories
echo -e "${YELLOW}[4/5] Setting up directories...${NC}"
mkdir -p data/logs vector_db
echo -e "${GREEN}✓ Directories ready${NC}\n"

# 5. Start FastAPI server
echo -e "${YELLOW}[5/5] Starting FastAPI server...${NC}"
echo -e "${GREEN}✓ Server starting on http://localhost:8000${NC}"
echo -e "\nEndpoints:"
echo -e "  ${BLUE}API Docs${NC}: http://localhost:8000/docs"
echo -e "  ${BLUE}ReDoc${NC}: http://localhost:8000/redoc"
echo -e "\nTest the API:"
echo -e "  ${BLUE}Health Check${NC}: http://localhost:8000/health"
echo -e "  ${BLUE}Test Suite${NC}: python test_api.py\n"
echo -e "${BLUE}Press Ctrl+C to stop${NC}\n"

# Start the server
python3 -m uvicorn main_api:app --host 0.0.0.0 --port 8000 --reload
