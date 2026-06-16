"""
FAISS Vector Database module for storing and retrieving code embeddings using OpenAI embeddings.
"""
import faiss
import numpy as np
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer

from config import INDEX_DIR, EMBEDDING_DIMENSION, EMBEDDING_MODEL

class EmbeddingStore:
    def __init__(self):
        # We know all-MiniLM-L6-v2 dimension is 384
        self.dimension = 384 
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
        
        self.index_path = INDEX_DIR / "faiss.index"
        self.meta_path = INDEX_DIR / "metadata.json"
        
        # We use a small local embedding (~80MB) because Groq doesn't have embeddings
        try:
            self.model = SentenceTransformer(EMBEDDING_MODEL)
        except Exception as e:
            print(f"Error loading embedding model: {e}")
            self.model = None

    def _get_embedding(self, text: str) -> List[float]:
        if not self.model:
            return [0.0] * self.dimension
        try:
            return self.model.encode(text).tolist()
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return [0.0] * self.dimension

    def chunk_and_embed_file(self, filepath: str, content: str):
        """Chunk a file and add to FAISS."""
        # Simple chunking by lines for now, or by functions in a real system
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Very simple token estimate heuristic (1 word ~= 1.3 tokens)
        for i, line in enumerate(lines):
            current_chunk.append(line)
            current_length += len(line.split())
            
            if current_length > 300 or i == len(lines) - 1:
                chunk_text = "\n".join(current_chunk)
                chunks.append({
                    "filepath": filepath,
                    "text": chunk_text,
                    "start_line": i - len(current_chunk) + 1,
                    "end_line": i
                })
                current_chunk = []
                current_length = 0
                
        # Embed
        vectors = []
        for c in chunks:
            vec = self._get_embedding(c["text"])
            vectors.append(vec)
            self.metadata.append(c)
            
        if vectors:
            vec_array = np.array(vectors, dtype=np.float32)
            self.index.add(vec_array)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.index.ntotal == 0:
            return []
            
        query_vec = np.array([self._get_embedding(query)], dtype=np.float32)
        distances, indices = self.index.search(query_vec, top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.metadata):
                res = self.metadata[idx].copy()
                res["score"] = float(distances[0][i])
                results.append(res)
                
        return results

    def save(self, skip_save: bool = False):
        if skip_save:
            return
        faiss.write_index(self.index, str(self.index_path))
        with open(self.meta_path, "w") as f:
            json.dump(self.metadata, f)

    def load(self) -> bool:
        if self.index_path.exists() and self.meta_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            with open(self.meta_path, "r") as f:
                self.metadata = json.load(f)
            return True
        return False
        
    def clear(self):
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
