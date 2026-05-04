# Architecture Diagram

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   DevOps Log Analyzer System                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                            │
├─────────────────────────────────────────────────────────────────┤
│  • Interactive Mode (REPL)                                       │
│  • CLI Mode (--analyze "log message")                            │
│  • Demo Mode (--demo, sample logs)                               │
└────────────────┬────────────────────────────────────────────────┘
                 │ Raw Log Message
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Main Entry Point                              │
│                      (main.py)                                   │
├─────────────────────────────────────────────────────────────────┤
│  • Environment setup                                             │
│  • System initialization                                         │
│  • Graph invocation                                              │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│           LangGraph Multi-Agent Orchestration                   │
│          (graph/multi_agent_graph.py)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Node 1: Log Analysis Agent                               │  │
│  │ • Parse log message                                      │  │
│  │ • Identify component (Docker/Python/Nginx/Linux)        │  │
│  │ • Classify error type                                   │  │
│  │ Role: DevOps expert analysis                            │  │
│  └─────────┬──────────────────────────────────────────────┘  │
│            │ parsed_log: {component, error_type, ...}        │
│            ▼                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Node 2: Documentation Retriever Agent                    │  │
│  │ • Construct semantic search query                        │  │
│  │ • Search ChromaDB vector database                        │  │
│  │ • Retrieve top-3 relevant documentation chunks           │  │
│  │ Role: Knowledge base specialist                          │  │
│  └─────────┬──────────────────────────────────────────────┘  │
│            │ retrieved_docs: [doc1, doc2, doc3]              │
│            ▼                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Node 3: Solution Generator Agent                         │  │
│  │ • Combine analysis + documentation                       │  │
│  │ • Generate root cause explanation                        │  │
│  │ • Create step-by-step solution                           │  │
│  │ • Include specific commands                              │  │
│  │ Role: Solution architect                                 │  │
│  └─────────┬──────────────────────────────────────────────┘  │
│            │ solution: {root_cause, steps, commands}         │
│            ▼                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Node 4: Validation Agent                                 │  │
│  │ • Verify technical accuracy                              │  │
│  │ • Check safety and best practices                        │  │
│  │ • Ensure clarity and completeness                        │  │
│  │ • Format final output                                    │  │
│  │ Role: Quality assurance specialist                      │  │
│  └─────────┬──────────────────────────────────────────────┘  │
│            │                                                 │
└────────────┼─────────────────────────────────────────────────┘
             │ final_output: Formatted solution
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Output Formatters                             │
│  • Terminal display                                              │
│  • JSON export (future)                                          │
│  • Report generation (future)                                    │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                    Supporting Systems                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────────────┐   │
│  │  Tools Module        │  │  LLM Integration             │   │
│  │  (tools/tools.py)    │  │  (Ollama local inference)    │   │
│  ├──────────────────────┤  ├──────────────────────────────┤   │
│  │ • VectorSearchTool   │  │ • Model: mistral/llama2      │   │
│  │ • LogParsingTool     │  │ • Endpoint: localhost:11434  │   │
│  │ • CommandGenerator   │  │ • Temperature: 0.3           │   │
│  └──────────────────────┘  └──────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────────────┐   │
│  │  Vector Database     │  │  Embedding Model             │   │
│  │  (ChromaDB)          │  │  (SentenceTransformers)      │   │
│  ├──────────────────────┤  ├──────────────────────────────┤   │
│  │ • Storage: DuckDB    │  │ • Model: all-MiniLM-L6-v2    │   │
│  │ • Format: Parquet    │  │ • Dimensions: 384            │   │
│  │ • Collections:       │  │ • Device: CPU                │   │
│  │   devops_docs        │  └──────────────────────────────┘   │
│  └──────────────────────┘                                       │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────────────┐   │
│  │  Memory/State        │  │  Data Ingestion              │   │
│  │  (SQLite)            │  │  (ingestion/ingest_data.py)  │   │
│  ├──────────────────────┤  ├──────────────────────────────┤   │
│  │ • Checkpoint DB      │  │ • Load: PDFs/Text files      │   │
│  │ • Session state      │  │ • Parse: PyPDFLoader         │   │
│  │ • Conversation       │  │ • Split: Chunk (1000 chars)  │   │
│  │   history            │  │ • Embed: SentenceTransformers│   │
│  └──────────────────────┘  │ • Store: ChromaDB            │   │
│                             └──────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                    Data Sources                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input Logs (data/logs/)              Documentation (data/docs/)│
│  ├── docker_logs.txt                  ├── docker_troublesh...txt│
│  ├── server_logs.txt                  ├── linux_server...txt    │
│  └── python_errors.txt                └── python_debug...txt    │
│                                                                  │
│                         ↓ (Ingestion)                           │
│                                                                  │
│  Vector Database (vector_db/)                                   │
│  ├── chroma.db         (indices)                                │
│  └── *.parquet         (embeddings)                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                   Resource Requirements                          │
├─────────────────────────────────────────────────────────────────┤
│ Memory:      8 GB RAM (base) + 2-4 GB for models                │
│ Disk:        2-3 GB (Ollama model + embeddings)                 │
│ GPU:         Optional 1 GB VRAM (for acceleration)              │
│ CPU:         4+ cores recommended                               │
│ Network:     None (fully offline)                               │
└─────────────────────────────────────────────────────────────────┘

