"""
Code parser using the standard `ast` module.
Extracts classes, functions, docstrings, imports, and calls.
"""
import ast
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set

from config import SUPPORTED_EXTENSIONS, IGNORE_DIRS, MAX_FILE_SIZE_KB

@dataclass
class ParsedFunction:
    name: str
    lineno: int
    end_lineno: int
    docstring: Optional[str]
    args: List[str]
    calls: Set[str] = field(default_factory=set)

@dataclass
class ParsedClass:
    name: str
    lineno: int
    end_lineno: int
    docstring: Optional[str]
    bases: List[str]
    methods: List[ParsedFunction] = field(default_factory=list)

@dataclass
class ParsedModule:
    filepath: str
    imports: Set[str] = field(default_factory=set)
    classes: List[ParsedClass] = field(default_factory=list)
    functions: List[ParsedFunction] = field(default_factory=list)

class CodeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports = set()
        self.classes = []
        self.functions = []
        
        self.current_class = None
        self.current_function = None

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node)

    def visit_Call(self, node):
        if self.current_function:
            # Try to extract the name of the called function
            if isinstance(node.func, ast.Name):
                self.current_function.calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                self.current_function.calls.add(node.func.attr)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(base.attr)
                
        parsed_class = ParsedClass(
            name=node.name,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node),
            bases=bases
        )
        
        self.classes.append(parsed_class)
        self.current_class = parsed_class
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node):
        # Handle async functions as well
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._handle_function(node)

    def _handle_function(self, node):
        args = [arg.arg for arg in node.args.args]
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
            
        parsed_func = ParsedFunction(
            name=node.name,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node),
            args=args
        )
        
        if self.current_class:
            self.current_class.methods.append(parsed_func)
        else:
            self.functions.append(parsed_func)
            
        prev_func = self.current_function
        self.current_function = parsed_func
        self.generic_visit(node)
        self.current_function = prev_func


class ProjectParser:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)

    def should_parse(self, filepath: Path) -> bool:
        if filepath.suffix not in SUPPORTED_EXTENSIONS:
            return False
            
        # Check if in ignore dir
        for part in filepath.parts:
            if part in IGNORE_DIRS:
                return False
                
        # Check size
        if filepath.stat().st_size > MAX_FILE_SIZE_KB * 1024:
            return False
            
        return True

    def parse_file(self, filepath: Path) -> Optional[ParsedModule]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            tree = ast.parse(content, filename=str(filepath))
            visitor = CodeVisitor()
            visitor.visit(tree)
            
            # Use relative path for cleaner graph nodes
            rel_path = str(filepath.relative_to(self.root_dir))
            
            return ParsedModule(
                filepath=rel_path,
                imports=visitor.imports,
                classes=visitor.classes,
                functions=visitor.functions
            )
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return None

    def parse_project(self) -> List[ParsedModule]:
        modules = []
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                filepath = Path(root) / file
                if self.should_parse(filepath):
                    module = self.parse_file(filepath)
                    if module:
                        modules.append(module)
        return modules
