# CodeSage

CodeSage is a local codebase intelligence system that combines Retrieval-Augmented Generation (RAG) with static analysis to facilitate code exploration, refactoring, and quality assessment. By integrating Abstract Syntax Tree (AST) parsing, vector embeddings, and dependency graph traversal, the system provides contextual responses to architectural queries and calculates complexity metrics autonomously.

---

## Technical Capabilities

### 1. Semantic Codebase Querying
Users can query the codebase using natural language. The system implements a Retrieval-Augmented Generation pipeline:
- **Vector Search:** Converts queries into dense vector embeddings and retrieves relevant code segments from a local FAISS index.
- **Graph Augmentation:** Extracts relational context (imports, class hierarchies, function calls) from an in-memory `NetworkX` graph.
- **LLM Reasoning:** Passes the aggregated context to a Large Language Model (via Groq) to synthesize technically accurate responses based strictly on the provided codebase context.

### 2. Dependency Tracking & Impact Analysis
The system constructs a relational dependency graph mapping files, classes, and methods. Users can supply a target module to compute its fan-in configuration, revealing downstream dependencies and calculating its overall modification risk tier (often referred to as a "blast radius" analysis).

### 3. AST Complexity Heuristics
A static analysis engine utilizes Python's native `ast` module to evaluate code quality at runtime. It profiles the source code against explicit programmatic heuristics:
- Cyclomatic complexity tracking (branching density and nested control structures).
- Function length anomalies.
- Parameter count thresholds.
- Multiple-exit-point detection.

### 4. Autonomous Agents & Refactoring
CodeSage integrates specialized LLM-driven agents:
- **Bug Hunter:** Ingests unformatted error tracebacks, traverses the vector index to identify the failing source file, and proposes programmatic fixes.
- **Auto-Refactor:** Analyzes complex or unstructured code blocks and streams optimized, statically typed, and PEP-8 compliant suggestions back to the client interface.

### 5. Persistent Observation & Storage
- **Event-Driven Synchronization:** A `watchdog` daemon monitors the active directory tree for filesystem modifications, automatically calculating incremental semantic vectors and updating the AST graph to prevent index staleness.
- **Query Logging:** Integrates with `pymongo` to persistently log historical interactions, metadata, and LLM responses natively into a MongoDB database process without blocking the visualization thread.

---

## Technical Architecture & Stack

*   **Extraction & Mapping:** Native Python `ast`, `networkx`.
*   **Vector Engine:** `sentence-transformers` (`all-MiniLM-L6-v2`) generating embeddings stored in `faiss-cpu`.
*   **Reasoning API:** Groq (`llama-3.1-8b-instant`).
*   **Storage Configuration:** MongoDB (`mongodb://127.0.0.1:27018`).
*   **Interface Layer:** Streamlit runtime.

---

## Deployment & Setup

**1. Environment Initialization**
Ensure Python 3.10+ is installed on the host system.
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Environment Variables Configuration**
Rename the `.env.example` template to `.env` and configure the required API values:
```ini
GROQ_API_KEY=gsk_your_key_here
LLM_MODEL=llama-3.1-8b-instant
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

**3. MongoDB Provisioning**
To enable the UI Query History feature, initialize an isolated MongoDB daemon on port `27018`:
```bash
mkdir -p ~/mongodb-codesage
mongod --port 27018 --dbpath ~/mongodb-codesage
```

---

## Execution Routine

The system relies on cached embeddings and graph nodes before the interface can effectively parse queries.

**1. Calculate Base Index**
Recursively parse the target directory to generate `.index`, `.json`, and `.pkl` artifacts.
```bash
python3 main.py index
```

**2. Launch Visualization Client**
Start the main application dashboard locally.
```bash
python3 main.py ui
```
*The Streamlit client will bind to `localhost:8501` by default.*

**3. Run Watchdog Daemon (Concurrent Task)**
Optionally spin up a concurrent terminal to maintain index integrity as source code is modified in real-time.
```bash
python3 main.py watch
```
