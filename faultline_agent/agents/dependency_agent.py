"""
Dependency Agent
Builds and analyzes the dependency graph, identifying structural
vulnerabilities and critical paths.
"""

from __future__ import annotations
from typing import Any
from datetime import datetime
from agents.base_agent import BaseAgent, AgentResult
from core.graph_builder import SystemGraph
from core.models import ScenarioConfig


class DependencyAgent(BaseAgent):
    """
    Constructs the dependency graph and performs structural analysis
    to identify architectural vulnerabilities.
    """
    
    def __init__(self, graph: SystemGraph):
        super().__init__(
            name="DependencyAgent",
            description="Builds dependency graph and identifies structural vulnerabilities"
        )
        self.graph = graph
    
    def execute(self, context: dict[str, Any]) -> AgentResult:
        """
        Build the dependency graph and analyze its structure.
        
        Expected context:
            - scenario: ScenarioConfig
            - nodes: list of SystemNode
            - edges: list of SystemEdge
        """
        start_time = datetime.now()
        
        try:
            scenario = context.get("scenario")
            if not scenario:
                return self._build_result(
                    success=False,
                    error="No scenario provided",
                    start_time=start_time,
                )
            
            self.reason("Building dependency graph from scenario")
            
            # Build the graph
            self.graph.build_from_scenario(scenario)
            
            self.reason(f"Graph built: {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges")
            
            # Perform structural analysis
            analysis = self._analyze_structure()
            
            self.reason(f"Found {len(analysis['single_points_of_failure'])} single points of failure")
            self.reason(f"Identified {len(analysis['critical_paths'])} critical paths")
            
            # Calculate node criticality
            criticality = self.graph.calculate_node_criticality()
            analysis["criticality_scores"] = criticality
            
            # Identify high-risk clusters
            clusters = self._identify_risk_clusters(criticality)
            analysis["risk_clusters"] = clusters
            
            result_data = {
                "graph_metrics": self.graph.get_graph_metrics(),
                "analysis": analysis,
                "layout": self.graph.get_layout(),
            }
            
            self.send_message(
                "StressAgent",
                result_data,
                msg_type="graph_ready"
            )
            
            return self._build_result(
                success=True,
                data=result_data,
                start_time=start_time,
            )
        
        except Exception as e:
            return self._build_result(
                success=False,
                error=str(e),
                start_time=start_time,
            )
    
    def _analyze_structure(self) -> dict[str, Any]:
        """Perform comprehensive structural analysis."""
        spofs = self.graph.find_single_points_of_failure()
        critical_paths = self.graph.find_critical_paths()
        metrics = self.graph.get_graph_metrics()
        
        # Identify nodes with high fan-in (many dependents)
        high_fan_in = []
        for node_id in self.graph.graph.nodes():
            dependents = self.graph.get_dependents(node_id)
            if len(dependents) >= 3:
                node = self.graph.get_node(node_id)
                high_fan_in.append({
                    "node_id": node_id,
                    "name": node.name if node else node_id,
                    "dependent_count": len(dependents),
                })
        
        # Identify isolated components
        isolated = [
            nid for nid in self.graph.graph.nodes()
            if self.graph.graph.degree(nid) <= 1
        ]
        
        return {
            "single_points_of_failure": [
                {
                    "node_id": nid,
                    "name": self.graph.nodes[nid].name if nid in self.graph.nodes else nid,
                    "blast_radius": self.graph.get_failure_blast_radius(nid),
                }
                for nid in spofs
            ],
            "critical_paths": critical_paths,
            "high_fan_in_nodes": sorted(
                high_fan_in, key=lambda x: x["dependent_count"], reverse=True
            ),
            "isolated_nodes": isolated,
            "graph_density": metrics.get("density", 0),
            "is_connected": metrics.get("is_connected", False),
            "component_count": metrics.get("components", 1),
        }
    
    def _identify_risk_clusters(
        self, criticality: dict[str, float]
    ) -> list[dict[str, Any]]:
        """Identify clusters of high-risk nodes that are interconnected."""
        high_risk_nodes = [
            nid for nid, score in criticality.items()
            if score > 0.5
        ]
        
        clusters = []
        visited = set()
        
        for node_id in high_risk_nodes:
            if node_id in visited:
                continue
            
            # BFS to find connected high-risk nodes
            cluster = []
            queue = [node_id]
            
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                
                if current in high_risk_nodes or current == node_id:
                    cluster.append(current)
                    # Check neighbors
                    neighbors = (
                        self.graph.get_dependencies(current) +
                        self.graph.get_dependents(current)
                    )
                    for neighbor in neighbors:
                        if neighbor not in visited and neighbor in high_risk_nodes:
                            queue.append(neighbor)
            
            if len(cluster) >= 2:
                avg_criticality = sum(
                    criticality.get(nid, 0) for nid in cluster
                ) / len(cluster)
                clusters.append({
                    "nodes": cluster,
                    "size": len(cluster),
                    "avg_criticality": avg_criticality,
                    "risk_level": "critical" if avg_criticality > 0.7 else "high",
                })
        
        return sorted(clusters, key=lambda x: x["avg_criticality"], reverse=True)