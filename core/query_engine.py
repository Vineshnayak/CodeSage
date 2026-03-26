"""
Query Engine: Combines Graph Traversal, Vector Search, and LLM to answer code queries.
"""
from typing import List, Dict, Any, Tuple
from groq import Groq

from config import GROQ_API_KEY, LLM_MODEL
from core.knowledge_graph import KnowledgeGraph
from core.embeddings import EmbeddingStore

class QueryEngine:
    def __init__(self, kg: KnowledgeGraph, vector_store: EmbeddingStore):
        self.kg = kg
        self.vector_store = vector_store
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

    def query(self, question: str) -> str:
        """Process a natural language query and return an answer."""
        
        # 1. Vector Search for relevant code context
        vector_results = self.vector_store.search(question, top_k=3)
        context_snippets = []
        relevant_files = set()
        
        for res in vector_results:
            context_snippets.append(
                f"File: {res['filepath']} (Lines {res['start_line']}-{res['end_line']})\n"
                f"```python\n{res['text']}\n```"
            )
            relevant_files.add(res['filepath'])

        # 2. Graph Traversal for relationships (Multi-hop reasoning context)
        graph_context = []
        for filepath in relevant_files:
            deps = self.kg.get_file_dependencies(filepath)
            if deps:
                graph_context.append(f"File {filepath} imports: {', '.join(deps)}")
                
            # Find classes and functions in this file from the graph
            file_node = f"file:{filepath}"
            if file_node in self.kg.graph:
                entities = []
                for _, v, data in self.kg.graph.out_edges(file_node, data=True):
                    if data.get("relation") == "contains":
                        node_data = self.kg.graph.nodes[v]
                        entities.append(f"{node_data.get('type')}: {node_data.get('name')}")
                if entities:
                    graph_context.append(f"File {filepath} contains: {', '.join(entities)}")

        # Assemble prompt
        context_str = "\n\n".join(context_snippets)
        graph_str = "\n".join(graph_context)
        
        prompt = f"""You are an expert AI software architect and developer. 
Answer the user's question about the codebase based ONLY on the provided context.

QUESTION:
{question}

CODE SNIPPETS (Semantic search results):
{context_str}

ARCHITECTURE CONTEXT (Knowledge graph relations):
{graph_str}

Please provide a detailed, accurate answer. Include code reasoning and mention specific files or functions.
If the context doesn't contain enough information to answer fully, state that clearly.
"""

        # 3. Call LLM
        if not self.client:
            return "Groq API Key not configured. Cannot generate LLM response.\n\nContext found:\n" + context_str

        # Ensure we read directly from the .env file to completely bypass Python's module caching
        from dotenv import dotenv_values
        from config import BASE_DIR
        env_vars = dotenv_values(BASE_DIR / ".env")
        current_model = env_vars.get("LLM_MODEL", "llama-3.1-8b-instant")

        try:
            response = self.client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": "You are a helpful codebase intelligence assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            answer = response.choices[0].message.content
            
            try:
                from db.database import save_chat_query
                save_chat_query(question, answer, current_model)
                print(f"✅ Successfully asked query and triggered MongoDB save!")
            except Exception as e:
                print(f"❌ Failed to reach or save to MongoDB in query engine: {e}")
                
            return answer
        except Exception as e:
            return f"Error communicating with LLM: {str(e)}"
