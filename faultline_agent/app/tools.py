"""
Faultline ADK Tools
ADK 2.0 FunctionTool-compatible tool definitions.

Design Philosophy:
- Many small, composable tools (not monolithic "do everything" functions)
- The LLM agent decides WHICH tools to call, in WHAT order, and HOW to synthesize
- Each tool has a single responsibility and returns structured data
- Tools are stateless functions — shared state lives in _FaultlineState singleton
- All args are strings (ADK requirement for FunctionTools) — parsed internally

Architecture:
- Setup tools: Initialize system topology (must be called first)
- Explore tools: Navigate the dependency graph (composable primitives)
- Analyze tools: Identify structural vulnerabilities
- Simulate tools: Test failure hypotheses with statistical rigor
- Optimize tools: Recommend cost-effective improvements
- Memory tools: Track investigation history for pattern detection
"""

from __future__ import annotations
import sys
import os
from typing import Any

# Ensure faultline root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.graph_builder import SystemGraph
from core.failure_engine import FailureEngine
from core.simulator import FaultlineSimulator
from core.models import ScenarioConfig, StressType
from scenarios.ecommerce import build_ecommerce_scenario
from scenarios.banking import build_banking_scenario
from scenarios.cicd import build_cicd_scenario


# ─── Shared State ────────────────────────────────────────────────────────────

class _FaultlineState:
    """Module-level state holder for the simulation engine."""

    def __init__(self):
        self.simulator = FaultlineSimulator()
        self.graph: SystemGraph = SystemGraph()
        self.engine: FailureEngine | None = None
        self.initialized: bool = False
        self.current_scenario: str = ""
        self.simulation_history: list[dict] = []

    def reset(self):
        self.simulator.reset()
        self.graph = SystemGraph()
        self.engine = None
        self.initialized = False
        self.current_scenario = ""


_state = _FaultlineState()


def _get_scenario_builder(scenario_id: str):
    builders = {
        "ecommerce": build_ecommerce_scenario,
        "banking": build_banking_scenario,
        "cicd": build_cicd_scenario,
    }
    return builders.get(scenario_id)


# ─── Scenario & Setup Tools ─────────────────────────────────────────────────


def load_scenario(scenario_id: str) -> dict:
    """Load a system topology for analysis. This must be called before other tools.

    Args:
        scenario_id: System to load. One of: ecommerce, banking, cicd.

    Returns:
        dict with scenario name, node count, edge count, node types.
    """
    builder = _get_scenario_builder(scenario_id)
    if not builder:
        return {"error": f"Unknown scenario: {scenario_id}. Available: ecommerce, banking, cicd"}

    _state.reset()
    scenario = builder()
    _state.simulator.initialize(scenario)
    _state.graph = _state.simulator.graph
    _state.engine = _state.simulator.engine
    _state.initialized = True
    _state.current_scenario = scenario_id

    return {
        "status": "loaded",
        "scenario": scenario.name,
        "scenario_id": scenario_id,
        "total_nodes": len(_state.graph.nodes),
        "total_edges": len(_state.graph.edges),
        "node_types": list(set(n.node_type for n in _state.graph.nodes.values())),
        "complexity": scenario.complexity_level,
    }


def list_nodes() -> dict:
    """List all components in the system with their type, tier, and health.

    Returns:
        dict with nodes list sorted by criticality tier.
    """
    if not _state.initialized:
        return {"error": "No scenario loaded. Call load_scenario first."}

    nodes = []
    for nid, node in _state.graph.nodes.items():
        nodes.append({
            "id": nid,
            "name": node.name,
            "type": node.node_type,
            "tier": node.tier,
            "status": node.status if isinstance(node.status, str) else node.status.value,
            "health": round(node.health_score, 2),
            "business_value": round(node.business_value, 2),
        })

    nodes.sort(key=lambda x: (x["tier"], x["name"]))
    return {"nodes": nodes, "total": len(nodes)}


# ─── Graph Exploration Tools (Composable) ────────────────────────────────────


