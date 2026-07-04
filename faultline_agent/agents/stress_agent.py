"""
Stress Simulation Agent
Designs and applies stress scenarios to the system graph,
identifying optimal failure injection points.
"""

from __future__ import annotations
from typing import Any
from datetime import datetime
import numpy as np
from agents.base_agent import BaseAgent, AgentResult
from core.graph_builder import SystemGraph
from core.models import StressType, NodeStatus


class StressAgent(BaseAgent):
    """
    Designs intelligent stress tests based on graph structure
    and applies them to identify breaking points.
    """
    
    def __init__(self, graph: SystemGraph):
        super().__init__(
            name="StressAgent",
            description="Designs and applies stress scenarios to identify breaking points"
        )
        self.graph = graph
        self.rng = np.random.default_rng(42)
    
    def execute(self, context: dict[str, Any]) -> AgentResult:
        """
        Design and recommend stress scenarios.
        
        Expected context:
            - analysis: Graph analysis results from DependencyAgent
            - stress_mode: "auto" | "targeted" | "random" | "worst_case"
            - target_nodes: Optional list of specific nodes to stress
        """
        start_time = datetime.now()
        
        try:
            analysis = context.get("analysis", {})
            stress_mode = context.get("stress_mode", "auto")
            target_nodes = context.get("target_nodes", [])
            
            self.reason(f"Designing stress scenarios in '{stress_mode}' mode")
            
            if stress_mode == "auto":
                scenarios = self._design_auto_scenarios(analysis)
            elif stress_mode == "targeted":
                scenarios = self._design_targeted_scenarios(target_nodes)
            elif stress_mode == "random":
                scenarios = self._design_random_scenarios()
            elif stress_mode == "worst_case":
                scenarios = self._design_worst_case_scenarios(analysis)
            else:
                scenarios = self._design_auto_scenarios(analysis)
            
            self.reason(f"Designed {len(scenarios)} stress scenarios")
            
            # Rank scenarios by expected impact
            ranked = self._rank_scenarios(scenarios)
            
            result_data = {
                "scenarios": ranked,
                "total_scenarios": len(ranked),
                "stress_mode": stress_mode,
                "recommended_first": ranked[0] if ranked else None,
            }
            
            self.send_message(
                "PropagationAgent",
                result_data,
                msg_type="stress_designed"
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
    
    def _design_auto_scenarios(self, analysis: dict) -> list[dict[str, Any]]:
        """Automatically design scenarios based on graph analysis."""
        scenarios = []
        
        # Scenario 1: Attack single points of failure
        spofs = analysis.get("single_points_of_failure", [])
        for spof in spofs[:3]:
            node_id = spof["node_id"]
            node = self.graph.get_node(node_id)
            if node:
                scenarios.append({
                    "name": f"SPOF Attack: {node.name}",
                    "description": f"Stress test on single point of failure: {node.name}",
                    "stress_points": [{
                        "node_id": node_id,
                        "stress_type": "dependency_failure",
                        "intensity": 0.85,
                    }],
                    "category": "spof_attack",
                    "expected_impact": "high",
                })
        
        # Scenario 2: High fan-in node overload
        high_fan_in = analysis.get("high_fan_in_nodes", [])
        for hfi in high_fan_in[:2]:
            node_id = hfi["node_id"]
            node = self.graph.get_node(node_id)
            if node:
                scenarios.append({
                    "name": f"Overload: {node.name}",
                    "description": f"Load spike on high-dependency node: {node.name}",
                    "stress_points": [{
                        "node_id": node_id,
                        "stress_type": "load_spike",
                        "intensity": 0.9,
                    }],
                    "category": "overload",
                    "expected_impact": "high",
                })
        
        # Scenario 3: External dependency failure
        external_nodes = [
            nid for nid, n in self.graph.nodes.items()
            if n.node_type == "external"
        ]
        if external_nodes:
            scenarios.append({
                "name": "External Service Outage",
                "description": "Simulating external dependency becoming unavailable",
                "stress_points": [
                    {
                        "node_id": nid,
                        "stress_type": "external_outage",
                        "intensity": 0.95,
                    }
                    for nid in external_nodes[:2]
                ],
                "category": "external_failure",
                "expected_impact": "medium",
            })
        
        # Scenario 4: Cascading network partition
        gateway_nodes = [
            nid for nid, n in self.graph.nodes.items()
            if n.node_type in ("gateway", "load_balancer", "network")
        ]
        if gateway_nodes:
            scenarios.append({
                "name": "Network Partition",
                "description": "Network infrastructure failure causing partition",
                "stress_points": [
                    {
                        "node_id": nid,
                        "stress_type": "network_partition",
                        "intensity": 0.8,
                    }
                    for nid in gateway_nodes[:2]
                ],
                "category": "network_failure",
                "expected_impact": "critical",
            })
        
        # Scenario 5: Multi-point simultaneous failure
        criticality = analysis.get("criticality_scores", {})
        top_critical = sorted(criticality.items(), key=lambda x: x[1], reverse=True)[:3]
        if len(top_critical) >= 2:
            scenarios.append({
                "name": "Multi-Point Failure",
                "description": "Simultaneous failure of multiple critical nodes",
                "stress_points": [
                    {
                        "node_id": nid,
                        "stress_type": "cascading_failure",
                        "intensity": 0.75,
                    }
                    for nid, _ in top_critical[:3]
                ],
                "category": "multi_point",
                "expected_impact": "catastrophic",
            })
        
        return scenarios
    
    def _design_targeted_scenarios(self, target_nodes: list[str]) -> list[dict[str, Any]]:
        """Design scenarios targeting specific nodes."""
        scenarios = []
        
        stress_types = [
            StressType.LOAD_SPIKE,
            StressType.LATENCY,
            StressType.MEMORY_PRESSURE,
            StressType.NETWORK_PARTITION,
        ]
        
        for node_id in target_nodes:
            node = self.graph.get_node(node_id)
            if not node:
                continue
            
            for stress_type in stress_types:
                scenarios.append({
                    "name": f"{stress_type.value.replace('_', ' ').title()}: {node.name}",
                    "description": f"Targeted {stress_type.value} on {node.name}",
                    "stress_points": [{
                        "node_id": node_id,
                        "stress_type": stress_type.value,
                        "intensity": 0.8,
                    }],
                    "category": "targeted",
                    "expected_impact": "variable",
                })
        
        return scenarios
    
    def _design_random_scenarios(self, count: int = 5) -> list[dict[str, Any]]:
        """Design random stress scenarios for chaos testing."""
        scenarios = []
        all_nodes = list(self.graph.nodes.keys())
        
        if not all_nodes:
            return scenarios
        
        stress_types = list(StressType)
        
        for i in range(count):
            num_targets = self.rng.integers(1, min(4, len(all_nodes) + 1))
            targets = self.rng.choice(all_nodes, size=num_targets, replace=False)
            
            scenarios.append({
                "name": f"Chaos Test #{i+1}",
                "description": f"Random stress on {num_targets} node(s)",
                "stress_points": [
                    {
                        "node_id": str(nid),
                        "stress_type": self.rng.choice(stress_types).value,
                        "intensity": float(self.rng.uniform(0.5, 0.95)),
                    }
                    for nid in targets
                ],
                "category": "chaos",
                "expected_impact": "unknown",
            })
        
        return scenarios
    
    def _design_worst_case_scenarios(self, analysis: dict) -> list[dict[str, Any]]:
        """Design worst-case scenarios targeting maximum damage."""
        scenarios = []
        
        # Find the node whose failure causes maximum cascade
        max_blast = None
        max_blast_size = 0
        
        for node_id in self.graph.nodes:
            blast = self.graph.get_failure_blast_radius(node_id)
            if blast["total_affected"] > max_blast_size:
                max_blast_size = blast["total_affected"]
                max_blast = blast
        
        if max_blast:
            node = self.graph.get_node(max_blast["source"])
            scenarios.append({
                "name": f"Maximum Cascade: {node.name if node else max_blast['source']}",
                "description": f"Failure of node with largest blast radius ({max_blast_size} affected)",
                "stress_points": [{
                    "node_id": max_blast["source"],
                    "stress_type": "dependency_failure",
                    "intensity": 0.95,
                }],
                "category": "worst_case",
                "expected_impact": "catastrophic",
                "blast_radius": max_blast,
            })
        
        # Simultaneous failure of all tier-1 nodes
        tier1_nodes = [
            nid for nid, n in self.graph.nodes.items()
            if n.tier == 1
        ]
        if tier1_nodes:
            scenarios.append({
                "name": "Total Critical Infrastructure Failure",
                "description": "Simultaneous failure of all Tier-1 critical nodes",
                "stress_points": [
                    {
                        "node_id": nid,
                        "stress_type": "cascading_failure",
                        "intensity": 0.95,
                    }
                    for nid in tier1_nodes
                ],
                "category": "worst_case",
                "expected_impact": "catastrophic",
            })
        
        return scenarios
    
    def _rank_scenarios(self, scenarios: list[dict]) -> list[dict]:
        """Rank scenarios by expected impact and informativeness."""
        impact_order = {
            "catastrophic": 5,
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
            "variable": 2.5,
            "unknown": 2,
        }
        
        for scenario in scenarios:
            impact = scenario.get("expected_impact", "medium")
            num_points = len(scenario.get("stress_points", []))
            scenario["_rank_score"] = impact_order.get(impact, 2) + num_points * 0.5
        
        ranked = sorted(scenarios, key=lambda x: x.get("_rank_score", 0), reverse=True)
        
        # Clean up internal ranking field
        for s in ranked:
            s.pop("_rank_score", None)
        
        return ranked