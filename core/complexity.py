"""
Code complexity and risk detection using heuristics (AST-based).
"""
import ast
from typing import Dict, Any, List

class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.complexity_score = 1
        self.returns = 0
        self.loops = 0

    def visit_If(self, node):
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity_score += 1
        self.loops += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity_score += 1
        self.loops += 1
        self.generic_visit(node)

    def visit_Try(self, node):
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_Return(self, node):
        self.returns += 1
        self.generic_visit(node)


def analyze_function_complexity(func_node: ast.FunctionDef) -> Dict[str, Any]:
    """Calculate cyclomatic complexity and risk for a function."""
    visitor = ComplexityVisitor()
    visitor.visit(func_node)
    
    # Calculate lines
    lines = func_node.end_lineno - func_node.lineno if hasattr(func_node, 'end_lineno') and func_node.end_lineno else 1
    
    # Params
    params = len(func_node.args.args)
    if func_node.args.vararg: params += 1
    if func_node.args.kwarg: params += 1

    score = visitor.complexity_score
    risk = "Low"
    issues = []
    
    if score > 10:
        risk = "Medium"
        issues.append(f"High cyclomatic complexity ({score})")
    if score > 15:
        risk = "High"
    
    if lines > 50:
        if risk != "High": risk = "Medium"
        issues.append(f"Function too long ({lines} lines)")
        
    if params > 5:
        issues.append(f"Too many parameters ({params})")
        
    if visitor.returns > 3:
        issues.append(f"Multiple exit points ({visitor.returns} returns)")

    return {
        "name": func_node.name,
        "complexity": score,
        "lines": lines,
        "parameters": params,
        "risk": risk,
        "issues": issues
    }

def analyze_file_complexity(filepath: str) -> List[Dict[str, Any]]:
    """Scan file for complex or risky functions."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
            
        results = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                res = analyze_function_complexity(node)
                if res["risk"] in ("Medium", "High") or res["issues"]:
                    results.append(res)
        return results
    except Exception as e:
        return []