def find_dependencies(node_id: str) -> dict:
    """Find what a specific node depends on (upstream dependencies).

    Args:
        node_id: The node to inspect.

    Returns:
        dict with the node's upstream dependencies and their details.
    """
    if not _state.initialized:
        return {"error": "No scenario loaded."}

    node = _state.graph.get_node(node_id)
    if not node:
        available = [f"{nid} ({n.name})" for nid, n in list(_state.graph.nodes.items())[:10]]
        return {"error": f"Node '{node_id}' not found. Available: {available}"}

    deps = _state.graph.get_dependencies(node_id)
    dep_details = []
    for dep_id in deps:
        dep_node = _state.graph.get_node(dep_id)
        if dep_node:
            dep_details.append({
                "id": dep_id,
                "name": dep_node.name,
                "type": dep_node.node_type,
                "tier": dep_node.tier,
                "health": round(dep_node.health_score, 2),
            })

    return {
        "node": node_id,
        "node_name": node.name,
        "depends_on": dep_details,
        "dependency_count": len(dep_details),
    }


def find_dependents(node_id: str) -> dict:
    """Find what depends on a specific node (downstream dependents). If this node fails, these are affected.

    Args:
        node_id: The node to inspect.

    Returns:
        dict with downstream dependents that would be affected by this node's failure.
    """
    if not _state.initialized:
        return {"error": "No scenario loaded."}

    node = _state.graph.get_node(node_id)
    if not node:
        available = [f"{nid} ({n.name})" for nid, n in list(_state.graph.nodes.items())[:10]]
        return {"error": f"Node '{node_id}' not found. Available: {available}"}

    dependents = _state.graph.get_dependents(node_id)
    dep_details = []
    for dep_id in dependents:
        dep_node = _state.graph.get_node(dep_id)
        if dep_node:
            dep_details.append({
                "id": dep_id,
                "name": dep_node.name,
                "type": dep_node.node_type,
                "tier": dep_node.tier,
                "business_value": round(dep_node.business_value, 2),
            })

    return {
        "node": node_id,
        "node_name": node.name,
        "dependents": dep_details,
        "dependent_count": len(dep_details),
        "impact_note": f"If {node.name} fails, {len(dep_details)} downstream components are directly affected.",
    }


def compute_blast_radius(node_id: str) -> dict:
    """Calculate the full blast radius if a node fails — all transitively affected nodes.

    Args:
        node_id: The node to compute blast radius for.

    Returns:
        dict with total affected count, affected nodes by tier, and estimated impact.
    """
    if not _state.initialized:
        return {"error": "No scenario loaded."}

    node = _state.graph.get_node(node_id)
    if not node:
        return {"error": f"Node '{node_id}' not found."}

    blast = _state.graph.get_failure_blast_radius(node_id)
    affected_nodes = blast.get("affected_nodes", [])

    # Categorize by tier
    by_tier = {"tier_1_critical": [], "tier_2_important": [], "tier_3_standard": [], "tier_4_low": []}
    for nid in affected_nodes:
        n = _state.graph.get_node(nid)
        if n:
            tier_key = f"tier_{n.tier}_{'critical' if n.tier == 1 else 'important' if n.tier == 2 else 'standard' if n.tier == 3 else 'low'}"
            by_tier.setdefault(tier_key, []).append(n.name)

    return {
        "source_node": node_id,
        "source_name": node.name,
        "total_affected": blast.get("total_affected", 0),
        "affected_by_tier": {k: v for k, v in by_tier.items() if v},
        "percentage_of_system": round(blast.get("total_affected", 0) / max(len(_state.graph.nodes), 1) * 100, 1),
    }


