# Setup Guide

Complete step-by-step guide to set up and run the DevOps Multi-Agent Log Analyzer.

## Prerequisites

Before starting, ensure you have:
- Windows, Mac, or Linux
- Python 3.10 or higher
- 8 GB RAM (4 GB minimum)
- 3 GB free disk space
- Ollama installed

Check Python version:
```bash
python --version
# Should show: Python 3.10.x or higher
```

## Step 1: Install Ollama

### Windows
1. Download from https://ollama.ai/download
2. Run the installer
3. Accept defaults
4. Restart your computer

### Mac
```bash
# Using Homebrew
brew install ollama

# Or download from https://ollama.ai/download
```

### Linux
```bash
curl https://ollama.ai/install.sh | sh
```

Verify installation:
```bash
ollama --version
```

## Step 2: Download LLM Model

Before starting the application, download a model:

```bash
# Option 1: Mistral (recommended, ~7GB)
ollama pull mistral

# Option 2: Llama2 (~13GB, slower)
ollama pull llama2

# Option 3: Neural-chat (smaller, ~5GB)
ollama pull neural-chat
```

This downloads ~5-13GB depending on model. Can take 5-30 minutes.

Verify model is installed:
```bash
ollama list
# Should show the model you downloaded
```

## Step 3: Clone/Prepare Project

### Option A: From GitHub (if available)
```bash
git clone <repository-url>
cd ai-devops-log-analyzer
```

### Option B: Manual Setup
```bash
# Create project directory
mkdir ai-devops-log-analyzer
cd ai-devops-log-analyzer

# Copy all project files to this directory
# (Project files should be provided)
```

## Step 4: Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

# Verify (should show (venv) in terminal)
```

## Step 5: Install Python Dependencies

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

This will install:
- langchain
- langgraph
- chromadb
- sentence-transformers
- pypdf
- And more (see requirements.txt)

Takes 5-15 minutes depending on internet speed.

## Step 6: Start Ollama Service

**Important**: Keep this terminal window open while using the application.

```bash
# Start Ollama service
ollama serve

# Output should show:
# 2024/03/06 13:45:00 listening on 127.0.0.1:11434
```

**Do not close this terminal!** The application needs this service running.

## Step 7: Run Data Ingestion (One-time Setup)

In a **new terminal** (keep Ollama running in the other):

```bash
# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Run ingestion
python ingestion/ingest_data.py

# Output should show:
# Loading documents from data/docs
# Loading docker_troubleshooting.txt
# Loading linux_server_guide.txt
# Loading python_debugging.txt
# Splitting documents into chunks
# Ingesting chunks into ChromaDB...
# Successfully ingested X chunks into ChromaDB
```

This creates the vector database for documentation retrieval.

## Step 8: Run the Application

In the same terminal (with activated venv):

### Interactive Mode (Recommended)
```bash
python main.py

# Output:
# Setting up environment...
# ✓ Ollama is running
# Initializing DevOps Log Analyzer...
# ✓ Tools initialized
# ✓ Agents initialized
# ✓ Multi-agent graph created
#
# ==================================================
# DevOps Log Analyzer - Interactive Mode
# ==================================================
#
# Enter DevOps log messages for analysis.
# Type 'quit' or 'exit' to exit.
#
# >>> Enter log message:
```

Type a log message and press Enter. Example:
```
docker: Error response from daemon: driver failed programming external connectivity
```

### Demo Mode
```bash
python main.py --demo

# Runs analysis on 3 sample logs automatically
```

### CLI Mode
```bash
python main.py --analyze "docker: Error response from daemon"

# Analyzes a single log and exits
```

## Verification Checklist

After setup, verify everything works:

```bash
# 1. Check Ollama is running (in first terminal)
ollama list  # Should show your downloaded model

# 2. Check Python environment (in second terminal with venv active)
python --version  # Should show Python 3.10+
pip list | grep langchain  # Should show langchain installed

# 3. Check vector database exists
# Windows:
python -c "import os; print('Vector DB exists:' if os.path.exists('vector_db') else 'Not found')"

