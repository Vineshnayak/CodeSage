"""
Impact Analyzer using graph traversal to predict breakage and risky changes.
"""
import networkx as nx
from typing import List, Dict, Any, Set
from core.knowledge_graph import KnowledgeGraph

class ImpactAnalyzer:
    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

    def analyze_impact(self, node_id: str, depth: int = 3) -> Dict[str, Any]:
        """
        Analyze what depends on a given node (file/function/class).
        Uses reverse graph traversal (what imports/calls this node).
        """
        if node_id not in self.kg.graph:
            return {"error": f"Node {node_id} not found in graph."}

        # We want to find nodes that have edges *to* our target node
        # In our graph, A imports B means edge A->B.
        # Call A calls B means edge A->B.
        # So things that depend on B have paths *to* B. We use reverse graph.
        rev_graph = self.kg.graph.reverse(copy=False)

        affected_nodes = set()
        queue = [(node_id, 0)]
        visited = {node_id}

        while queue:
            current, current_depth = queue.pop(0)
            if current != node_id:
                affected_nodes.add(current)
                
            if current_depth < depth:
                for neighbor in rev_graph.neighbors(current):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, current_depth + 1))

        # Categorize
        affected_files = []
        affected_functions = []
        affected_classes = []

        for node in affected_nodes:
            node_type = self.kg.graph.nodes[node].get("type", "unknown")
            node_name = self.kg.graph.nodes[node].get("name", node)
            if node_type == "file":
                affected_files.append(node_name)
            elif node_type in ("function", "method"):
                affected_functions.append(node_name)
            elif node_type == "class":
                affected_classes.append(node_name)

        # Risk Score heuristic: fan-in (how many things depend on it directly)
        fan_in = rev_graph.degree(node_id)
        risk_level = "High" if fan_in > 10 else "Medium" if fan_in > 3 else "Low"

        causal_reasoning = f"Modifying {node_id} has a {risk_level} risk. It directly affects {fan_in} components, and cascades down to {len(affected_nodes)} total components within {depth} hops."

        return {
            "node": node_id,
            "fan_in": fan_in,
            "risk_level": risk_level,
            "total_affected": len(affected_nodes),
            "files_affected": affected_files,
            "functions_affected": affected_functions,
            "classes_affected": affected_classes,
            "reasoning": causal_reasoning
        }
