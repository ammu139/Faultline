"""
Faultline ADK 2.0 Workflow Pipeline
Graph-based workflow that executes the full fragility analysis pipeline
using ADK's Workflow API with typed function nodes.

Pipeline: START → ingest → analyze → design_stress → propagate → generate_insights

This workflow can be invoked programmatically or used as a sub-agent.
"""

from __future__ import annotations
import sys
import os
from typing import Any

# Ensure faultline root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from google.adk.workflow import Workflow, node
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as genai_types

from app.schemas import (
    IngestionInput,
    IngestionOutput,
    AnalysisOutput,
    StressDesignOutput,
    StressScenario,
    PropagationOutput,
    PropagationResult,
    InsightOutput,
    InsightItem,
    Recommendation,
)

from core.graph_builder import SystemGraph
from core.failure_engine import FailureEngine
from core.simulator import FaultlineSimulator
from core.models import StressType, ScenarioConfig
from scenarios.ecommerce import build_ecommerce_scenario
from scenarios.banking import build_banking_scenario
from scenarios.cicd import build_cicd_scenario
from agents.dependency_agent import DependencyAgent
from agents.stress_agent import StressAgent
from agents.propagation_agent import PropagationAgent


# ─── Module-level state for workflow nodes ───────────────────────────────────

class _WorkflowState:
    """Holds state across workflow nodes within a single pipeline run."""
    def __init__(self):
        self.simulator: FaultlineSimulator | None = None
        self.graph: SystemGraph | None = None
        self.engine: FailureEngine | None = None
        self.scenario: ScenarioConfig | None = None
        self.analysis: dict[str, Any] = {}

_wf_state = _WorkflowState()


# ─── Model Configuration ────────────────────────────────────────────────────

_model_name = os.getenv("LLM_MODEL", "gpt-4o")
_base_url = os.getenv("OPENAI_BASE_URL", "")

if _base_url:
    _litellm_model = LiteLlm(model=f"openai/{_model_name}", api_base=_base_url)
else:
    _litellm_model = LiteLlm(model=f"openai/{_model_name}")


# ─── Workflow Function Nodes ─────────────────────────────────────────────────


def ingest_scenario(node_input: genai_types.Content) -> dict:
    """Parse user input and initialize the scenario.
    
    Expects user message like: "analyze ecommerce" or "banking worst_case"
    """
    # Extract text from Content
    text = ""
    if node_input and node_input.parts:
        text = node_input.parts[0].text if node_input.parts[0].text else ""
    
    text_lower = text.lower().strip()
    
    # Parse scenario_id and stress_mode from input
    scenario_id = "ecommerce"  # default
    stress_mode = "auto"  # default
    
    for sid in ["ecommerce", "banking", "cicd"]:
        if sid in text_lower:
            scenario_id = sid
            break
    
    for mode in ["worst_case", "targeted", "random", "auto"]:
        if mode in text_lower:
            stress_mode = mode
            break
    
    # Build scenario
    builders = {
        "ecommerce": build_ecommerce_scenario,
        "banking": build_banking_scenario,
        "cicd": build_cicd_scenario,
    }
    builder = builders[scenario_id]
    scenario = builder()
    
    # Initialize simulator
    simulator = FaultlineSimulator()
    simulator.initialize(scenario)
    
    # Store in workflow state
    _wf_state.simulator = simulator
    _wf_state.graph = simulator.graph
    _wf_state.engine = simulator.engine
    _wf_state.scenario = scenario
    
    return {
        "scenario_name": scenario.name,
        "scenario_id": scenario_id,
        "stress_mode": stress_mode,
        "total_nodes": len(simulator.graph.nodes),
        "total_edges": len(simulator.graph.edges),
        "node_types": list(set(n.node_type for n in simulator.graph.nodes.values())),
        "complexity_level": scenario.complexity_level,
    }


def analyze_graph(node_input: dict) -> dict:
    """Perform structural analysis on the dependency graph."""
    graph = _wf_state.graph
    if not graph:
        return {"error": "No graph initialized"}
    
    # Use DependencyAgent logic
    dep_agent = DependencyAgent(graph)
    result = dep_agent.execute({"scenario": _wf_state.scenario})
    
    if not result.success:
        return {"error": result.error or "Analysis failed"}
    
    analysis = result.data.get("analysis", {})
    _wf_state.analysis = analysis
    
    return {
        "single_points_of_failure": analysis.get("single_points_of_failure", []),
        "critical_paths": analysis.get("critical_paths", []),
        "high_fan_in_nodes": analysis.get("high_fan_in_nodes", []),
        "criticality_scores": analysis.get("criticality_scores", {}),
        "risk_clusters": analysis.get("risk_clusters", []),
        "graph_density": analysis.get("graph_density", 0),
        "is_connected": analysis.get("is_connected", True),
        "total_nodes": len(graph.nodes),
        "total_edges": len(graph.edges),
        "stress_mode": node_input.get("stress_mode", "auto"),
    }


