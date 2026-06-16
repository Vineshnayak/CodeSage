import os
from groq import Groq
from core.query_engine import QueryEngine

class BugHunterAgent:
    def __init__(self, engine: QueryEngine, api_key: str = None):
        from config import GROQ_API_KEY
        self.api_key = api_key or GROQ_API_KEY
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        self.engine = engine

    def hunt_bug(self, traceback_text: str) -> str:
        if not self.client:
            return "Groq API Key not configured."
            
        from dotenv import dotenv_values
        from config import BASE_DIR
        env_vars = dotenv_values(BASE_DIR / ".env")
        current_model = env_vars.get("LLM_MODEL", "llama-3.1-8b-instant")
        
        # 1. Use the vector database to search our codebase based on the error
        vector_results = self.engine.vector_store.search(traceback_text, top_k=3)
        context_snippets = []
        for res in vector_results:
            context_snippets.append(
                f"File: {res['filepath']} (Lines {res['start_line']}-{res['end_line']})\n"
                f"```python\n{res['text']}\n```"
            )
        context_str = "\n".join(context_snippets)
        
        prompt = f"""You are an autonomous AI Debugging Agent.
Analyze the provided Python traceback and identify the root cause of the bug based on the codebase context retrieved from the vector database.
Explain the fix clearly and provide the corrected code.

IMPORTANT ANTI-HALLUCINATION INSTRUCTION:
If the provided RELATED CODEBASE CONTEXT does NOT contain the actual code causing the error or is completely unrelated, you MUST explicitly state that the relevant code was not found. Do NOT invent or hallucinate a fix based on unrelated context.

TRACEBACK:
{traceback_text}

RELATED CODEBASE CONTEXT (Found automatically):
{context_str}
"""
        try:
            response = self.client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": "You are an expert debugger."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"