def compute_node_criticality(node_id: str) -> dict:
    """Compute how critical a specific node is using graph centrality metrics.

    Args:
        node_id: The node to assess.

    Returns:
        dict with criticality score, centrality metrics, and risk assessment.
    """
    if not _state.initialized:
        return {"error": "No scenario loaded."}

    node = _state.graph.get_node(node_id)
    if not node:
        return {"error": f"Node '{node_id}' not found."}

    criticality = _state.graph.calculate_node_criticality()
    score = criticality.get(node_id, 0)

    # Rank among all nodes
    ranked = sorted(criticality.items(), key=lambda x: x[1], reverse=True)
    rank = next((i + 1 for i, (nid, _) in enumerate(ranked) if nid == node_id), 0)

    blast = _state.graph.get_failure_blast_radius(node_id)
    deps = _state.graph.get_dependencies(node_id)
    dependents = _state.graph.get_dependents(node_id)

    return {
        "node_id": node_id,
        "name": node.name,
        "criticality_score": round(score, 3),
        "rank": f"{rank}/{len(ranked)}",
        "tier": node.tier,
        "blast_radius": blast.get("total_affected", 0),
        "upstream_dependencies": len(deps),
        "downstream_dependents": len(dependents),
        "risk_level": "CRITICAL" if score > 0.7 else "HIGH" if score > 0.5 else "MODERATE" if score > 0.3 else "LOW",
    }


# ─── Structural Analysis Tools ──────────────────────────────────────────────


def find_single_points_of_failure() -> dict:
    """Identify all single points of failure — nodes whose removal disconnects the system.

    Returns:
        dict with SPOFs, their blast radius, and why they're dangerous.
    """
    if not _state.initialized:
        return {"error": "No scenario loaded."}

    spofs = _state.graph.find_single_points_of_failure()
    spof_details = []
    for nid in spofs:
        node = _state.graph.get_node(nid)
        blast = _state.graph.get_failure_blast_radius(nid)
        spof_details.append({
            "node_id": nid,
            "name": node.name if node else nid,
            "type": node.node_type if node else "unknown",
            "tier": node.tier if node else 0,
            "blast_radius": blast.get("total_affected", 0),
            "reason": f"Removing {node.name if node else nid} disconnects {blast.get('total_affected', 0)} nodes from the system.",
        })

    spof_details.sort(key=lambda x: x["blast_radius"], reverse=True)

    return {
        "single_points_of_failure": spof_details,
        "total_spofs": len(spof_details),
        "system_verdict": "FRAGILE" if len(spof_details) > 2 else "MODERATE" if spof_details else "RESILIENT",
    }


def find_critical_paths() -> dict:
    """Find the most critical dependency paths in the system — chains where failure propagates fastest.

    Returns:
        dict with critical paths and their risk characteristics.
    """
    if not _state.initialized:
        return {"error": "No scenario loaded."}

    paths = _state.graph.find_critical_paths()
    criticality = _state.graph.calculate_node_criticality()

    # Find high fan-in nodes (bottlenecks)
    high_fan_in = []
    for node_id in _state.graph.graph.nodes():
        dependents = _state.graph.get_dependents(node_id)
        if len(dependents) >= 3:
            node = _state.graph.get_node(node_id)
            high_fan_in.append({
                "node_id": node_id,
                "name": node.name if node else node_id,
                "dependent_count": len(dependents),
                "criticality": round(criticality.get(node_id, 0), 3),
            })

    high_fan_in.sort(key=lambda x: x["dependent_count"], reverse=True)

    return {
        "critical_paths": paths[:5],
        "bottleneck_nodes": high_fan_in[:5],
        "graph_density": round(_state.graph.get_graph_metrics().get("density", 0), 4),
    }


# ─── Simulation Tools ────────────────────────────────────────────────────────


