"""
Propagation Tool
Provides failure propagation analysis capabilities for agents.
"""

from __future__ import annotations
from typing import Any
from core.graph_builder import SystemGraph
from core.failure_engine import FailureEngine
from core.models import StressType


class PropagationTool:
    """Tool for analyzing and executing failure propagation."""
    
    def __init__(self, graph: SystemGraph, engine: FailureEngine):
        self.graph = graph
        self.engine = engine
    
    def trace_cascade(self, node_id: str, max_depth: int = 5) -> dict[str, Any]:
        """Trace potential cascade path from a node without executing."""
        waves = self.graph.get_cascade_path(node_id, max_depth)
        
        all_affected = []
        for wave in waves:
            all_affected.extend(wave)
        
        return {
            "source": node_id,
            "waves": waves,
            "total_potentially_affected": len(all_affected),
            "max_depth": len(waves),
            "affected_details": [
                {
                    "node_id": nid,
                    "name": self.graph.nodes[nid].name if nid in self.graph.nodes else nid,
                    "tier": self.graph.nodes[nid].tier if nid in self.graph.nodes else 0,
                }
                for nid in all_affected
            ],
        }
    
    def simulate_propagation(
        self,
        node_id: str,
        stress_type: str = "load_spike",
        intensity: float = 0.8,
        max_depth: int = 5,
    ) -> dict[str, Any]:
        """Execute a full propagation simulation."""
        stress = StressType(stress_type)
        
        # Reset before simulation
        self.engine.reset_system()
        
        # Inject and propagate
        event = self.engine.inject_failure(node_id, stress, intensity)
        result = self.engine.propagate_failure(node_id, stress, max_depth=max_depth)
        
        return {
            "event": {
                "source": event.source_node_id,
                "type": event.stress_type.value,
                "severity": event.severity.value,
            },
            "result": {
                "total_affected": result.total_affected,
                "max_depth": result.max_depth,
                "cascade_path": result.cascade_path,
                "critical_nodes_hit": result.critical_nodes_hit,
                "severity": result.severity.value,
                "downtime_estimate": result.estimated_downtime_seconds,
                "revenue_impact": result.estimated_revenue_impact,
                "recommendations": result.recommendations,
                "timeline": result.timeline_events,
            },
        }
    
    def compare_scenarios(
        self, scenarios: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Compare multiple failure scenarios side by side."""
        results = []
        
        for scenario in scenarios:
            self.engine.reset_system()
            node_id = scenario["node_id"]
            stress_type = StressType(scenario.get("stress_type", "load_spike"))
            intensity = scenario.get("intensity", 0.8)
            
            self.engine.inject_failure(node_id, stress_type, intensity)
            result = self.engine.propagate_failure(node_id, stress_type)
            
            results.append({
                "scenario": scenario,
                "affected": result.total_affected,
                "depth": result.max_depth,
                "severity": result.severity.value,
                "critical_hits": len(result.critical_nodes_hit),
            })
        
        # Sort by impact
        results.sort(key=lambda x: x["affected"], reverse=True)
        
        return {
            "comparison": results,
            "worst_case": results[0] if results else None,
            "best_case": results[-1] if results else None,
        }
    
    def find_weakest_link(self) -> dict[str, Any]:
        """Find the node whose failure causes the most damage."""
        worst_node = None
        worst_affected = 0
        
        for node_id in self.graph.nodes:
            self.engine.reset_system()
            self.engine.inject_failure(node_id, StressType.DEPENDENCY_FAILURE, 0.9)
            result = self.engine.propagate_failure(node_id, StressType.DEPENDENCY_FAILURE)
            
            if result.total_affected > worst_affected:
                worst_affected = result.total_affected
                worst_node = node_id
        
        self.engine.reset_system()
        
        if worst_node:
            node = self.graph.get_node(worst_node)
            return {
                "weakest_node": worst_node,
                "name": node.name if node else worst_node,
                "max_cascade_size": worst_affected,
                "blast_radius": self.graph.get_failure_blast_radius(worst_node),
            }
        
        return {"weakest_node": None, "message": "No nodes in graph"}