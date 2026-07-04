"""
Faultline State Machine
Manages agent states, transitions, and the overall simulation lifecycle.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Callable, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from core.models import SimulationState, NodeStatus
import copy


class AgentPhase(str, Enum):
    """Phases of the multi-agent pipeline."""
    IDLE = "idle"
    INGESTION = "ingestion"
    GRAPH_BUILDING = "graph_building"
    STRESS_ANALYSIS = "stress_analysis"
    PROPAGATION = "propagation"
    INSIGHT_GENERATION = "insight_generation"
    REPORTING = "reporting"
    COMPLETE = "complete"
    ERROR = "error"


class SimulationMode(str, Enum):
    """Simulation execution modes."""
    REALTIME = "realtime"
    STEP_BY_STEP = "step_by_step"
    FAST_FORWARD = "fast_forward"
    REPLAY = "replay"


class StateTransition(BaseModel):
    """Records a state transition."""
    from_phase: AgentPhase
    to_phase: AgentPhase
    timestamp: datetime = Field(default_factory=datetime.now)
    trigger: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class FaultlineStateMachine:
    """
    Central state machine for the Faultline system.
    Manages simulation state, agent coordination, and phase transitions.
    """
    
    # Valid phase transitions
    VALID_TRANSITIONS = {
        AgentPhase.IDLE: [AgentPhase.INGESTION, AgentPhase.ERROR],
        AgentPhase.INGESTION: [AgentPhase.GRAPH_BUILDING, AgentPhase.ERROR],
        AgentPhase.GRAPH_BUILDING: [AgentPhase.STRESS_ANALYSIS, AgentPhase.ERROR],
        AgentPhase.STRESS_ANALYSIS: [AgentPhase.PROPAGATION, AgentPhase.ERROR],
        AgentPhase.PROPAGATION: [AgentPhase.INSIGHT_GENERATION, AgentPhase.STRESS_ANALYSIS, AgentPhase.ERROR],
        AgentPhase.INSIGHT_GENERATION: [AgentPhase.REPORTING, AgentPhase.STRESS_ANALYSIS, AgentPhase.ERROR],
        AgentPhase.REPORTING: [AgentPhase.COMPLETE, AgentPhase.STRESS_ANALYSIS, AgentPhase.ERROR],
        AgentPhase.COMPLETE: [AgentPhase.IDLE, AgentPhase.STRESS_ANALYSIS],
        AgentPhase.ERROR: [AgentPhase.IDLE],
    }
    
    def __init__(self):
        self.current_phase: AgentPhase = AgentPhase.IDLE
        self.simulation_state: SimulationState = SimulationState()
        self.mode: SimulationMode = SimulationMode.REALTIME
        self.history: list[StateTransition] = []
        self.node_states: dict[str, NodeStatus] = {}
        self.node_health: dict[str, float] = {}
        self.snapshots: list[dict[str, Any]] = []
        self._listeners: list[Callable] = []
        self._context: dict[str, Any] = {}
    
    @property
    def context(self) -> dict[str, Any]:
        """Get the current context dictionary."""
        return self._context
    
    def set_context(self, key: str, value: Any) -> None:
        """Set a value in the context."""
        self._context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a value from the context."""
        return self._context.get(key, default)
    
    def transition_to(self, new_phase: AgentPhase, trigger: str = "") -> bool:
        """
        Attempt to transition to a new phase.
        Returns True if transition was valid and executed.
        """
        if new_phase not in self.VALID_TRANSITIONS.get(self.current_phase, []):
            return False
        
        transition = StateTransition(
            from_phase=self.current_phase,
            to_phase=new_phase,
            trigger=trigger,
        )
        self.history.append(transition)
        self.current_phase = new_phase
        
        # Notify listeners
        for listener in self._listeners:
            listener(transition)
        
        return True
    
    def add_listener(self, callback: Callable) -> None:
        """Add a state transition listener."""
        self._listeners.append(callback)
    
    def update_node_status(self, node_id: str, status: NodeStatus, health: float) -> None:
        """Update the status and health of a node."""
        self.node_states[node_id] = status
        self.node_health[node_id] = max(0.0, min(1.0, health))
        
        # Update overall system health
        if self.node_health:
            self.simulation_state.system_health_score = (
                sum(self.node_health.values()) / len(self.node_health)
            )
    
    def take_snapshot(self) -> dict[str, Any]:
        """Take a snapshot of the current state for replay/timeline."""
        snapshot = {
            "step": self.simulation_state.step,
            "timestamp": datetime.now().isoformat(),
            "phase": self.current_phase.value,
            "node_states": dict(self.node_states),
            "node_health": dict(self.node_health),
            "system_health": self.simulation_state.system_health_score,
            "active_failures": len(self.simulation_state.active_failures),
            "cascade_depth": self.simulation_state.cascade_depth,
        }
        self.snapshots.append(snapshot)
        return snapshot
    
    def advance_step(self) -> None:
        """Advance the simulation by one step."""
        self.simulation_state.step += 1
        self.simulation_state.elapsed_time_seconds += (
            1.0 / self.simulation_state.speed_multiplier
        )
    
    def reset(self) -> None:
        """Reset the state machine to initial state."""
        self.current_phase = AgentPhase.IDLE
        self.simulation_state = SimulationState()
        self.node_states.clear()
        self.node_health.clear()
        self.snapshots.clear()
        self._context.clear()
        # Keep history for audit trail
    
    def get_affected_count(self) -> int:
        """Get count of nodes not in healthy state."""
        return sum(
            1 for status in self.node_states.values()
            if status != NodeStatus.HEALTHY
        )
    
    def get_critical_failures(self) -> list[str]:
        """Get list of node IDs in DEAD or FAILING state."""
        return [
            node_id for node_id, status in self.node_states.items()
            if status in (NodeStatus.DEAD, NodeStatus.FAILING)
        ]
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize state machine to dictionary."""
        return {
            "phase": self.current_phase.value,
            "mode": self.mode.value,
            "simulation": self.simulation_state.model_dump(),
            "node_states": {k: v.value for k, v in self.node_states.items()},
            "node_health": dict(self.node_health),
            "history_length": len(self.history),
            "snapshots_count": len(self.snapshots),
        }