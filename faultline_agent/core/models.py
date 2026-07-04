"""
Faultline Data Models
Pydantic models for system components, graph nodes, edges, and simulation state.
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class NodeStatus(str, Enum):
    """Health status of a system node."""
    HEALTHY = "healthy"
    STRESSED = "stressed"
    DEGRADED = "degraded"
    FAILING = "failing"
    DEAD = "dead"
    RECOVERING = "recovering"
    UNKNOWN = "unknown"


class StressType(str, Enum):
    """Types of stress that can be applied."""
    LOAD_SPIKE = "load_spike"
    LATENCY = "latency"
    MEMORY_PRESSURE = "memory_pressure"
    DISK_FULL = "disk_full"
    NETWORK_PARTITION = "network_partition"
    DEPENDENCY_FAILURE = "dependency_failure"
    DATA_CORRUPTION = "data_corruption"
    SECURITY_BREACH = "security_breach"
    EXTERNAL_OUTAGE = "external_outage"
    NATURAL_DISASTER = "natural_disaster"
    HUMAN_ERROR = "human_error"
    CASCADING_FAILURE = "cascading_failure"


class ImpactSeverity(str, Enum):
    """Severity levels for business impact."""
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    CATASTROPHIC = "catastrophic"


class SystemNode(BaseModel):
    """Represents a component in the system dependency graph."""
    model_config = {"use_enum_values": True}
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    node_type: str
    description: str = ""
    status: str = "healthy"
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)
    resilience: float = Field(default=0.7, ge=0.0, le=1.0)
    load_capacity: float = Field(default=1.0, ge=0.0)
    current_load: float = Field(default=0.3, ge=0.0)
    recovery_time_seconds: float = 30.0
    sla_target: float = 0.999
    business_value: float = Field(default=0.5, ge=0.0, le=1.0)
    tier: int = Field(default=2, ge=1, le=4)  # 1=critical, 4=low priority
    metadata: dict[str, Any] = Field(default_factory=dict)
    failure_history: list[dict[str, Any]] = Field(default_factory=list)
    
    @property
    def is_overloaded(self) -> bool:
        return self.current_load > self.load_capacity * 0.9
    
    @property
    def stress_level(self) -> float:
        return min(1.0, self.current_load / max(self.load_capacity, 0.01))


class SystemEdge(BaseModel):
    """Represents a dependency relationship between nodes."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_id: str
    target_id: str
    relationship: str = "depends_on"
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    latency_ms: float = 10.0
    bandwidth_mbps: float = 100.0
    is_critical: bool = False
    failure_probability: float = Field(default=0.01, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FailureEvent(BaseModel):
    """Represents a failure event in the simulation."""
    model_config = {"use_enum_values": True}
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = Field(default_factory=datetime.now)
    source_node_id: str
    stress_type: str = "load_spike"
    severity: str = "medium"
    propagation_path: list[str] = Field(default_factory=list)
    affected_nodes: list[str] = Field(default_factory=list)
    business_impact: dict[str, Any] = Field(default_factory=dict)
    root_cause: str = ""
    description: str = ""
    time_to_detect_seconds: float = 0.0
    time_to_resolve_seconds: float = 0.0
    is_external: bool = False


class SimulationState(BaseModel):
    """Current state of the simulation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    scenario_name: str = ""
    step: int = 0
    total_steps: int = 0
    elapsed_time_seconds: float = 0.0
    is_running: bool = False
    is_paused: bool = False
    speed_multiplier: float = 1.0
    active_failures: list[FailureEvent] = Field(default_factory=list)
    cascade_depth: int = 0
    total_nodes_affected: int = 0
    system_health_score: float = 1.0
    business_impact_score: float = 0.0
    timeline: list[dict[str, Any]] = Field(default_factory=list)


class PropagationResult(BaseModel):
    """Result of a failure propagation analysis."""
    model_config = {"use_enum_values": True}
    
    origin_node: str
    stress_type: str = "load_spike"
    cascade_path: list[list[str]] = Field(default_factory=list)
    total_affected: int = 0
    max_depth: int = 0
    critical_nodes_hit: list[str] = Field(default_factory=list)
    affected_nodes: list[str] = Field(default_factory=list)
    estimated_downtime_seconds: float = 0.0
    estimated_revenue_impact: float = 0.0
    severity: str = "medium"
    recommendations: list[str] = Field(default_factory=list)
    timeline_events: list[dict[str, Any]] = Field(default_factory=list)


class FragilityInsight(BaseModel):
    """An insight about system fragility."""
    model_config = {"use_enum_values": True}
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    description: str
    category: str
    severity: str = "medium"
    affected_nodes: list[str] = Field(default_factory=list)
    recommendation: str = ""
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)


class ScenarioConfig(BaseModel):
    """Configuration for a simulation scenario."""
    name: str
    description: str
    nodes: list[SystemNode] = Field(default_factory=list)
    edges: list[SystemEdge] = Field(default_factory=list)
    initial_failures: list[dict[str, Any]] = Field(default_factory=list)
    external_factors: list[dict[str, Any]] = Field(default_factory=list)
    business_context: dict[str, Any] = Field(default_factory=dict)
    simulation_duration_seconds: float = 300.0
    complexity_level: str = "medium"