```

## Data Flow During Analysis

```
┌──────────────────────┐
│  Raw Log Input       │
│  "Error response..." │
└──────────┬───────────┘
           │
           ▼
    ┌─────────────────────────────────────────────┐
    │ LogParsingTool.parse_log()                  │
    │ Extract: component, error_type, keywords    │
    └──────────┬────────────────────────────────┘
               │
               ▼
    ┌─────────────────────────────────────────────┐
    │ Build Search Query                          │
    │ "docker port binding error"                 │
    └──────────┬────────────────────────────────┘
               │
               ▼
    ┌─────────────────────────────────────────────┐
    │ HuggingFaceEmbeddings.embed_query()         │
    │ Generate: 384-dim query vector              │
    └──────────┬────────────────────────────────┘
               │
               ▼
    ┌─────────────────────────────────────────────┐
    │ ChromaDB.query()                            │
    │ Find: Top-3 similar doc embeddings          │
    └──────────┬────────────────────────────────┘
               │
               ▼
    ┌─────────────────────────────────────────────┐
    │ Retrieved Docs + Analysis                   │
    │ → LLM generates solution                    │
    └──────────┬────────────────────────────────┘
               │
               ▼
    ┌─────────────────────────────────────────────┐
    │ Validation & Formatting                     │
    │ → Final structured output                   │
    └──────────┬────────────────────────────────┘
               │
               ▼
           ┌─────────────────────┐
           │ User Gets Solution  │
           │ • Root cause        │
           │ • Steps             │
           │ • Commands          │
           └─────────────────────┘
```

## Technology Stack Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Python 3.10+                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Orchestration        │  LLM & ML          │  Data              │
│  ──────────────────   │  ─────────────────  │  ───────          │
│  • LangChain 0.1+     │  • Ollama local    │  • ChromaDB        │
│  • LangGraph 0.0+     │  • LangChain-Ollama│  • SQLAlchemy      │
│  • Pydantic           │  • Sentence-       │  • PyPDF           │
│  •                    │    Transformers    │  • RecursiveText-  │
│                       │                    │    Splitter        │
│                       │                    │                    │
│  Testing              │  Runtime           │  Utilities         │
│  ────────             │  ──────────        │  ──────────        │
│  • PyTest             │  • Python logging  │  • Requests        │
│  • Mock               │  • PathLib         │  • Dotenv          │
│                       │                    │                    │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
Local Machine (Windows/Linux/Mac)
│
├── Python Virtual Environment
│   ├── Python 3.10+
│   ├── Dependencies (pip)
│   └── Application code
│
├── Local Services
│   ├── Ollama (LLM inference)
│   │   └── Models: mistral/llama2 (~7-13GB)
│   │
│   └── Vector Database (ChromaDB)
│       └── Embedded DuckDB + embeddings
│
├── Data Storage
│   ├── vector_db/ (embeddings)
│   ├── memory/ (checkpoints.sqlite)
│   └── data/ (logs & docs)
│
└── Configuration
    └── No external APIs, fully self-contained
```