def simulate_failure(node_id: str, stress_type: str, intensity: str) -> dict:
    """Simulate a single failure and trace the cascade propagation through the system.

    Args:
        node_id: ID of the node to fail.
        stress_type: Type of stress. One of: load_spike, latency, memory_pressure, disk_full, network_partition, dependency_failure, data_corruption, security_breach, external_outage, cascading_failure.
        intensity: Failure intensity between 0.1 and 1.0.

    Returns:
        dict with cascade path, affected nodes, severity, downtime estimate, and recommendations.
    """
    if not _state.initialized or not _state.engine:
        return {"error": "No scenario loaded. Call load_scenario first."}

    if node_id not in _state.graph.nodes:
        available = list(_state.graph.nodes.keys())[:10]
        return {"error": f"Node '{node_id}' not found. Available: {available}"}

    valid_types = [s.value for s in StressType]
    if stress_type not in valid_types:
        return {"error": f"Invalid stress_type. Valid: {valid_types}"}

    try:
        intensity_float = max(0.1, min(1.0, float(intensity)))
    except (ValueError, TypeError):
        intensity_float = 0.8

    # Reset and inject
    _state.engine.reset_system()
    stress = StressType(stress_type)
    event = _state.engine.inject_failure(node_id, stress, intensity_float)
    result = _state.engine.propagate_failure(node_id, stress, max_depth=5)

    # Collect affected nodes
    affected_details = []
    for nid, node in _state.graph.nodes.items():
        status = node.status if isinstance(node.status, str) else node.status.value
        if status != "healthy":
            affected_details.append({
                "id": nid,
                "name": node.name,
                "status": status,
                "health": round(node.health_score, 2),
            })

    # Record in history
    sim_record = {
        "node_id": node_id,
        "node_name": _state.graph.get_node(node_id).name if _state.graph.get_node(node_id) else node_id,
        "stress_type": stress_type,
        "intensity": intensity_float,
        "total_affected": result.total_affected,
        "severity": result.severity,
        "max_depth": result.max_depth,
    }
    _state.simulation_history.append(sim_record)

    return {
        "source_node": node_id,
        "source_name": _state.graph.get_node(node_id).name if _state.graph.get_node(node_id) else node_id,
        "stress_type": stress_type,
        "intensity": intensity_float,
        "total_affected": result.total_affected,
        "max_cascade_depth": result.max_depth,
        "severity": result.severity,
        "critical_nodes_hit": result.critical_nodes_hit,
        "estimated_downtime_seconds": round(result.estimated_downtime_seconds, 1),
        "estimated_revenue_impact": round(result.estimated_revenue_impact, 2),
        "affected_nodes": affected_details[:10],
        "recommendations": result.recommendations,
    }


def monte_carlo_simulate(node_id: str, stress_type: str, num_iterations: str) -> dict:
    """Run Monte Carlo simulation — multiple iterations with randomized parameters to get statistical confidence.

    Args:
        node_id: ID of the node to stress.
        stress_type: Type of stress to apply.
        num_iterations: Number of simulation iterations (10-100).

    Returns:
        dict with statistical results: mean/median/worst-case affected nodes, confidence intervals.
    """
    if not _state.initialized or not _state.engine:
        return {"error": "No scenario loaded."}

    if node_id not in _state.graph.nodes:
        return {"error": f"Node '{node_id}' not found."}

    valid_types = [s.value for s in StressType]
    if stress_type not in valid_types:
        return {"error": f"Invalid stress_type. Valid: {valid_types}"}

    try:
        iterations = max(10, min(100, int(num_iterations)))
    except (ValueError, TypeError):
        iterations = 50

    import numpy as np
    rng = np.random.default_rng()

    results = []
    for _ in range(iterations):
        _state.engine.reset_system()
        # Randomize intensity and decay
        intensity = float(rng.uniform(0.5, 0.95))
        stress = StressType(stress_type)
        _state.engine.inject_failure(node_id, stress, intensity)
        result = _state.engine.propagate_failure(
            node_id, stress,
            max_depth=5,
            decay_factor=float(rng.uniform(0.5, 0.85)),
        )
        results.append({
            "affected": result.total_affected,
            "depth": result.max_depth,
            "downtime": result.estimated_downtime_seconds,
        })

    affected_counts = [r["affected"] for r in results]
    downtimes = [r["downtime"] for r in results]

    node = _state.graph.get_node(node_id)

    return {
        "node": node_id,
        "node_name": node.name if node else node_id,
        "stress_type": stress_type,
        "iterations": iterations,
        "affected_nodes": {
            "mean": round(float(np.mean(affected_counts)), 1),
            "median": round(float(np.median(affected_counts)), 1),
            "p95_worst_case": round(float(np.percentile(affected_counts, 95)), 1),
            "max": int(np.max(affected_counts)),
            "min": int(np.min(affected_counts)),
        },
        "estimated_downtime_seconds": {
            "mean": round(float(np.mean(downtimes)), 1),
            "p95": round(float(np.percentile(downtimes, 95)), 1),
        },
        "failure_probability": round(sum(1 for a in affected_counts if a > 3) / iterations, 2),
        "confidence": "HIGH" if iterations >= 50 else "MODERATE",
    }


