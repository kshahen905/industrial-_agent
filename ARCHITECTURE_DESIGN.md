# DevOps Log Analyzer - System Architecture

## Architecture Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DevOps Multi-Agent Log Analyzer                          │
│                          System Architecture                                │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────┐
                              │   User Input     │
                              │  (Log Message)   │
                              └────────┬─────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────────────────────┐
        │              PHASE 1: DATA INGESTION & GROUNDING             │
        │                                                              │
        │  ┌────────────────┐     ┌───────────────┐   ┌────────────┐ │
        │  │ Documentation  │────▶│  Embeddings   │──▶│ ChromaDB   │ │
        │  │   Files        │     │  Generation   │   │ Vector DB  │ │
        │  │ • Docker       │     │ (MinLM-L6)    │   │            │ │
        │  │ • Linux        │     │               │   │ 17 Chunks  │ │
        │  │ • Python       │     │               │   │ 4+ Tags    │ │
        │  └────────────────┘     └───────────────┘   └────────────┘ │
        │       ingest_data.py     (tools.py)         (vector_db/)   │
        └──────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────────────────────┐
        │         PHASE 2: LANGGRAPH MULTI-AGENT ORCHESTRATION         │
        │                                                              │
        │   ┌──────────────────────────────────────────────────────┐  │
        │   │              STATE GRAPH                             │  │
        │   │  ┌─────────────────────────────────────────────┐    │  │
        │   │  │ GraphState:                                 │    │  │
        │   │  │ • messages: list[str]                       │    │  │
        │   │  │ • original_log: str                         │    │  │
        │   │  │ • parsed_log: dict                          │    │  │
        │   │  │ • retrieved_docs: list                      │    │  │
        │   │  │ • solution: str                             │    │  │
        │   │  │ • final_output: str                         │    │  │
        │   │  └─────────────────────────────────────────────┘    │  │
        │   └──────────────────────────────────────────────────────┘  │
        │                           │                                 │
        │                           ▼                                 │
        │   ┌───────────────────────────────────────────────┐         │
        │   │  NODE EXECUTION FLOW (LangGraph)              │         │
        │   │                                               │         │
        │   │  Node 1: log_analysis_node                    │         │
        │   │  ├─ Parses log → component, error_type       │         │
        │   │  ├─ Calls: LogParsingTool                    │         │
        │   │  └─ Updates state: parsed_log                │         │
        │   │           │                                  │         │
        │   │           ▼                                  │         │
        │   │  Node 2: retrieval_node                       │         │
        │   │  ├─ Builds search query from parsed_log      │         │
        │   │  ├─ Calls: VectorSearchTool                  │         │
        │   │  ├─ Filters: doc_type, error_category       │         │
        │   │  └─ Updates state: retrieved_docs (3 docs)   │         │
        │   │           │                                  │         │
        │   │           ▼                                  │         │
        │   │  Node 3: solution_generation_node             │         │
        │   │  ├─ Combines: parsed_log + retrieved_docs    │         │
        │   │  ├─ Calls: CommandGeneratorTool              │         │
        │   │  ├─ LLM generates: Root cause + steps        │         │
        │   │  └─ Updates state: solution                  │         │
        │   │           │                                  │         │
        │   │           ▼                                  │         │
        │   │  Node 4: validation_node                      │         │
        │   │  ├─ Reviews proposed solution                │         │
        │   │  ├─ Validates: accuracy + safety             │         │
        │   │  ├─ Formats output                           │         │
        │   │  └─ Updates state: final_output              │         │
        │   │           │                                  │         │
        │   │           ▼                                  │         │
        │   │  ROUTING: END (Return final_output)           │         │
        │   │                                               │         │
        │   └───────────────────────────────────────────────┘         │
        │                                                              │
        │         (graph/multi_agent_graph.py)                        │
        └──────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────────────────────┐
        │                    TOOLS LAYER                               │
        │                                                              │
        │  VectorSearchTool          LogParsingTool                   │
        │  ├─ Queries ChromaDB       ├─ Pattern matching             │
        │  ├─ Semantic search        ├─ Component detection          │
        │  ├─ Metadata filtering     ├─ Error type classification    │
        │  └─ Returns 3 docs         └─ Category assignment          │
        │                                                              │
        │  CommandGeneratorTool                                       │
        │  ├─ Diagnostic commands                                    │
        │  ├─ Fix commands                                           │
        │  └─ Verification commands                                  │
        │                                                              │
        │           (tools/tools.py)                                  │
        └──────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────────────────────┐
        │                    OUTPUT LAYER                              │
        │                                                              │
        │  ╔════════════════════════════════════════════════════════╗ │
        │  ║  DevOps Log Analysis - Final Recommendation            ║ │
        │  ╚════════════════════════════════════════════════════════╝ │
        │                                                              │
        │  Component: [identified]                                   │
        │  Error Type: [classified]                                  │
        │                                                              │
        │  Root Cause: [LLM analysis + grounding]                    │
        │                                                              │
        │  Solution Steps:                                            │
        │    1. [Diagnostic step]                                     │
        │    2. [Fix step]                                            │
        │    3. [Verification step]                                   │
        │                                                              │
        │  Commands:                                                  │
        │    $ [command 1 with explanation]                           │
        │    $ [command 2 with explanation]                           │
        │                                                              │
        │  Quality Assessment:                                        │
        │    ✓ Technical Accuracy: [LLM validation]                  │
        │    ✓ Safety Concerns: [Risk analysis]                      │
        │    ✓ Logical Order: [Step sequence validation]             │
        │    ✓ Clarity: [Formatting review]                          │
        │                                                              │
        └──────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
                              ┌──────────────┐
                              │ User Output  │
                              │ (Solution)   │
                              └──────────────┘
