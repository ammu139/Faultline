"""
Faultline Graph Builder
Constructs and manages the system dependency graph using NetworkX.
"""

from __future__ import annotations
from typing import Any, Optional
import networkx as nx
import numpy as np
from core.models import SystemNode, SystemEdge, NodeStatus, ScenarioConfig
from config import NODE_TYPES, EDGE_TYPES


class SystemGraph:
    """
    Core dependency graph engine.
    Builds, analyzes, and manipulates the system topology.
    """
    
    def __init__(self):
        self.graph: nx.DiGraph = nx.DiGraph()
        self.nodes: dict[str, SystemNode] = {}
        self.edges: dict[str, SystemEdge] = {}
        self._layout_cache: Optional[dict] = None
    
    def add_node(self, node: SystemNode) -> None:
        """Add a system node to the graph."""
        self.nodes[node.id] = node
        node_attrs = {
            "name": node.name,
            "node_type": node.node_type,
            "status": node.status,
            "health_score": node.health_score,
            "resilience": node.resilience,
            "business_value": node.business_value,
            "tier": node.tier,
            "load_capacity": node.load_capacity,
            "current_load": node.current_load,
        }
        self.graph.add_node(node.id, **node_attrs)
        self._layout_cache = None
    
    def add_edge(self, edge: SystemEdge) -> None:
        """Add a dependency edge to the graph."""
        self.edges[edge.id] = edge
        edge_attrs = {
            "relationship": edge.relationship,
            "weight": edge.weight,
            "is_critical": edge.is_critical,
            "latency_ms": edge.latency_ms,
            "failure_probability": edge.failure_probability,
        }
        self.graph.add_edge(edge.source_id, edge.target_id, **edge_attrs)
        self._layout_cache = None
    
    def build_from_scenario(self, scenario: ScenarioConfig) -> None:
        """Build the graph from a scenario configuration."""
        self.clear()
        for node in scenario.nodes:
            self.add_node(node)
        for edge in scenario.edges:
            self.add_edge(edge)
    
    def clear(self) -> None:
        """Clear the graph."""
        self.graph.clear()
        self.nodes.clear()
        self.edges.clear()
        self._layout_cache = None
    
    def get_node(self, node_id: str) -> Optional[SystemNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def get_dependencies(self, node_id: str) -> list[str]:
        """Get all nodes that this node depends on (successors in directed graph)."""
        if node_id not in self.graph:
            return []
        return list(self.graph.successors(node_id))
    
    def get_dependents(self, node_id: str) -> list[str]:
        """Get all nodes that depend on this node (predecessors)."""
        if node_id not in self.graph:
            return []
        return list(self.graph.predecessors(node_id))
    
    def get_cascade_path(self, source_id: str, max_depth: int = 5) -> list[list[str]]:
        """
        Get the cascade propagation path from a source node.
        Returns waves of affected nodes at each depth level.
        """
        if source_id not in self.graph:
            return []
        
        waves = []
        visited = {source_id}
        current_wave = [source_id]
        
        for depth in range(max_depth):
            next_wave = []
            for node_id in current_wave:
                dependents = self.get_dependents(node_id)
                for dep in dependents:
                    if dep not in visited:
                        visited.add(dep)
                        next_wave.append(dep)
            
            if not next_wave:
                break
            waves.append(next_wave)
            current_wave = next_wave
        
        return waves
    
    def find_single_points_of_failure(self) -> list[str]:
        """Identify nodes whose removal disconnects the graph."""
        spofs = []
        # Use articulation points for undirected version
        undirected = self.graph.to_undirected()
        if nx.is_connected(undirected):
            spofs = list(nx.articulation_points(undirected))
        else:
            # Check each component
            for component in nx.connected_components(undirected):
                subgraph = undirected.subgraph(component)
                if len(subgraph) > 2:
                    spofs.extend(nx.articulation_points(subgraph))
        return spofs
    
    def find_critical_paths(self) -> list[list[str]]:
        """Find the most critical dependency chains."""
        critical_paths = []
        
        # Find paths between high-value nodes
        high_value_nodes = [
            nid for nid, node in self.nodes.items()
            if node.business_value > 0.7 or node.tier == 1
        ]
        
        for source in high_value_nodes:
            for target in high_value_nodes:
                if source != target:
                    try:
                        paths = list(nx.all_simple_paths(
                            self.graph, source, target, cutoff=5
                        ))
                        critical_paths.extend(paths)
                    except nx.NetworkXError:
                        continue
        
        # Sort by path length (longer = more fragile)
        critical_paths.sort(key=len, reverse=True)
        return critical_paths[:10]
    
    def calculate_node_criticality(self) -> dict[str, float]:
        """
        Calculate criticality score for each node based on:
        - Betweenness centrality
        - PageRank
        - Number of dependents
        - Business value
        """
        if len(self.graph) == 0:
            return {}
        
        # Betweenness centrality
        betweenness = nx.betweenness_centrality(self.graph)
        
        # PageRank
        try:
            pagerank = nx.pagerank(self.graph)
        except nx.PowerIterationFailedConvergence:
            pagerank = {n: 1.0 / len(self.graph) for n in self.graph.nodes()}
        
        # Combine metrics
        criticality = {}
        for node_id in self.graph.nodes():
            node = self.nodes.get(node_id)
            if node:
                dependent_count = len(self.get_dependents(node_id))
                max_dependents = max(len(self.get_dependents(n)) for n in self.graph.nodes()) or 1
                
                score = (
                    0.3 * betweenness.get(node_id, 0) +
                    0.2 * pagerank.get(node_id, 0) * len(self.graph) +
                    0.2 * (dependent_count / max_dependents) +
                    0.2 * node.business_value +
                    0.1 * (1.0 - node.resilience)
                )
                criticality[node_id] = min(1.0, score)
        
        return criticality
    
    def get_failure_blast_radius(self, node_id: str) -> dict[str, Any]:
        """Calculate the blast radius if a node fails."""
        cascade = self.get_cascade_path(node_id)
        all_affected = [node_id]
        for wave in cascade:
            all_affected.extend(wave)
        
        total_business_value = sum(
            self.nodes[nid].business_value
            for nid in all_affected
            if nid in self.nodes
        )
        
        critical_hit = any(
            self.nodes[nid].tier == 1
            for nid in all_affected
            if nid in self.nodes
        )
        
        return {
            "source": node_id,
            "affected_nodes": all_affected,
            "cascade_waves": cascade,
            "total_affected": len(all_affected),
            "total_business_value_at_risk": total_business_value,
            "hits_critical_tier": critical_hit,
            "max_depth": len(cascade),
        }
    
    def get_layout(self, algorithm: str = "spring") -> dict[str, tuple[float, float]]:
        """Calculate graph layout positions."""
        if self._layout_cache is not None:
            return self._layout_cache
        
        if len(self.graph) == 0:
            return {}
        
        if algorithm == "spring":
            pos = nx.spring_layout(self.graph, k=2, iterations=50, seed=42)
        elif algorithm == "kamada_kawai":
            pos = nx.kamada_kawai_layout(self.graph)
        elif algorithm == "circular":
            pos = nx.circular_layout(self.graph)
        elif algorithm == "shell":
            # Group by tier
            shells = []
            for tier in range(1, 5):
                tier_nodes = [
                    nid for nid, node in self.nodes.items()
                    if node.tier == tier
                ]
                if tier_nodes:
                    shells.append(tier_nodes)
            if shells:
                pos = nx.shell_layout(self.graph, nlist=shells)
            else:
                pos = nx.spring_layout(self.graph, seed=42)
        else:
            pos = nx.spring_layout(self.graph, seed=42)
        
        self._layout_cache = {k: (float(v[0]), float(v[1])) for k, v in pos.items()}
        return self._layout_cache
    
    def get_graph_metrics(self) -> dict[str, Any]:
        """Get overall graph metrics."""
        if len(self.graph) == 0:
            return {"nodes": 0, "edges": 0}
        
        undirected = self.graph.to_undirected()
        
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "density": nx.density(self.graph),
            "is_connected": nx.is_weakly_connected(self.graph),
            "components": nx.number_weakly_connected_components(self.graph),
            "avg_clustering": nx.average_clustering(undirected),
            "avg_degree": sum(dict(self.graph.degree()).values()) / max(len(self.graph), 1),
        }
    
    def to_serializable(self) -> dict[str, Any]:
        """Convert graph to a JSON-serializable format."""
        return {
            "nodes": [
                {
                    "id": nid,
                    "name": node.name,
                    "type": node.node_type,
                    "status": node.status,
                    "health": node.health_score,
                    "tier": node.tier,
                    "business_value": node.business_value,
                }
                for nid, node in self.nodes.items()
            ],
            "edges": [
                {
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "relationship": edge.relationship,
                    "weight": edge.weight,
                    "is_critical": edge.is_critical,
                }
                for edge in self.edges.values()
            ],
            "metrics": self.get_graph_metrics(),
        }