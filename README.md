# DevOps Multi-Agent Log Analyzer

A local, offline AI system for analyzing DevOps logs and generating actionable solutions using multi-agent orchestration with LangGraph and ChromaDB.

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- 8 GB RAM (4 GB minimum)
- 3 GB disk space
- Ollama installed ([download](https://ollama.ai))

### 2. Setup

```bash
# Clone/navigate to project
cd ai-devops-log-analyzer

# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download Ollama model
ollama pull mistral
# OR: ollama pull llama2

# Start Ollama service
ollama serve
```

### 3. Run

```bash
# Interactive mode (recommended)
python main.py

# Demo mode (sample logs)
python main.py --demo

# CLI mode (single analysis)
python main.py --analyze "docker: Error response from daemon..."
```

## 📋 Features

### Multi-Agent System
- **Log Analysis Agent** - Identifies component, error type, root cause
- **Retriever Agent** - Searches documentation using semantic similarity
- **Solution Generator Agent** - Creates step-by-step solutions with commands
- **Validation Agent** - Reviews solutions for accuracy and safety

### Supported Components
- ✅ Docker - Port binding, connection, memory, image pull errors
- ✅ Python - Import errors, database connection, JSON parsing, memory
- ✅ Nginx/Apache - Connection refused, configuration, process errors
- ✅ Linux/Systemd - OOM, service failures, SSH, DNS

### Output Example

```
╔════════════════════════════════════════════════════════════════╗
║           DevOps Log Analysis - Final Recommendation           ║
╚════════════════════════════════════════════════════════════════╝

Component: Docker
Error Type: Port Binding Error

Root Cause:
Port 80 is already in use by another process...

Solution Steps:
1. Identify process using port 80
   lsof -i :80

2. Stop conflicting service
   sudo systemctl stop <service>

3. Restart Docker
   sudo systemctl restart docker

Commands Reference:
docker ps
docker logs <container_name>
```

## 🏗️ Project Structure

```
ai-devops-log-analyzer/
├── data/
│   ├── logs/              # Sample DevOps logs
│   │   ├── docker_logs.txt
│   │   ├── server_logs.txt
│   │   └── python_errors.txt
│   └── docs/              # Documentation for ingestion
│       ├── docker_troubleshooting.txt
│       ├── linux_server_guide.txt
│       └── python_debugging.txt
│
├── vector_db/             # ChromaDB embeddings
│
├── ingestion/
│   └── ingest_data.py     # Data ingestion pipeline
│
├── tools/
│   └── tools.py           # Vector search, log parser, command generator
│
├── agents/
│   └── agents_config.py   # Agent personas and configurations
│
├── graph/
│   └── multi_agent_graph.py  # LangGraph workflow orchestration
│
├── memory/
│   └── checkpoint_db.sqlite  # Session state persistence
│
├── tests/
│   ├── persistence_test.py   # Unit tests
│   └── retrieval_test.md     # Manual retrieval tests
│
├── docs/
│   ├── PRD.md                  # Product requirements
│   ├── agent_personas.md       # Agent descriptions
│   └── ARCHITECTURE.md         # System architecture
│
├── main.py                # Entry point
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🔧 Configuration

### Ollama Model Selection

Edit `agents/agents_config.py`:
```python
factory = AgentFactory(
    model_name="mistral",      # or "llama2"
    base_url="http://localhost:11434"
)
```

### Data Ingestion

Run manually:
```bash
python ingestion/ingest_data.py
```

Or automatically on first run via `main.py`.

### Custom Documentation

1. Add PDF or text files to `data/docs/`
2. Run ingestion: `python ingestion/ingest_data.py`
3. System will automatically embed and store

## 📊 Data Flow

```
User Log
    ↓
Log Analysis Agent
    ↓ (parsed_log)
Documentation Retriever
    ↓ (retrieved_docs)
Solution Generator
    ↓ (solution)
Validation Agent
    ↓ (final_output)
User Solution
```

## 🧪 Testing

### Manual Tests
```bash
# See retrieval tests
cat tests/retrieval_test.md

# Run tests
pytest tests/persistence_test.py -v
```

### Test a Specific Log
```bash
python main.py --analyze "ERROR [docker]: driver failed programming external connectivity"
```

## 📚 Usage Examples

### Example 1: Docker Port Binding Error

**Input:**
```
docker: Error response from daemon: driver failed programming external connectivity on endpoint nginx_container: Error starting userland proxy: listen tcp 0.0.0.0:80: bind: address already in use
```

**Output:**
```
Problem Detected: Docker Port Binding Error
Root Cause: Another process is already using port 80
Suggested Fix:
  Run: lsof -i :80
  Then: sudo systemctl restart docker
Documentation Reference: Docker troubleshooting guide
```

### Example 2: Python Module Not Found

**Input:**
```
Traceback: ModuleNotFoundError: No module named 'yaml'
```

**Output:**
```
Problem Detected: Python Dependency Error
Root Cause: Required package 'yaml' is not installed
Suggested Fix:
  Run: pip install yaml
  Verify: python -c "import yaml"
Documentation Reference: Python debugging guide
```

### Example 3: Connection Refused

**Input:**
```
ERROR [nginx]: connect() failed (111: Connection refused)
```

**Output:**
```
Problem Detected: Service Connection Error
Root Cause: Upstream service is not running or unreachable
Suggested Fix:
  Check: systemctl status <service>
  Restart: systemctl restart <service>
  Test: curl http://localhost
Documentation Reference: Linux server guide
```

## 🔐 Security

- ✅ **Fully Local** - No data sent to external services
- ✅ **Offline** - Works without internet connection
- ✅ **Open Source** - All dependencies are open-source
- ✅ **No Credentials** - No API keys required
- ✅ **Safe Commands** - Validation agent reviews all commands

## 📈 Performance

| Metric | Expected |
|--------|----------|
| Response Time | 5-10 seconds |
| Memory Usage | 2-4 GB (peak) |
| Vector Search | <1 second |
| LLM Inference | 3-5 seconds |
| Model Size | 7-13 GB (on disk) |

## 🚫 Troubleshooting

### Ollama Connection Error
```
Error: Could not connect to Ollama
Solution:
1. Start Ollama: ollama serve
2. Pull model: ollama pull mistral
3. Verify: curl http://localhost:11434/api/tags
```

### Vector DB Not Found
```
Warning: Vector database not found
Solution:
1. Run ingestion: python ingestion/ingest_data.py
2. Or place PDFs in data/docs/ and re-run main.py
```

### Memory Issues
```
Error: Out of memory
Solution:
1. Close other applications
2. Use lighter model: ollama pull tinyllama
3. Reduce batch sizes in code
```

### Slow Responses
```
Slow analysis
Solution:
1. Ensure Ollama is running: ollama serve
2. Check CPU usage: top/Task Manager
3. Increase GPU allocation if available
```

## 🛠️ Development

### Add New Component Support

1. Update `LogParsingTool.PATTERNS` in `tools/tools.py`
2. Add documentation to `data/docs/`
3. Add commands to `CommandGeneratorTool.COMMAND_TEMPLATES`
4. Test with `main.py --analyze`

### Add Custom Documentation

1. Save PDF/text to `data/docs/`
2. Run: `python ingestion/ingest_data.py`
3. Vector DB will be updated automatically

### Extend Agent Capabilities

1. Edit `agents/agents_config.py` for agent config
2. Update `graph/multi_agent_graph.py` node functions
3. Test with `python main.py --demo`

## 📝 Documentation

- [Product Requirements Document](docs/PRD.md)
- [Agent Personas](docs/agent_personas.md)
- [System Architecture](docs/ARCHITECTURE.md)
- [Retrieval Tests](tests/retrieval_test.md)

## 🤝 Architecture

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed system architecture, data flow, and technology stack.

## 📦 Dependencies

- **langchain** - LLM orchestration
- **langgraph** - Multi-agent workflow
- **chromadb** - Vector database
- **sentence-transformers** - Semantic embeddings
- **ollama** - Local LLM inference
- **pypdf** - PDF processing
- **sqlalchemy** - Database ORM
- **pytest** - Testing

See [requirements.txt](requirements.txt) for full list.

## 🎯 Roadmap

- [ ] Web UI for visualization
- [ ] Real-time log streaming
- [ ] Custom ML model training
- [ ] Incident tracking integration
- [ ] Multi-language support
- [ ] Feedback loop for improvement
- [ ] Docker containerization
- [ ] REST API interface

## 📄 License

Open source - feel free to use and modify.

## 🤓 Contributing

### To Add New Features:
1. Fork or create a branch
2. Make changes with tests
3. Submit with clear description

### To Report Issues:
1. Describe the problem clearly
2. Include log messages
3. Provide system information

## ❓ FAQ

**Q: Does it require internet?**
A: No, fully offline. Ollama models download once, then work offline.

**Q: Can I add custom documentation?**
A: Yes! Add PDFs/text to `data/docs/` and run ingestion.

**Q: What models can I use?**
A: Any model Ollama supports (mistral, llama2, neural-chat, etc).

**Q: How accurate are the solutions?**
A: High accuracy for well-documented errors, improves with custom documentation.

**Q: Can I use this in production?**
A: Yes, with caution. Always review generated commands before executing.

## 📞 Support

For issues or questions:
1. Check troubleshooting section above
2. Review documentation in `docs/`
3. Check test examples in `tests/`

---

**Made with ❤️ for DevOps Engineers**