```

---

## 🏗️ **System Components Breakdown**

### **1. Data Ingestion Pipeline (`ingestion/ingest_data.py`)**

**Purpose**: Load, clean, chunk, and vectorize DevOps documentation

**Flow**:
```
Raw Text Files
    ↓
Load & Clean (UTF-8 encoding, strip noise)
    ↓
Semantic Chunking (1000 chars, 200 overlap)
    ↓
Metadata Enrichment (4+ tags per chunk):
    • doc_type: [docker, linux, python, general]
    • error_category: [containerization, system, application, etc.]
    • priority_level: [high, medium, low]
    • last_updated: [date]
    ↓
Embedding Generation (all-MiniLM-L6-v2)
    ↓
ChromaDB Storage (17 chunks, indexed)
```

**Features**:
- ✅ Automatic document type detection
- ✅ 4 metadata tags per chunk (Lab 2 requirement: 3+)
- ✅ Metadata filtering support for precise retrieval
- ✅ Error handling for corrupted files

---

### **2. Tools Module (`tools/tools.py`)**

Three primary tools with Pydantic validation:

#### **Tool 1: VectorSearchTool**
```python
Input: Search query (string)
       Top K (int, default 3)
       Metadata filters (dict, optional)

Process:
  1. Generate query embedding
  2. Search ChromaDB semantic index
  3. Apply metadata filters (doc_type, error_category, priority)
  4. Return top 3 documents with scores

Output: List[Dict] with content, source, relevance scores
```

#### **Tool 2: LogParsingTool**
```python
Input: Raw log message (string)

Process:
  1. Pattern matching against 50+ regex patterns
  2. Extract component (Docker, Linux, Python, etc.)
  3. Extract error type (oom, connection_refused, etc.)
  4. Classify error category (resource_exhaustion, etc.)

Output: Dict with component, error_type, error_category
```

#### **Tool 3: CommandGeneratorTool**
```python
Input: Component (string)
       Error type (string)

Process:
  1. Route to component-specific command set
  2. Generate diagnostic commands (free, top, netstat, etc.)
  3. Generate fix commands (restart, config change, etc.)
  4. Generate verification commands

Output: List[str] with safe, tested commands
```

---

### **3. Agents Configuration (`agents/agents_config.py`)**

**Four Specialized Agents** (with distinct personas):

| Agent | Role | Tools | Input | Output |
|-------|------|-------|-------|--------|
| **Log Analyzer** | Parse logs | LogParsingTool | Raw log | Parsed components |
| **Retriever** | Find docs | VectorSearchTool | Parsed log | Relevant docs |
| **Solution Gen** | Generate fixes | CommandGeneratorTool + LLM | Parsed + docs | Solution steps |
| **Validator** | Review quality | LLM validation | Proposed solution | Refined output |

---

### **4. LangGraph Orchestration (`graph/multi_agent_graph.py`)**

**Graph State Structure**:
```python
{
    "messages": [],              # Conversation history
    "original_log": "",          # Input log
    "parsed_log": {},            # Analysis results
    "retrieved_docs": [],        # ChromaDB results
    "solution": "",              # Generated solution
    "final_output": ""          # Formatted output
}
```

**Execution Flow**:
```
START
  │
  ├─→ [log_analysis_node]
  │   - Calls LogParsingTool
  │   - Calls LLM for analysis
  │   - Updates: parsed_log
  │
  ├─→ [retrieval_node]
  │   - Builds search query
  │   - Calls VectorSearchTool
  │   - Applies metadata filters
  │   - Updates: retrieved_docs
  │
  ├─→ [solution_generation_node]
  │   - Combines parsed_log + retrieved_docs
  │   - Calls CommandGeneratorTool
  │   - LLM generates solution
  │   - Updates: solution
  │
  ├─→ [validation_node]
  │   - Reviews for accuracy
  │   - Validates safety
  │   - Formats output
  │   - Updates: final_output
  │
  └─→ END
      Return: final_output
