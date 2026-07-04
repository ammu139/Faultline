"""
Failure Propagation Agent
Executes failure propagation simulations and traces cascade paths
through the dependency graph.
"""

from __future__ import annotations
from typing import Any
from datetime import datetime
from agents.base_agent import BaseAgent, AgentResult
from core.graph_builder import SystemGraph
from core.failure_engine import FailureEngine
from core.models import StressType, PropagationResult


class PropagationAgent(BaseAgent):
    """
    Executes failure propagation and traces cascading impacts
    across the system dependency graph.
    """
    
    def __init__(self, graph: SystemGraph, engine: FailureEngine):
        super().__init__(
            name="PropagationAgent",
            description="Traces failure cascades and maps impact propagation"
        )
        self.graph = graph
        self.engine = engine
    
    def execute(self, context: dict[str, Any]) -> AgentResult:
        """
        Execute failure propagation for given stress scenarios.
        
        Expected context:
            - scenarios: List of stress scenarios to execute
            - propagation_depth: Max cascade depth (default: 5)
            - decay_factor: Signal decay per hop (default: 0.7)
        """
        start_time = datetime.now()
        
        try:
            scenarios = context.get("scenarios", [])
            max_depth = context.get("propagation_depth", 5)
            decay_factor = context.get("decay_factor", 0.7)
            
            if not scenarios:
                return self._build_result(
                    success=False,
                    error="No scenarios provided for propagation",
                    start_time=start_time,
                )
            
            self.reason(f"Executing propagation for {len(scenarios)} scenarios")
            
            all_results = []
            
            for scenario in scenarios:
                self.reason(f"Processing scenario: {scenario.get('name', 'unnamed')}")
                
                # Reset system before each scenario
                self.engine.reset_system()
                
                # Execute stress points
                stress_points = scenario.get("stress_points", [])
                scenario_results = []
                
                for point in stress_points:
                    node_id = point["node_id"]
                    stress_type = StressType(point.get("stress_type", "load_spike"))
                    intensity = point.get("intensity", 0.8)
                    
                    # Inject failure
                    self.engine.inject_failure(node_id, stress_type, intensity)
                    
                    # Propagate
                    result = self.engine.propagate_failure(
                        node_id, stress_type,
                        max_depth=max_depth,
                        decay_factor=decay_factor,
                    )
                    scenario_results.append(result)
                
                # Aggregate scenario results
                aggregated = self._aggregate_results(scenario, scenario_results)
                all_results.append(aggregated)
            
            # Generate summary
            summary = self._generate_summary(all_results)
            
            result_data = {
                "propagation_results": all_results,
                "summary": summary,
                "total_scenarios_executed": len(all_results),
            }
            
            self.send_message(
                "InsightAgent",
                result_data,
                msg_type="propagation_complete"
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
    
    def execute_single(
        self,
        node_id: str,
        stress_type: str,
        intensity: float = 0.8,
        max_depth: int = 5,
    ) -> dict[str, Any]:
        """Execute a single propagation for interactive use."""
        self.engine.reset_system()
        
        stress = StressType(stress_type)
        event = self.engine.inject_failure(node_id, stress, intensity)
        result = self.engine.propagate_failure(node_id, stress, max_depth=max_depth)
        
        return {
            "event": {
                "source": event.source_node_id,
                "type": event.stress_type,
                "severity": event.severity,
                "description": event.description,
            },
            "propagation": {
                "total_affected": result.total_affected,
                "max_depth": result.max_depth,
                "cascade_path": result.cascade_path,
                "critical_nodes_hit": result.critical_nodes_hit,
                "severity": result.severity,
                "estimated_downtime": result.estimated_downtime_seconds,
                "estimated_revenue_impact": result.estimated_revenue_impact,
                "recommendations": result.recommendations,
                "timeline": result.timeline_events,
            },
            "node_states": {
                nid: {
                    "name": node.name,
                    "status": node.status,
                    "health": node.health_score,
                }
                for nid, node in self.graph.nodes.items()
            },
        }
    
    def _aggregate_results(
        self, scenario: dict, results: list[PropagationResult]
    ) -> dict[str, Any]:
        """Aggregate multiple propagation results for a scenario."""
        total_affected = set()
        max_depth = 0
        all_critical = []
        total_downtime = 0.0
        all_timeline = []
        all_recommendations = set()
        
        for result in results:
            for node_id in (result.cascade_path or []):
                if isinstance(node_id, list):
                    total_affected.update(node_id)
                else:
                    total_affected.add(node_id)
            
            max_depth = max(max_depth, result.max_depth)
            all_critical.extend(result.critical_nodes_hit)
            total_downtime += result.estimated_downtime_seconds
            all_timeline.extend(result.timeline_events)
            all_recommendations.update(result.recommendations)
        
        # Determine worst severity
        from core.models import ImpactSeverity
        severity_order = [
            ImpactSeverity.NEGLIGIBLE, ImpactSeverity.LOW,
            ImpactSeverity.MEDIUM, ImpactSeverity.HIGH,
            ImpactSeverity.CRITICAL, ImpactSeverity.CATASTROPHIC,
        ]
        worst_severity = ImpactSeverity.NEGLIGIBLE
        for result in results:
            result_sev = result.severity if isinstance(result.severity, str) else result.severity.value
            worst_sev = worst_severity if isinstance(worst_severity, str) else worst_severity.value
            sev_values = ["negligible", "low", "medium", "high", "critical", "catastrophic"]
            if sev_values.index(result_sev) > sev_values.index(worst_sev):
                worst_severity = result_sev
        
        return {
            "scenario_name": scenario.get("name", "unnamed"),
            "scenario_category": scenario.get("category", "unknown"),
            "total_affected": len(total_affected),
            "affected_nodes": list(total_affected),
            "max_cascade_depth": max_depth,
            "critical_nodes_hit": list(set(all_critical)),
            "worst_severity": worst_severity if isinstance(worst_severity, str) else worst_severity.value,
            "estimated_downtime_seconds": total_downtime,
            "timeline": sorted(all_timeline, key=lambda x: x.get("time", 0)),
            "recommendations": list(all_recommendations),
            "stress_points_count": len(scenario.get("stress_points", [])),
        }
    
    def _generate_summary(self, all_results: list[dict]) -> dict[str, Any]:
        """Generate an overall summary of all propagation results."""
        if not all_results:
            return {"status": "no_results"}
        
        # Find worst scenario
        worst = max(all_results, key=lambda x: x.get("total_affected", 0))
        
        # Calculate averages
        avg_affected = sum(r["total_affected"] for r in all_results) / len(all_results)
        avg_depth = sum(r["max_cascade_depth"] for r in all_results) / len(all_results)
        
        # Count severity distribution
        severity_dist = {}
        for r in all_results:
            sev = r.get("worst_severity", "unknown")
            severity_dist[sev] = severity_dist.get(sev, 0) + 1
        
        # Collect all unique recommendations
        all_recs = set()
        for r in all_results:
            all_recs.update(r.get("recommendations", []))
        
        return {
            "total_scenarios": len(all_results),
            "worst_scenario": worst["scenario_name"],
            "worst_affected_count": worst["total_affected"],
            "average_affected": avg_affected,
            "average_cascade_depth": avg_depth,
            "severity_distribution": severity_dist,
            "top_recommendations": list(all_recs)[:5],
            "system_resilience_score": max(0, 1.0 - (avg_affected / max(len(self.graph.nodes), 1))),
        }