"""
Faultline ADK Schemas
Pydantic models for structured I/O between workflow nodes.
These define the typed contracts for data flowing through the ADK Workflow pipeline.
"""

from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


# ─── Workflow Node I/O Schemas ───────────────────────────────────────────────


class IngestionInput(BaseModel):
    """Input to the ingestion node."""
    scenario_id: str = Field(description="Scenario identifier: ecommerce, banking, or cicd")
    stress_mode: str = Field(default="auto", description="Stress mode: auto, targeted, random, worst_case")


class IngestionOutput(BaseModel):
    """Output from the ingestion/initialization node."""
    scenario_name: str
    total_nodes: int
    total_edges: int
    node_types: list[str]
    complexity_level: str


class AnalysisOutput(BaseModel):
    """Output from the dependency analysis node."""
    single_points_of_failure: list[dict[str, Any]] = Field(default_factory=list)
    critical_paths: list[list[str]] = Field(default_factory=list)
    high_fan_in_nodes: list[dict[str, Any]] = Field(default_factory=list)
    criticality_scores: dict[str, float] = Field(default_factory=dict)
    risk_clusters: list[dict[str, Any]] = Field(default_factory=list)
    graph_density: float = 0.0
    is_connected: bool = True
    total_nodes: int = 0
    total_edges: int = 0


class StressScenario(BaseModel):
    """A single stress scenario designed by the stress agent."""
    name: str
    description: str
    stress_points: list[dict[str, Any]] = Field(default_factory=list)
    category: str = "auto"
    expected_impact: str = "medium"


class StressDesignOutput(BaseModel):
    """Output from the stress design node."""
    scenarios: list[StressScenario] = Field(default_factory=list)
    total_scenarios: int = 0
    stress_mode: str = "auto"
    recommended_first: Optional[StressScenario] = None


class PropagationResult(BaseModel):
    """Result of a single scenario propagation."""
    scenario_name: str
    scenario_category: str = "unknown"
    total_affected: int = 0
    affected_nodes: list[str] = Field(default_factory=list)
    max_cascade_depth: int = 0
    critical_nodes_hit: list[str] = Field(default_factory=list)
    worst_severity: str = "medium"
    estimated_downtime_seconds: float = 0.0
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class PropagationOutput(BaseModel):
    """Output from the propagation node."""
    propagation_results: list[PropagationResult] = Field(default_factory=list)
    total_scenarios_executed: int = 0
    worst_scenario: str = ""
    worst_affected_count: int = 0
    average_affected: float = 0.0
    average_cascade_depth: float = 0.0
    system_resilience_score: float = 1.0


class InsightItem(BaseModel):
    """A single fragility insight."""
    title: str
    description: str
    category: str = "structural"
    severity: str = "medium"
    affected_nodes: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    """A single actionable recommendation."""
    recommendation: str
    priority: str = "medium"
    category: str = "resilience"
    effort: str = "medium"


class InsightOutput(BaseModel):
    """Output from the insight generation node (LLM-powered)."""
    risk_score: float = Field(ge=0.0, le=1.0, description="Overall risk score 0-1")
    risk_level: str = Field(description="Risk level: LOW, MODERATE, ELEVATED, HIGH, CRITICAL")
    summary: str = Field(description="Executive summary of system fragility")
    insights: list[InsightItem] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)


# ─── Tool Response Schemas ───────────────────────────────────────────────────


class NodeInfo(BaseModel):
    """Information about a single node."""
    id: str
    name: str
    node_type: str
    tier: int
    status: str
    health: float
    business_value: float


class SystemStatus(BaseModel):
    """Current system health status."""
    system_health: float
    total_nodes: int
    affected_count: int
    critical_failures: list[str] = Field(default_factory=list)
    simulation_step: int = 0


class FailureInjectionResult(BaseModel):
    """Result of injecting a failure."""
    source_node: str
    stress_type: str
    severity: str
    total_affected: int
    max_depth: int
    cascade_path: list[list[str]] = Field(default_factory=list)
    critical_nodes_hit: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class FragilityReport(BaseModel):
    """Comprehensive fragility report."""
    single_points_of_failure: list[dict[str, Any]] = Field(default_factory=list)
    top_fragile_nodes: list[dict[str, Any]] = Field(default_factory=list)
    criticality_scores: dict[str, float] = Field(default_factory=dict)
    overall_resilience: float = 1.0