```

**Sequential Router**:
- No conditional branching currently
- Always follow: Analysis → Retrieval → Generation → Validation

---

### **5. Main Entry Point (`main.py`)**

**Responsibilities**:
1. Environment setup verification (Ollama, ChromaDB)
2. System initialization (tools, agents, graph)
3. Interactive user loop
4. Demo mode with sample logs

**Execution Modes**:
```bash
# Interactive mode (default)
python main.py
>>> Enter log message: [user input]

# Demo mode
python main.py --demo

# Specific analysis
python main.py --analyze "error message"
```

---

## 📊 **Data Flow Diagram**

```
User Input (DevOps Log)
        │
        ▼
┌───────────────────────────────────────────┐
│ Environmental Verification                │
│ • Ollama connection status                │
│ • ChromaDB accessibility                  │
│ • Model availability                      │
└───────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────┐
│ Data Ingestion Check                      │
│ • Vector DB exists?                       │
│ • 17 chunks loaded?                       │
│ • Metadata indexed?                       │
└───────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────┐
│ Agent System Initialization               │
│ • Load config (agents_config.py)          │
│ • Initialize LLM (phi3:mini)              │
│ • Create tool instances                   │
│ • Compile LangGraph                       │
└───────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────┐
│ User Input Processing                     │
│ • Accept log message                      │
│ • Validate input                          │
│ • Start graph execution                   │
└───────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────┐
│ Multi-Agent Pipeline Execution            │
│                                           │
│ Agent 1: Parse & Identify                │
│ ├─ Input: Raw log                        │
│ └─ Output: Component + Error type        │
│                                           │
│ Agent 2: Retrieve Documentation          │
│ ├─ Input: Parsed components              │
│ └─ Output: 3 relevant docs               │
│                                           │
│ Agent 3: Generate Solution               │
│ ├─ Input: Parsed + Docs                  │
│ └─ Output: Steps + Commands              │
│                                           │
│ Agent 4: Validate & Format               │
│ ├─ Input: Proposed solution              │
│ └─ Output: Final recommendation          │
└───────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────┐
│ Output Formatting & Display               │
│ • Structured output generation           │
│ • ASCII formatting                        │
│ • Console display                         │
└───────────────────────────────────────────┘
        │
        ▼
User Output (Solution Report)
```

---

## 🔄 **Technology Stack & Mappings**

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **LLM** | Ollama (phi3:mini) | Local, offline reasoning |
| **Orchestration** | LangGraph | Agent workflow management |
| **Embeddings** | SentenceTransformers (all-MiniLM-L6-v2) | Document vectorization |
| **Vector DB** | ChromaDB | Semantic search & storage |
| **Language** | Python 3.10+ | Implementation |
| **Config** | config.py + .env | Centralized settings |
| **Chunking** | RecursiveCharacterTextSplitter | Semantic document splitting |
| **Format** | Pydantic | Input validation |

---

## 📈 **Scalability & Extension Points**

### **Future Enhancements**:

1. **Add New Components**:
   - Update `data/docs/` with new documentation
   - Metadata tags automatically applies
   - Run `python ingestion/ingest_data.py` to re-index

2. **Add New Tools**:
   - Create tool function in `tools.py`
   - Add @tool decorator
   - Reference in agent nodes

3. **Add New Agents**:
   - Define persona in `agents_config.py`
   - Assign tools
   - Add node in `multi_agent_graph.py`

4. **Modify Graph Flow**:
   - Change routing in `multi_agent_graph.py`
   - Add conditional logic
   - Implement loops or branching

---

## ✅ **Lab Compliance Checklist**

- [✅] **Lab 1**: Use-case selected (DevOps), architecture documented
- [✅] **Lab 2**: RAG pipeline with metadata (4 tags), vector indexing
- [✅] **Lab 3**: LangGraph with tools and state management
- [⏳] **Lab 4**: Multi-agent setup (needs role restriction)
- [⏳] **Lab 5**: HITL & checkpointing (to be implemented)

---

## 📖 **How to Use This Diagram**

1. **For Understanding**: Follow the data flow from top to bottom
2. **For Troubleshooting**: Check each component in the stack
3. **For Extension**: Identify the right layer to add features
4. **For Documentation**: Use as reference for system design

---

**Architecture created**: March 8, 2026
**LangGraph framework**: Multi-nodeagent orchestration
**Status**: Operational with Phase 1-2 complete, Phase 3-5 pending
