"""
Knowledge Graph builder using NetworkX.
Creates semantic relationships (imports, definitions, calls, inheritance).
"""
import networkx as nx
import os
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import GRAPH_DIR
from core.parser import ParsedModule

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def build_from_modules(self, modules: List[ParsedModule]):
        """Build graph from parsed modules."""
        self.graph.clear()
        
        # Add files as nodes
        for mod in modules:
            file_node = f"file:{mod.filepath}"
            self.graph.add_node(file_node, type="file", path=mod.filepath)
            
            # Module imports
            for imp in mod.imports:
                mod_node = f"module:{imp}"
                self.graph.add_node(mod_node, type="module", name=imp)
                self.graph.add_edge(file_node, mod_node, relation="imports")
                
            # Classes
            for cls in mod.classes:
                cls_node = f"class:{cls.name}"
                self.graph.add_node(cls_node, type="class", name=cls.name, file=mod.filepath, lineno=cls.lineno)
                self.graph.add_edge(file_node, cls_node, relation="contains")
                
                # Inheritance
                for base in cls.bases:
                    base_node = f"class:{base}"
                    # Might not exist yet, add it loosely
                    self.graph.add_node(base_node, type="class_reference", name=base)
                    self.graph.add_edge(cls_node, base_node, relation="inherits_from")
                    
                # Methods
                for method in cls.methods:
                    method_node = f"method:{cls.name}.{method.name}"
                    self.graph.add_node(method_node, type="method", name=method.name, file=mod.filepath, lineno=method.lineno)
                    self.graph.add_edge(cls_node, method_node, relation="contains")
                    
                    # Method calls
                    for call in method.calls:
                        call_node = f"call_ref:{call}"
                        self.graph.add_node(call_node, type="function_reference", name=call)
                        self.graph.add_edge(method_node, call_node, relation="calls")
                        
            # Standalone functions
            for func in mod.functions:
                func_node = f"function:{func.name}"
                self.graph.add_node(func_node, type="function", name=func.name, file=mod.filepath, lineno=func.lineno)
                self.graph.add_edge(file_node, func_node, relation="contains")
                
                # Function calls
                for call in func.calls:
                    call_node = f"call_ref:{call}"
                    self.graph.add_node(call_node, type="function_reference", name=call)
                    self.graph.add_edge(func_node, call_node, relation="calls")

        self.resolve_references()

    def resolve_references(self):
        """Map abstract call_refs to actual function/method nodes where possible."""
        # This is a heuristic resolution
        actual_funcs = {data["name"]: node for node, data in self.graph.nodes(data=True) if data.get("type") in ("function", "method")}
        
        edges_to_add = []
        edges_to_remove = []
        
        for u, v, data in self.graph.edges(data=True):
            if data.get("relation") == "calls":
                target_node_data = self.graph.nodes[v]
                if target_node_data.get("type") == "function_reference":
                    target_name = target_node_data.get("name")
                    if target_name in actual_funcs:
                        edges_to_add.append((u, actual_funcs[target_name], {"relation": "calls"}))
                        edges_to_remove.append((u, v))
                        
        self.graph.add_edges_from(edges_to_add)
        self.graph.remove_edges_from(edges_to_remove)
        
        # Clean up orphaned references
        orphans = [node for node, degree in self.graph.degree() if degree == 0 and self.graph.nodes[node].get("type") in ("function_reference", "class_reference")]
        self.graph.remove_nodes_from(orphans)

    def save(self, filename: str = "project_graph.gpickle", skip_save: bool = False):
        if skip_save:
            return
        path = GRAPH_DIR / filename
        with open(path, "wb") as f:
            pickle.dump(self.graph, f)

    def load(self, filename: str = "project_graph.gpickle") -> bool:
        path = GRAPH_DIR / filename
        if path.exists():
            with open(path, "rb") as f:
                self.graph = pickle.load(f)
            return True
        return False

    def get_file_dependencies(self, filepath: str) -> List[str]:
        file_node = f"file:{filepath}"
        if file_node not in self.graph:
            return []
            
        deps = []
        for _, v, data in self.graph.out_edges(file_node, data=True):
            if data.get("relation") == "imports":
                deps.append(self.graph.nodes[v].get("name", v))
        return deps