def compare_failure_scenarios(node_ids: str) -> dict:
    """Compare multiple failure hypotheses side-by-side to identify the highest-risk component.

    Args:
        node_ids: Comma-separated list of node IDs to compare (e.g., "redis_cache,payment_gateway,auth_service").

    Returns:
        dict with ranked comparison of failure impact for each node.
    """
    if not _state.initialized or not _state.engine:
        return {"error": "No scenario loaded."}

    ids = [nid.strip() for nid in node_ids.split(",") if nid.strip()]
    if not ids:
        return {"error": "Provide comma-separated node IDs."}

    comparisons = []
    for nid in ids:
        if nid not in _state.graph.nodes:
            comparisons.append({"node_id": nid, "error": "not found"})
            continue

        _state.engine.reset_system()
        stress = StressType.DEPENDENCY_FAILURE
        _state.engine.inject_failure(nid, stress, 0.85)
        result = _state.engine.propagate_failure(nid, stress, max_depth=5)

        node = _state.graph.get_node(nid)
        comparisons.append({
            "node_id": nid,
            "name": node.name if node else nid,
            "total_affected": result.total_affected,
            "max_depth": result.max_depth,
            "severity": result.severity,
            "estimated_downtime_seconds": round(result.estimated_downtime_seconds, 1),
            "risk_score": round(result.total_affected / max(len(_state.graph.nodes), 1), 2),
        })

    # Rank by risk
    valid = [c for c in comparisons if "error" not in c]
    valid.sort(key=lambda x: x["total_affected"], reverse=True)

    return {
        "comparisons": valid,
        "highest_risk": valid[0]["name"] if valid else "N/A",
        "recommendation": f"Prioritize resilience improvements for {valid[0]['name']} — it causes the most widespread cascade." if valid else "",
    }


# ─── Optimization Tools ──────────────────────────────────────────────────────


