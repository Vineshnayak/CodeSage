"""
Semantic Insight — Configuration
Central configuration for all modules.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = DATA_DIR / "index"
GRAPH_DIR = DATA_DIR / "graph"

# Create directories if they don't exist
INDEX_DIR.mkdir(parents=True, exist_ok=True)
GRAPH_DIR.mkdir(parents=True, exist_ok=True)

# ── LLM Configuration ─────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

USE_LOCAL_EMBEDDINGS = True
USE_GROQ_LLM = True

# ── Parser Configuration ──────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".py"}
IGNORE_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "env",
    "node_modules", ".tox", ".mypy_cache", ".pytest_cache",
    "dist", "build", "egg-info", ".eggs", ".idea", ".vscode",
}
MAX_FILE_SIZE_KB = 500  # Skip files larger than this

# ── Embedding Configuration ───────────────────────────────────────────────
EMBEDDING_DIMENSION = 384  # For all-MiniLM-L6-v2
CHUNK_MAX_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 64

# ── Complexity Thresholds ─────────────────────────────────────────────────
COMPLEXITY_HIGH = 15
COMPLEXITY_MEDIUM = 10
MAX_FUNCTION_LINES = 50
MAX_PARAMS = 7
MAX_NESTING_DEPTH = 4

# ── Server ─────────────────────────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8000
STREAMLIT_PORT = 8501
