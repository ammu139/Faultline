"""
Faultline Simulator
Orchestrates the simulation lifecycle, combining graph, failure engine,
and state machine into a cohesive simulation runtime.
"""

from __future__ import annotations
from typing import Any, Optional, Generator
from datetime import datetime
from core.models import (
    SimulationState, NodeStatus, StressType, PropagationResult,
    FailureEvent, ScenarioConfig
)
from core.graph_builder import SystemGraph
from core.failure_engine import FailureEngine
from core.state_machine import FaultlineStateMachine, AgentPhase, SimulationMode


class SimulationTimeline:
    """Records and replays simulation events over time."""
    
    def __init__(self):
        self.events: list[dict[str, Any]] = []
        self.snapshots: list[dict[str, Any]] = []
    
    def record_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Record a simulation event."""
        self.events.append({
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data,
        })
    
    def record_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Record a state snapshot."""
        self.snapshots.append(snapshot)
    
    def get_events_in_range(self, start_step: int, end_step: int) -> list[dict]:
        """Get events within a step range."""
        return [
            e for e in self.events
            if start_step <= e.get("data", {}).get("step", 0) <= end_step
        ]
    
    def clear(self) -> None:
        """Clear all recorded data."""
        self.events.clear()
        self.snapshots.clear()


class FaultlineSimulator:
    """
    Main simulation orchestrator.
    Manages the complete lifecycle of a failure simulation.
    """
    
    def __init__(self):
        self.graph = SystemGraph()
        self.engine: Optional[FailureEngine] = None
        self.state_machine = FaultlineStateMachine()
        self.timeline = SimulationTimeline()
        self._scenario: Optional[ScenarioConfig] = None
        self._is_initialized = False
    
    def initialize(self, scenario: ScenarioConfig) -> None:
        """Initialize the simulator with a scenario."""
        self._scenario = scenario
        
        # Build the graph
        self.graph.build_from_scenario(scenario)
        
        # Initialize failure engine
        self.engine = FailureEngine(self.graph)
        
        # Reset state machine
        self.state_machine.reset()
        self.state_machine.simulation_state.scenario_name = scenario.name
        self.state_machine.simulation_state.total_steps = int(
            scenario.simulation_duration_seconds
        )
        
        # Initialize node states
        for node_id, node in self.graph.nodes.items():
            self.state_machine.update_node_status(
                node_id, node.status, node.health_score
            )
        
        # Clear timeline
        self.timeline.clear()
        self._is_initialized = True
    
    def start(self) -> None:
        """Start the simulation."""
        if not self._is_initialized:
            raise RuntimeError("Simulator not initialized. Call initialize() first.")
        
        self.state_machine.simulation_state.is_running = True
        self.state_machine.transition_to(AgentPhase.INGESTION, "simulation_start")
        
        self.timeline.record_event("simulation_start", {
            "scenario": self._scenario.name if self._scenario else "unknown",
            "nodes": len(self.graph.nodes),
            "edges": len(self.graph.edges),
        })
    
    def stop(self) -> None:
        """Stop the simulation."""
        self.state_machine.simulation_state.is_running = False
        self.state_machine.simulation_state.is_paused = False
    
    def pause(self) -> None:
        """Pause the simulation."""
        self.state_machine.simulation_state.is_paused = True
    
    def resume(self) -> None:
        """Resume the simulation."""
        self.state_machine.simulation_state.is_paused = False
    
    def step(self) -> dict[str, Any]:
        """
        Execute one simulation step.
        Returns the step result with current state.
        """
        if not self.engine:
            return {"error": "Simulator not initialized"}
        
        state = self.state_machine.simulation_state
        
        # Advance the simulation
        self.engine.simulate_step(state)
        
        # Update state machine with current node states
        for node_id, node in self.graph.nodes.items():
            self.state_machine.update_node_status(
                node_id, node.status, node.health_score
            )
        
        # Take snapshot
        snapshot = self.state_machine.take_snapshot()
        self.timeline.record_snapshot(snapshot)
        
        # Build step result
        step_result = {
            "step": state.step,
            "system_health": state.system_health_score,
            "nodes_affected": state.total_nodes_affected,
            "cascade_depth": state.cascade_depth,
            "node_states": {
                nid: {
                    "name": node.name,
                    "status": node.status.value if hasattr(node.status, 'value') else node.status,
                    "health": node.health_score,
                    "load": node.current_load,
                }
                for nid, node in self.graph.nodes.items()
            },
        }
        
        self.timeline.record_event("step", step_result)
        return step_result
    
    def inject_failure(
        self,
        node_id: str,
        stress_type: str,
        intensity: float = 0.8,
    ) -> dict[str, Any]:
        """Inject a failure and propagate it."""
        if not self.engine:
            return {"error": "Simulator not initialized"}
        
        stress = StressType(stress_type)
        
        # Inject
        event = self.engine.inject_failure(node_id, stress, intensity)
        
        # Propagate
        result = self.engine.propagate_failure(node_id, stress)
        
        # Update state machine
        for nid, node in self.graph.nodes.items():
            self.state_machine.update_node_status(
                nid, node.status, node.health_score
            )
        
        self.state_machine.simulation_state.cascade_depth = max(
            self.state_machine.simulation_state.cascade_depth,
            result.max_depth,
        )
        
        # Record event
        self.timeline.record_event("failure_injection", {
            "node_id": node_id,
            "stress_type": stress_type,
            "intensity": intensity,
            "affected": result.total_affected,
            "severity": result.severity.value if hasattr(result.severity, 'value') else result.severity,
        })
        
        return {
            "event": {
                "source": event.source_node_id,
                "type": event.stress_type.value if hasattr(event.stress_type, 'value') else event.stress_type,
                "severity": event.severity.value if hasattr(event.severity, 'value') else event.severity,
                "description": event.description,
            },
            "propagation": {
                "total_affected": result.total_affected,
                "max_depth": result.max_depth,
                "critical_nodes_hit": result.critical_nodes_hit,
                "severity": result.severity.value if hasattr(result.severity, 'value') else result.severity,
                "estimated_downtime": result.estimated_downtime_seconds,
                "recommendations": result.recommendations,
                "timeline": result.timeline_events,
            },
        }
    
    def run_scenario_failures(self) -> list[dict[str, Any]]:
        """Run all initial failures defined in the scenario."""
        if not self._scenario or not self.engine:
            return []
        
        results = []
        for failure_config in self._scenario.initial_failures:
            result = self.inject_failure(
                node_id=failure_config["node_id"],
                stress_type=failure_config.get("stress_type", "load_spike"),
                intensity=failure_config.get("intensity", 0.7),
            )
            results.append(result)
        
        return results
    
    def get_system_status(self) -> dict[str, Any]:
        """Get comprehensive system status."""
        if not self.graph.nodes:
            return {"status": "not_initialized"}
        
        status_counts = {}
        for node in self.graph.nodes.values():
            status = node.status.value if hasattr(node.status, 'value') else node.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "system_health": self.state_machine.simulation_state.system_health_score,
            "total_nodes": len(self.graph.nodes),
            "status_distribution": status_counts,
            "critical_failures": self.state_machine.get_critical_failures(),
            "affected_count": self.state_machine.get_affected_count(),
            "simulation_step": self.state_machine.simulation_state.step,
            "is_running": self.state_machine.simulation_state.is_running,
            "graph_metrics": self.graph.get_graph_metrics(),
        }
    
    def get_fragility_analysis(self) -> dict[str, Any]:
        """Run fragility analysis on the current graph."""
        criticality = self.graph.calculate_node_criticality()
        spofs = self.graph.find_single_points_of_failure()
        critical_paths = self.graph.find_critical_paths()
        
        # Find top fragile nodes
        sorted_criticality = sorted(
            criticality.items(), key=lambda x: x[1], reverse=True
        )
        top_fragile = [
            {
                "node_id": nid,
                "name": self.graph.nodes[nid].name if nid in self.graph.nodes else nid,
                "criticality_score": score,
                "blast_radius": self.graph.get_failure_blast_radius(nid),
            }
            for nid, score in sorted_criticality[:5]
        ]
        
        return {
            "single_points_of_failure": [
                {
                    "node_id": nid,
                    "name": self.graph.nodes[nid].name if nid in self.graph.nodes else nid,
                }
                for nid in spofs
            ],
            "top_fragile_nodes": top_fragile,
            "critical_paths": critical_paths[:5],
            "criticality_scores": criticality,
        }
    
    def reset(self) -> None:
        """Reset the entire simulation."""
        if self.engine:
            self.engine.reset_system()
        self.state_machine.reset()
        self.timeline.clear()
        self._is_initialized = False