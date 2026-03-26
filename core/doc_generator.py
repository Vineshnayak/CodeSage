"""
Automatic Documentation Generator.
"""
import os
from groq import Groq
from pathlib import Path

from config import GROQ_API_KEY, LLM_MODEL

class DocGenerator:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

    def generate_function_doc(self, logic_str: str) -> str:
        """Use LLM to generate a summary for a function based on its code."""
        if not self.client:
            return "No API Key configured. Cannot generate documentation."
            
        prompt = f"""Generate a concise, technical Markdown documentation block for the following Python code snippet. 
Include the purpose, parameters (if any), and return value.

CODE:
```python
{logic_str}
```
"""
        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert Python technical writer."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating doc: {e}"

    def generate_readme(self, structure_map: str) -> str:
        """Generate a project-level README."""
        if not self.client:
            return "No API Key configured. Cannot generate README."
            
        prompt = f"""Generate a comprehensive, professional project README.md based on the following project structure and brief description.
Include Sections: Overview, Installation, Architecture, Core Components.

STRUCTURE:
{structure_map}
"""
        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert repository documentarian."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating README: {e}"