def recommend_optimization(budget_description: str) -> dict:
    """Given a resilience improvement goal, simulate different mitigation strategies and recommend the most cost-effective.

    Compares: adding redundancy to SPOFs, circuit breakers on critical paths, and load balancing on bottlenecks.

    Args:
        budget_description: Description of constraints or goals (e.g., "reduce risk with minimal changes" or "protect payment path").

    Returns:
        dict with ranked optimization options showing risk reduction per strategy.
    """
    if not _state.initialized or not _state.engine:
        return {"error": "No scenario loaded."}

    # Get current baseline
    spofs = _state.graph.find_single_points_of_failure()
    criticality = _state.graph.calculate_node_criticality()
    top_critical = sorted(criticality.items(), key=lambda x: x[1], reverse=True)[:5]

    strategies = []

    # Strategy 1: Add redundancy to top SPOF
    if spofs:
        top_spof = spofs[0]
        node = _state.graph.get_node(top_spof)
        blast = _state.graph.get_failure_blast_radius(top_spof)
        strategies.append({
            "strategy": f"Add redundancy/replica for {node.name if node else top_spof}",
            "target_node": top_spof,
            "type": "redundancy",
            "estimated_risk_reduction": round(blast.get("total_affected", 0) / max(len(_state.graph.nodes), 1) * 0.7, 2),
            "effort": "high",
            "reason": f"{node.name if node else top_spof} is a SPOF affecting {blast.get('total_affected', 0)} nodes. Adding a replica eliminates the single point of failure.",
        })

    # Strategy 2: Circuit breaker on highest-criticality node
    if top_critical:
        nid, score = top_critical[0]
        node = _state.graph.get_node(nid)
        dependents = _state.graph.get_dependents(nid)
        strategies.append({
            "strategy": f"Add circuit breaker on {node.name if node else nid}",
            "target_node": nid,
            "type": "circuit_breaker",
            "estimated_risk_reduction": round(score * 0.4, 2),
            "effort": "medium",
            "reason": f"{node.name if node else nid} has criticality {score:.2f} with {len(dependents)} dependents. A circuit breaker prevents cascade propagation.",
        })

    # Strategy 3: Load balancing on high fan-in node
    high_fan_in = []
    for nid_check in _state.graph.graph.nodes():
        deps = _state.graph.get_dependents(nid_check)
        if len(deps) >= 3:
            high_fan_in.append((nid_check, len(deps)))
    high_fan_in.sort(key=lambda x: x[1], reverse=True)

    if high_fan_in:
        nid, fan_count = high_fan_in[0]
        node = _state.graph.get_node(nid)
        strategies.append({
            "strategy": f"Add load balancer in front of {node.name if node else nid}",
            "target_node": nid,
            "type": "load_balancing",
            "estimated_risk_reduction": round(fan_count / max(len(_state.graph.nodes), 1) * 0.5, 2),
            "effort": "medium",
            "reason": f"{node.name if node else nid} has {fan_count} dependents. Load balancing distributes pressure and prevents overload cascades.",
        })

    # Strategy 4: Async queue on critical path
    if len(top_critical) >= 2:
        nid, score = top_critical[1]
        node = _state.graph.get_node(nid)
        strategies.append({
            "strategy": f"Introduce async queue between {node.name if node else nid} and its dependents",
            "target_node": nid,
            "type": "decoupling",
            "estimated_risk_reduction": round(score * 0.3, 2),
            "effort": "low",
            "reason": f"Decoupling {node.name if node else nid} with a queue absorbs load spikes and prevents synchronous cascade.",
        })

    # Rank by risk reduction / effort ratio
    effort_scores = {"low": 1, "medium": 2, "high": 3}
    for s in strategies:
        s["efficiency_score"] = round(s["estimated_risk_reduction"] / effort_scores.get(s["effort"], 2), 3)

    strategies.sort(key=lambda x: x["efficiency_score"], reverse=True)

    return {
        "optimization_strategies": strategies,
        "best_recommendation": strategies[0] if strategies else None,
        "total_potential_risk_reduction": round(sum(s["estimated_risk_reduction"] for s in strategies), 2),
    }


# ─── Memory & History Tools ──────────────────────────────────────────────────


def get_simulation_history() -> dict:
    """Get history of all simulations run in this session. Shows patterns in what's been tested.

    Returns:
        dict with simulation history and pattern analysis.
    """
    if not _state.simulation_history:
        return {"history": [], "message": "No simulations run yet. Use simulate_failure to start."}

    # Analyze patterns
    node_frequency = {}
    for sim in _state.simulation_history:
        name = sim.get("node_name", sim.get("node_id", "?"))
        node_frequency[name] = node_frequency.get(name, 0) + 1

    most_tested = sorted(node_frequency.items(), key=lambda x: x[1], reverse=True)

    # Find most fragile
    most_fragile = max(_state.simulation_history, key=lambda x: x.get("total_affected", 0))

    return {
        "total_simulations": len(_state.simulation_history),
        "history": _state.simulation_history[-10:],  # Last 10
        "most_tested_nodes": most_tested[:3],
        "most_fragile_finding": {
            "node": most_fragile.get("node_name", "?"),
            "affected": most_fragile.get("total_affected", 0),
            "severity": most_fragile.get("severity", "?"),
        },
    }


# ─── System Status Tools ─────────────────────────────────────────────────────


def get_system_status() -> dict:
    """Get current system health overview.

    Returns:
        dict with system_health, total_nodes, affected_count, critical_failures.
    """
    if not _state.initialized:
        return {"status": "not_initialized", "message": "Load a scenario first."}
    return _state.simulator.get_system_status()


def get_fragility_report() -> dict:
    """Get comprehensive fragility report with SPOFs, criticality rankings, and blast radius analysis.

    Returns:
        dict with full fragility assessment.
    """
    if not _state.initialized:
        return {"error": "No scenario loaded."}
    return _state.simulator.get_fragility_analysis()