"""
Graph Tool
Provides graph manipulation and analysis capabilities for agents.
"""

from __future__ import annotations
from typing import Any
from core.graph_builder import SystemGraph
from core.models import SystemNode, SystemEdge


class GraphTool:
    """Tool for graph operations - used by agents for graph manipulation."""
    
    def __init__(self, graph: SystemGraph):
        self.graph = graph
    
    def get_node_info(self, node_id: str) -> dict[str, Any]:
        """Get detailed information about a node."""
        node = self.graph.get_node(node_id)
        if not node:
            return {"error": f"Node {node_id} not found"}
        
        return {
            "id": node.id,
            "name": node.name,
            "type": node.node_type,
            "status": node.status.value if hasattr(node.status, 'value') else node.status,
            "health": node.health_score,
            "resilience": node.resilience,
            "tier": node.tier,
            "business_value": node.business_value,
            "load": f"{node.current_load:.1%}",
            "dependencies": self.graph.get_dependencies(node_id),
            "dependents": self.graph.get_dependents(node_id),
            "is_overloaded": node.is_overloaded,
        }
    
    def get_neighbors(self, node_id: str) -> dict[str, Any]:
        """Get all neighbors (dependencies + dependents) of a node."""
        return {
            "dependencies": self.graph.get_dependencies(node_id),
            "dependents": self.graph.get_dependents(node_id),
        }
    
    def get_blast_radius(self, node_id: str) -> dict[str, Any]:
        """Calculate blast radius for a node failure."""
        return self.graph.get_failure_blast_radius(node_id)
    
    def get_criticality_ranking(self) -> list[dict[str, Any]]:
        """Get nodes ranked by criticality score."""
        criticality = self.graph.calculate_node_criticality()
        ranked = sorted(criticality.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {
                "node_id": nid,
                "name": self.graph.nodes[nid].name if nid in self.graph.nodes else nid,
                "criticality": score,
                "tier": self.graph.nodes[nid].tier if nid in self.graph.nodes else 0,
            }
            for nid, score in ranked
        ]
    
    def find_path(self, source_id: str, target_id: str) -> list[str]:
        """Find shortest path between two nodes."""
        import networkx as nx
        try:
            path = nx.shortest_path(self.graph.graph, source_id, target_id)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
    
    def get_subgraph(self, node_ids: list[str]) -> dict[str, Any]:
        """Get a subgraph containing only specified nodes."""
        nodes = []
        edges = []
        
        node_set = set(node_ids)
        for nid in node_ids:
            node = self.graph.get_node(nid)
            if node:
                nodes.append({
                    "id": nid,
                    "name": node.name,
                    "type": node.node_type,
                    "status": node.status.value if hasattr(node.status, 'value') else node.status,
                })
        
        for edge in self.graph.edges.values():
            if edge.source_id in node_set and edge.target_id in node_set:
                edges.append({
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "relationship": edge.relationship,
                })
        
        return {"nodes": nodes, "edges": edges}
    
    def get_metrics(self) -> dict[str, Any]:
        """Get overall graph metrics."""
        return self.graph.get_graph_metrics()