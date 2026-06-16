---
title: CodeSage
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: 1.28.0
app_file: ui/app.py
pinned: false
---

# CodeSage

CodeSage is a codebase analysis tool that combines static analysis and Retrieval-Augmented Generation (RAG) to assist with code exploration and refactoring. It uses Abstract Syntax Tree (AST) parsing, vector embeddings, and dependency graph traversal to answer architectural queries and compute complexity metrics.

## Features

### 1. Codebase Querying
The system implements a RAG pipeline to process natural language queries about the codebase:
- **Vector Search:** Converts queries into dense vector embeddings and retrieves relevant code segments from a local FAISS index.
- **Graph Context:** Extracts structural relationships (imports, class hierarchies, function calls) using an in-memory `NetworkX` graph.
- **LLM Integration:** Passes the context to a Large Language Model (via Groq) to synthesize responses based on the provided codebase data.

### 2. Dependency Graph and Impact Analysis
Constructs a relational dependency graph mapping files, classes, and methods. Users can supply a target module to identify its downstream dependencies and evaluate the potential impact of modifications.

### 3. Static Code Analysis
Utilizes Python's native `ast` module to analyze source code complexity. It tracks:
- Cyclomatic complexity.
- Function length and parameter counts.
- Multiple-exit-point control structures.

### 4. Assisted Refactoring and Debugging
Integrates LLM-driven tools for code maintenance:
- **Bug Hunter:** Analyzes error tracebacks, locates the failing source file using the vector index, and suggests fixes.
- **Auto-Refactor:** Processes specified code blocks to recommend PEP-8 compliant and structurally improved alternatives.

### 5. File System Monitoring
A watchdog daemon monitors the active directory tree for modifications, updating semantic vectors and the AST graph to maintain index consistency.

## Technical Architecture

*   **Analysis:** `ast`, `networkx`
*   **Vector Search:** `sentence-transformers` (`all-MiniLM-L6-v2`), `faiss-cpu`
*   **LLM API:** Groq (`llama-3.1-8b-instant`)
*   **UI Framework:** Streamlit

## Setup and Deployment

**1. Environment Setup**
Requires Python 3.10 or higher.
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Configuration**
Copy the `.env.example` template to `.env` and configure your API keys:
```ini
GROQ_API_KEY=your_api_key_here
LLM_MODEL=llama-3.1-8b-instant
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## Usage

The application requires an initial index of the codebase to process queries.

**1. Build the Index**
Parse the target directory to generate the required index artifacts:
```bash
python3 main.py index
```

**2. Start the Interface**
Launch the Streamlit dashboard locally:
```bash
python3 main.py ui
```
*The Streamlit client runs on `localhost:8501` by default.*

**3. Run the File Monitor (Optional)**
Start a background process to update the index upon file modifications:
```bash
python3 main.py watch
```