# 4. Test a simple analysis
python main.py --analyze "ERROR python: ModuleNotFoundError yaml"
```

If all checks pass, you're ready to use the system!

## Troubleshooting Setup

### Issue: Ollama Connection Refused

**Error:**
```
Could not connect to Ollama: Connection refused
```

**Solution:**
1. Make sure Ollama is running: `ollama serve` in first terminal
2. Check Ollama is listening: `curl http://localhost:11434/api/tags`
3. Restart Ollama service

### Issue: Module Not Found

**Error:**
```
ModuleNotFoundError: No module named 'langchain'
```

**Solution:**
1. Ensure virtual environment is activated: Look for `(venv)` in terminal
2. Reinstall dependencies: `pip install -r requirements.txt`

### Issue: Vector DB Not Found

**Error:**
```
Warning: Vector database not found
```

**Solution:**
1. Run data ingestion: `python ingestion/ingest_data.py`
2. Ensure documentation files exist in `data/docs/`
3. Wait for completion (may take 2-5 minutes)

### Issue: Out of Memory

**Error:**
```
MemoryError or model loading failed
```

**Solution:**
1. Close other applications
2. Use smaller model: `ollama pull neural-chat` (instead of mistral)
3. Update `agents/agents_config.py` with new model name
4. Free up disk space (embeddings can be 1-2 GB)

### Issue: Slow Performance

**Symptoms:**
- Takes >30 seconds to get response
- CPU at 100%

**Solutions:**
1. Ensure you're not running other heavy processes
2. Check Ollama service is responsive: `ollama list`
3. Try a smaller model for faster response
4. Close and restart Ollama service

## First-Time Usage

After setup completes successfully:

1. **Read the Examples** - Check README.md for usage examples
2. **Try Demo Mode** - `python main.py --demo`
3. **Try Interactive Mode** - `python main.py` and type a log
4. **Review Output** - Understand the solution format
5. **Test Your Logs** - Use logs from your environment

## Quick Reference

### Running the System

```bash
# Terminal 1: Start Ollama (keep running)
ollama serve

# Terminal 2: Activate environment and run app
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
python main.py  # or --demo, or --analyze "log"
```

### Common Commands

```bash
# Update dependencies
pip install -r requirements.txt --upgrade

# Run tests
pytest tests/persistence_test.py -v

# Reingest documentation
python ingestion/ingest_data.py

# Check documentation was ingested
python -c "from tools.tools import VectorSearchTool; VectorSearchTool('vector_db').search('docker error')"
```

## Next Steps

After setup and verification:

1. **Read Documentation**
   - Check `docs/PRD.md` for product requirements
   - Check `docs/ARCHITECTURE.md` for system design
   - Check `docs/agent_personas.md` for agent roles

2. **Customize for Your Environment**
   - Add your documentation to `data/docs/`
   - Add sample logs to `data/logs/`
   - Run ingestion: `python ingestion/ingest_data.py`

3. **Test on Real Logs**
   - Use logs from your production environment
   - Verify solutions are relevant and safe
   - Provide feedback for improvement

4. **Integrate with Your Workflow**
   - Add to your DevOps procedures
   - Train team on usage
   - Collect improvement suggestions

## Support

If you encounter issues:

1. **Check Troubleshooting Section** - Above
2. **Review Documentation** - `docs/` directory
3. **Check Test Examples** - `tests/` directory
4. **Review Logs** - Check terminal output for error messages

## System Information

After setup, verify your system meets requirements:

```bash
# Check available resources
python -c "
import os
import psutil

print('=== System Information ===')
print(f'CPU Cores: {os.cpu_count()}')
print(f'Total RAM: {psutil.virtual_memory().total / (1024**3):.1f} GB')
print(f'Available RAM: {psutil.virtual_memory().available / (1024**3):.1f} GB')
print(f'Disk Free: {psutil.disk_usage(\"/\").free / (1024**3):.1f} GB')
print()
print('✓ Minimum 8GB RAM')
print('✓ Minimum 3GB Disk')
print('✓ 4+ CPU Cores')
"
```

---

**You're all set!** Start with `python main.py` or `python main.py --demo`
