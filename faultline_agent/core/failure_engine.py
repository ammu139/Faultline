"""
Faultline Failure Engine
Simulates failure propagation with probabilistic cascading,
time-based decay, and external factor modeling.
"""

from __future__ import annotations
from typing import Any, Optional
import numpy as np
from datetime import datetime
from core.models import (
    SystemNode, NodeStatus, StressType, ImpactSeverity,
    FailureEvent, PropagationResult, SimulationState
)
from core.graph_builder import SystemGraph


class FailureEngine:
    """
    Engine for simulating failure propagation through the dependency graph.
    Models cascading failures with probabilistic propagation,
    load redistribution, and recovery dynamics.
    """
    
    def __init__(self, graph: SystemGraph, seed: int = 42):
        self.graph = graph
        self.rng = np.random.default_rng(seed)
        self.failure_log: list[FailureEvent] = []
        self.propagation_history: list[PropagationResult] = []
        self._time_elapsed: float = 0.0
    
    def inject_failure(
        self,
        node_id: str,
        stress_type: StressType,
        intensity: float = 0.8,
        is_external: bool = False,
    ) -> FailureEvent:
        """
        Inject a failure into a specific node.
        Returns the failure event created.
        """
        node = self.graph.get_node(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found in graph")
        
        # Calculate damage based on intensity and node resilience
        damage = intensity * (1.0 - node.resilience * 0.5)
        new_health = max(0.0, node.health_score - damage)
        
        # Update node state
        node.health_score = new_health
        node.status = self._health_to_status(new_health)
        node.current_load = min(node.load_capacity * 1.5, node.current_load + intensity * 0.5)
        
        # Create failure event
        event = FailureEvent(
            source_node_id=node_id,
            stress_type=stress_type,
            severity=self._calculate_severity(damage, node),
            root_cause=f"{stress_type.value} on {node.name}",
            description=self._generate_failure_description(node, stress_type, intensity),
            is_external=is_external,
            time_to_detect_seconds=self._estimate_detection_time(node),
        )
        
        self.failure_log.append(event)
        return event
    
    def propagate_failure(
        self,
        source_node_id: str,
        stress_type: StressType,
        max_depth: int = 5,
        decay_factor: float = 0.7,
    ) -> PropagationResult:
        """
        Simulate failure propagation from a source node through the graph.
        Uses probabilistic cascading with decay.
        """
        result = PropagationResult(
            origin_node=source_node_id,
            stress_type=stress_type,
        )
        
        source_node = self.graph.get_node(source_node_id)
        if not source_node:
            return result
        
        visited = {source_node_id}
        current_wave = [source_node_id]
        current_intensity = 1.0
        timeline_time = 0.0
        
        for depth in range(max_depth):
            next_wave = []
            current_intensity *= decay_factor
            
            if current_intensity < 0.1:
                break
            
            for node_id in current_wave:
                # Get nodes that depend on the failing node
                dependents = self.graph.get_dependents(node_id)
                
                for dep_id in dependents:
                    if dep_id in visited:
                        continue
                    
                    dep_node = self.graph.get_node(dep_id)
                    if not dep_node:
                        continue
                    
                    # Calculate propagation probability
                    prop_probability = self._calculate_propagation_probability(
                        node_id, dep_id, current_intensity
                    )
                    
                    # Probabilistic propagation
                    if self.rng.random() < prop_probability:
                        visited.add(dep_id)
                        next_wave.append(dep_id)
                        
                        # Apply damage to dependent node
                        damage = current_intensity * (1.0 - dep_node.resilience * 0.3)
                        dep_node.health_score = max(0.0, dep_node.health_score - damage * 0.6)
                        dep_node.status = self._health_to_status(dep_node.health_score)
                        dep_node.current_load = min(
                            dep_node.load_capacity * 1.5,
                            dep_node.current_load + current_intensity * 0.3
                        )
                        
                        # Record timeline event
                        timeline_time += self._estimate_propagation_delay(node_id, dep_id)
                        result.timeline_events.append({
                            "time": timeline_time,
                            "node": dep_id,
                            "node_name": dep_node.name,
                            "health": dep_node.health_score,
                            "status": dep_node.status.value if hasattr(dep_node.status, 'value') else dep_node.status,
                            "depth": depth + 1,
                            "intensity": current_intensity,
                        })
                        
                        # Check if critical node hit
                        if dep_node.tier == 1:
                            result.critical_nodes_hit.append(dep_id)
            
            if next_wave:
                result.cascade_path.append(next_wave)
                current_wave = next_wave
            else:
                break
        
        # Calculate final metrics
        all_affected = list(visited - {source_node_id})
        result.total_affected = len(all_affected)
        result.max_depth = len(result.cascade_path)
        result.affected_nodes = all_affected
        result.severity = self._assess_overall_severity(result)
        result.estimated_downtime_seconds = self._estimate_downtime(result)
        result.estimated_revenue_impact = self._estimate_revenue_impact(result)
        result.recommendations = self._generate_recommendations(result)
        
        self.propagation_history.append(result)
        return result
    
    def simulate_step(self, state: SimulationState) -> SimulationState:
        """
        Advance the simulation by one time step.
        Handles recovery, load redistribution, and random external events.
        """
        self._time_elapsed += 1.0
        
        # Process recovery for damaged nodes
        for node_id, node in self.graph.nodes.items():
            if node.status in (NodeStatus.STRESSED, NodeStatus.DEGRADED):
                # Gradual recovery
                recovery = node.resilience * 0.05
                node.health_score = min(1.0, node.health_score + recovery)
                node.current_load = max(0.1, node.current_load - 0.02)
                node.status = self._health_to_status(node.health_score)
            
            elif node.status == NodeStatus.RECOVERING:
                recovery = node.resilience * 0.1
                node.health_score = min(1.0, node.health_score + recovery)
                if node.health_score > 0.8:
                    node.status = NodeStatus.HEALTHY
                    node.current_load = 0.3
        
        # Random external events (low probability)
        if self.rng.random() < 0.02:
            external_nodes = [
                nid for nid, n in self.graph.nodes.items()
                if n.node_type == "external"
            ]
            if external_nodes:
                target = self.rng.choice(external_nodes)
                self.inject_failure(
                    target,
                    StressType.EXTERNAL_OUTAGE,
                    intensity=self.rng.uniform(0.3, 0.7),
                    is_external=True,
                )
        
        # Update simulation state
        state.step += 1
        state.elapsed_time_seconds = self._time_elapsed
        state.total_nodes_affected = sum(
            1 for n in self.graph.nodes.values()
            if n.status != NodeStatus.HEALTHY
        )
        state.system_health_score = self._calculate_system_health()
        
        return state
    
    def apply_stress_scenario(
        self,
        stress_points: list[dict[str, Any]],
    ) -> list[PropagationResult]:
        """
        Apply a multi-point stress scenario.
        Each stress point defines a node, type, and intensity.
        """
        results = []
        for point in stress_points:
            node_id = point["node_id"]
            stress_type = StressType(point.get("stress_type", "load_spike"))
            intensity = point.get("intensity", 0.7)
            
            # Inject the failure
            self.inject_failure(node_id, stress_type, intensity)
            
            # Propagate
            result = self.propagate_failure(
                node_id, stress_type,
                max_depth=point.get("max_depth", 5),
            )
            results.append(result)
        
        return results
    
    def reset_system(self) -> None:
        """Reset all nodes to healthy state."""
        for node in self.graph.nodes.values():
            node.health_score = 1.0
            node.status = NodeStatus.HEALTHY
            node.current_load = 0.3
        self._time_elapsed = 0.0
    
    def _calculate_propagation_probability(
        self, source_id: str, target_id: str, intensity: float
    ) -> float:
        """Calculate probability of failure propagating between two nodes."""
        # Get edge data
        edge_data = self.graph.graph.get_edge_data(target_id, source_id)
        if not edge_data:
            edge_data = self.graph.graph.get_edge_data(source_id, target_id)
        
        base_prob = 0.5
        if edge_data:
            weight = edge_data.get("weight", 0.5)
            is_critical = edge_data.get("is_critical", False)
            base_prob = weight * (1.5 if is_critical else 1.0)
        
        # Factor in target node resilience
        target_node = self.graph.get_node(target_id)
        if target_node:
            resilience_factor = 1.0 - target_node.resilience * 0.5
            base_prob *= resilience_factor
        
        return min(0.95, base_prob * intensity)
    
    def _estimate_propagation_delay(self, source_id: str, target_id: str) -> float:
        """Estimate time delay for failure to propagate between nodes."""
        edge_data = self.graph.graph.get_edge_data(target_id, source_id)
        if not edge_data:
            edge_data = self.graph.graph.get_edge_data(source_id, target_id) or {}
        
        latency = edge_data.get("latency_ms", 100) / 1000.0
        return latency + self.rng.uniform(0.5, 3.0)
    
    def _health_to_status(self, health: float) -> NodeStatus:
        """Convert health score to status enum."""
        if health > 0.8:
            return NodeStatus.HEALTHY
        elif health > 0.6:
            return NodeStatus.STRESSED
        elif health > 0.4:
            return NodeStatus.DEGRADED
        elif health > 0.1:
            return NodeStatus.FAILING
        else:
            return NodeStatus.DEAD
    
    def _calculate_severity(self, damage: float, node: SystemNode) -> ImpactSeverity:
        """Calculate impact severity based on damage and node importance."""
        impact = damage * node.business_value * (5 - node.tier) / 4
        
        if impact > 0.8:
            return ImpactSeverity.CATASTROPHIC
        elif impact > 0.6:
            return ImpactSeverity.CRITICAL
        elif impact > 0.4:
            return ImpactSeverity.HIGH
        elif impact > 0.2:
            return ImpactSeverity.MEDIUM
        elif impact > 0.1:
            return ImpactSeverity.LOW
        else:
            return ImpactSeverity.NEGLIGIBLE
    
    def _assess_overall_severity(self, result: PropagationResult) -> ImpactSeverity:
        """Assess overall severity of a propagation result."""
        if len(result.critical_nodes_hit) > 2:
            return ImpactSeverity.CATASTROPHIC
        elif len(result.critical_nodes_hit) > 0:
            return ImpactSeverity.CRITICAL
        elif result.total_affected > 10:
            return ImpactSeverity.HIGH
        elif result.total_affected > 5:
            return ImpactSeverity.MEDIUM
        elif result.total_affected > 2:
            return ImpactSeverity.LOW
        else:
            return ImpactSeverity.NEGLIGIBLE
    
    def _estimate_downtime(self, result: PropagationResult) -> float:
        """Estimate total downtime in seconds."""
        total = 0.0
        for node_id in result.critical_nodes_hit:
            node = self.graph.get_node(node_id)
            if node:
                total += node.recovery_time_seconds
        
        # Add cascade delay
        total += result.max_depth * 30.0
        return total
    
    def _estimate_revenue_impact(self, result: PropagationResult) -> float:
        """Estimate revenue impact (normalized 0-1 scale)."""
        total_value = sum(
            self.graph.nodes[nid].business_value
            for nid in (result.critical_nodes_hit or [])
            if nid in self.graph.nodes
        )
        return min(1.0, total_value / max(len(self.graph.nodes), 1))
    
    def _estimate_detection_time(self, node: SystemNode) -> float:
        """Estimate time to detect failure based on node type and tier."""
        base_time = {1: 5.0, 2: 30.0, 3: 120.0, 4: 300.0}
        return base_time.get(node.tier, 60.0) * self.rng.uniform(0.5, 1.5)
    
    def _calculate_system_health(self) -> float:
        """Calculate overall system health score."""
        if not self.graph.nodes:
            return 1.0
        
        weighted_health = sum(
            node.health_score * node.business_value
            for node in self.graph.nodes.values()
        )
        total_weight = sum(
            node.business_value for node in self.graph.nodes.values()
        )
        
        return weighted_health / max(total_weight, 0.01)
    
    def _generate_failure_description(
        self, node: SystemNode, stress_type: StressType, intensity: float
    ) -> str:
        """Generate a human-readable failure description."""
        descriptions = {
            StressType.LOAD_SPIKE: f"Traffic spike overwhelmed {node.name} ({intensity*100:.0f}% over capacity)",
            StressType.LATENCY: f"Response latency on {node.name} exceeded SLA thresholds",
            StressType.MEMORY_PRESSURE: f"Memory exhaustion on {node.name} triggered OOM conditions",
            StressType.DISK_FULL: f"Disk space exhausted on {node.name}, writes failing",
            StressType.NETWORK_PARTITION: f"Network partition isolated {node.name} from cluster",
            StressType.DEPENDENCY_FAILURE: f"Upstream dependency failure cascaded to {node.name}",
            StressType.DATA_CORRUPTION: f"Data integrity violation detected in {node.name}",
            StressType.SECURITY_BREACH: f"Security incident compromised {node.name}",
            StressType.EXTERNAL_OUTAGE: f"External service outage affecting {node.name}",
            StressType.NATURAL_DISASTER: f"Infrastructure damage from external event impacting {node.name}",
            StressType.HUMAN_ERROR: f"Configuration error introduced instability in {node.name}",
            StressType.CASCADING_FAILURE: f"Cascading failure reached {node.name} from upstream",
        }
        return descriptions.get(stress_type, f"Unknown failure on {node.name}")
    
    def _generate_recommendations(self, result: PropagationResult) -> list[str]:
        """Generate actionable recommendations based on propagation results."""
        recommendations = []
        
        if result.max_depth > 3:
            recommendations.append(
                "Implement circuit breakers to limit cascade depth"
            )
        
        if len(result.critical_nodes_hit) > 0:
            recommendations.append(
                "Add redundancy for critical-tier nodes in the blast radius"
            )
        
        if result.total_affected > 5:
            recommendations.append(
                "Consider bulkhead isolation to contain failure domains"
            )
        
        if result.estimated_downtime_seconds > 300:
            recommendations.append(
                "Implement automated failover to reduce recovery time"
            )
        
        source_node = self.graph.get_node(result.origin_node)
        if source_node and source_node.resilience < 0.5:
            recommendations.append(
                f"Increase resilience of {source_node.name} (current: {source_node.resilience:.0%})"
            )
        
        if not recommendations:
            recommendations.append("System shows acceptable resilience for this failure mode")
        
        return recommendations