def design_stress_scenarios(node_input: dict) -> dict:
    """Design intelligent stress test scenarios based on analysis."""
    graph = _wf_state.graph
    if not graph:
        return {"error": "No graph initialized"}
    
    stress_mode = node_input.get("stress_mode", "auto")
    
    # Use StressAgent logic
    stress_agent = StressAgent(graph)
    result = stress_agent.execute({
        "analysis": _wf_state.analysis,
        "stress_mode": stress_mode,
    })
    
    if not result.success:
        return {"error": result.error or "Stress design failed"}
    
    scenarios = result.data.get("scenarios", [])
    
    return {
        "scenarios": scenarios,
        "total_scenarios": len(scenarios),
        "stress_mode": stress_mode,
        "recommended_first": scenarios[0] if scenarios else None,
    }


def propagate_failures(node_input: dict) -> dict:
    """Execute failure propagation for designed stress scenarios."""
    graph = _wf_state.graph
    engine = _wf_state.engine
    if not graph or not engine:
        return {"error": "No graph/engine initialized"}
    
    scenarios = node_input.get("scenarios", [])
    if not scenarios:
        return {"error": "No scenarios to propagate"}
    
    # Use PropagationAgent logic
    prop_agent = PropagationAgent(graph, engine)
    result = prop_agent.execute({
        "scenarios": scenarios,
        "propagation_depth": 5,
        "decay_factor": 0.7,
    })
    
    if not result.success:
        return {"error": result.error or "Propagation failed"}
    
    prop_data = result.data
    propagation_results = prop_data.get("propagation_results", [])
    summary = prop_data.get("summary", {})
    
    return {
        "propagation_results": propagation_results,
        "total_scenarios_executed": len(propagation_results),
        "worst_scenario": summary.get("worst_scenario", ""),
        "worst_affected_count": summary.get("worst_affected_count", 0),
        "average_affected": summary.get("average_affected", 0),
        "average_cascade_depth": summary.get("average_cascade_depth", 0),
        "system_resilience_score": summary.get("system_resilience_score", 1.0),
        "analysis": _wf_state.analysis,
        "scenario_name": _wf_state.scenario.name if _wf_state.scenario else "Unknown",
    }


# ─── LLM Insight Agent Node ─────────────────────────────────────────────────

insight_agent = LlmAgent(
    name="insight_generator",
    model=_litellm_model,
    instruction="""You are a System Fragility Intelligence analyst.
Given the propagation results and structural analysis data, generate a comprehensive
fragility assessment with:

1. **risk_score**: A float between 0.0 and 1.0 representing overall system risk
2. **risk_level**: One of: LOW, MODERATE, ELEVATED, HIGH, CRITICAL
3. **summary**: A 1-2 sentence executive summary of the system's fragility posture
4. **insights**: A list of 3-6 key fragility insights, each with:
   - title: Short descriptive title
   - description: Detailed explanation
   - category: One of: structural, cascade, business_impact, resilience
   - severity: One of: low, medium, high, critical
5. **recommendations**: A list of 3-5 prioritized recommendations, each with:
   - recommendation: The actionable recommendation
   - priority: One of: low, medium, high, critical
   - category: One of: redundancy, monitoring, architecture, process
   - effort: One of: low, medium, high

Base your analysis on:
- Number and severity of single points of failure
- Cascade depth and breadth from propagation results
- System resilience score
- Critical nodes affected
- Graph density and connectivity

Be specific and quantitative. Reference actual node names and metrics from the data.""",
    output_schema=InsightOutput,
    output_key="insights",
)


# ─── Workflow Definition ─────────────────────────────────────────────────────

pipeline_workflow = Workflow(
    name="faultline_pipeline",
    description="Full fragility analysis pipeline: ingest → analyze → stress → propagate → insights",
    edges=[
        ('START', ingest_scenario),
        (ingest_scenario, analyze_graph),
        (analyze_graph, design_stress_scenarios),
        (design_stress_scenarios, propagate_failures),
        (propagate_failures, insight_agent),
    ],
)