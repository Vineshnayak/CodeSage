import os
from groq import Groq

class RefactorAgent:
    def __init__(self, api_key: str = None):
        from config import GROQ_API_KEY
        self.api_key = api_key or GROQ_API_KEY
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def refactor_code(self, code: str, context: str) -> str:
        if not self.client:
            return "Groq API Key not configured."
            
        from dotenv import dotenv_values
        from config import BASE_DIR
        env_vars = dotenv_values(BASE_DIR / ".env")
        current_model = env_vars.get("LLM_MODEL", "llama-3.1-8b-instant")
        
        prompt = f"""You are an Expert Python Refactoring Agent.
Please refactor the following function to be more readable, efficient, and Pythonic.
- Reduce cyclomatic complexity if possible.
- Include Python type hints.
- Add a brief docstring.
Return ONLY the refactored code without conversational text.

Context where this is used: {context}

CODE TO REFACTOR:
```python
{code}
```
"""
        try:
            response = self.client.chat.completions.create(
                model=current_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            return response.choices[0].message.content.strip("`").replace("python\n", "")
        except Exception as e:
            return f"Error: {e}"
