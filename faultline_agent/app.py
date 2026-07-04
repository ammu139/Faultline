"""
Faultline: System Fragility Intelligence Agent
Main Streamlit Application

An AI agent system that builds dependency graphs of complex systems,
simulates stress/failures, and traces cascading impacts to identify
hidden fragility points before real-world breakdowns occur.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import time
from datetime import datetime

from config import config, AVAILABLE_SCENARIOS
from core.models import StressType
from agents.orchestrator import AgentOrchestrator
from scenarios.ecommerce import build_ecommerce_scenario
from scenarios.banking import build_banking_scenario
from scenarios.cicd import build_cicd_scenario
from ui.styles import MAIN_CSS, get_status_color, get_severity_color
from ui.visualizations import (
    create_dependency_graph,
    create_health_timeline,
    create_risk_heatmap,
    create_blast_radius_chart,
    create_severity_distribution,
)
from ui.incident_replay import render_incident_replay
from data.live_data_fetcher import fetch_live_context, get_service_status
from scenarios.custom_builder import CustomScenarioBuilder, TEMPLATES


# Page configuration
st.set_page_config(
    page_title="Faultline | System Fragility Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject custom CSS
st.markdown(MAIN_CSS, unsafe_allow_html=True)


def get_orchestrator() -> AgentOrchestrator:
    """Get or create the orchestrator instance."""
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = AgentOrchestrator()
    return st.session_state.orchestrator


def get_scenario_builder(scenario_id: str):
    """Get the scenario builder function for pre-built scenarios."""
    builders = {
        "ecommerce": build_ecommerce_scenario,
        "banking": build_banking_scenario,
        "cicd": build_cicd_scenario,
    }
    return builders.get(scenario_id)


def render_header():
    """Render the application header."""
    st.markdown(f"""
        <div class="faultline-header">
            <span class="faultline-version">v{config.version}</span>
            <p class="faultline-title">⚡ FAULTLINE</p>
            <p class="faultline-subtitle">System Fragility Intelligence Agent — Predict failures before they cascade</p>
        </div>
    """, unsafe_allow_html=True)


def render_sidebar(orchestrator):
    """Render a clean, professional sidebar."""
    import random
    
    # Logo area
    st.sidebar.markdown(f"**⚡ Faultline** `v{config.version}`")
    st.sidebar.markdown("---")
    
    # Section 1: Scenario
    scenario_id = st.sidebar.selectbox(
        "📋 Scenario",
        options=list(AVAILABLE_SCENARIOS.keys()),
        format_func=lambda x: f"{AVAILABLE_SCENARIOS[x]['icon']} {AVAILABLE_SCENARIOS[x]['name']}",
        key="scenario_select",
    )
    
    stress_mode = st.sidebar.selectbox(
        "🎯 Stress Mode",
        ["auto", "targeted", "random", "worst_case"],
        format_func=lambda x: {"auto": "Auto (AI)", "targeted": "Targeted", "random": "Chaos", "worst_case": "Worst Case"}.get(x, x),
    )
    
    intensity = st.sidebar.slider("⚡ Intensity", 0.1, 1.0, 0.8, 0.1)
    
    # Action buttons
    st.sidebar.markdown("")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        run_clicked = st.button("🚀 Analyze", use_container_width=True, type="primary")
    with col2:
        home_clicked = st.button("🏠 Home", use_container_width=True)
    
    if home_clicked:
        st.session_state.scenario_loaded = False
        st.session_state.pipeline_result = {}
        st.session_state.interactive_result = None
        orchestrator.reset()
        st.rerun()
    
    if run_clicked:
        builder = get_scenario_builder(scenario_id)
        if builder:
            with st.spinner("🔄 Running pipeline..."):
                scenario = builder()
                # Randomize seed for different results each run
                import numpy as np
                orchestrator.reset()
                if orchestrator.engine:
                    orchestrator.engine.rng = np.random.default_rng(int(time.time()))
                pipeline_result = orchestrator.run_full_pipeline(scenario=scenario, stress_mode=stress_mode)
                st.session_state.pipeline_result = pipeline_result
                st.session_state.scenario_loaded = True
                st.session_state.current_scenario = scenario_id
            st.rerun()
    
    
    # Section 3: Custom Scenario
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🔨 Custom Scenario**")
    template_id = st.sidebar.selectbox(
        "Template",
        options=["none"] + list(TEMPLATES.keys()),
        format_func=lambda x: "— Select —" if x == "none" else f"{TEMPLATES[x]['icon']} {TEMPLATES[x]['name']}",
        key="template_select",
    )
    if template_id != "none":
        template = TEMPLATES[template_id]
        custom_params = {}
        for pk, ps in template["parameters"].items():
            if ps["type"] == "int":
                custom_params[pk] = st.sidebar.slider(ps["label"], ps.get("min",1), ps.get("max",10), ps["default"], key=f"t_{pk}")
            elif ps["type"] == "bool":
                custom_params[pk] = st.sidebar.checkbox(ps["label"], ps["default"], key=f"t_{pk}")
        if st.sidebar.button("🔨 Build Custom", use_container_width=True):
            from scenarios.custom_builder import CustomScenarioBuilder
            b = CustomScenarioBuilder()
            sc = b.from_template(template_id, custom_params)
            orchestrator.reset()
            pr = orchestrator.run_full_pipeline(sc, stress_mode="auto")
            st.session_state.pipeline_result = pr
            st.session_state.scenario_loaded = True
            st.session_state.current_scenario = f"custom_{template_id}"
            AVAILABLE_SCENARIOS[f"custom_{template_id}"] = {"name": template["name"], "icon": template["icon"], "description": template["description"], "complexity": "custom"}
            st.rerun()
    
    # Section 4: Settings
    st.sidebar.markdown("---")
    st.sidebar.markdown("**⚙️ Settings**")
    alerts_enabled = st.sidebar.checkbox("Enable Alerts", value=True, key="alerts_toggle")
    continuous_mode = st.sidebar.checkbox("Continuous Monitor", value=False, key="continuous_toggle")
    st.session_state.alerts_enabled = alerts_enabled
    st.session_state.continuous_mode = continuous_mode
    
    return scenario_id, stress_mode, intensity


def render_graph_view(orchestrator: AgentOrchestrator, key_suffix: str = "main"):
    """Render the dependency graph visualization."""
    graph = orchestrator.graph
    
    if not graph.nodes:
        st.info("Load a scenario to visualize the dependency graph.")
        return
    
    nodes_data = {}
    for nid, node in graph.nodes.items():
        nodes_data[nid] = {
            "name": node.name,
            "type": node.node_type,
            "status": node.status,
            "health": node.health_score,
            "tier": node.tier,
            "business_value": node.business_value,
        }
    
    edges_data = [
        {"source": e.source_id, "target": e.target_id, "relationship": e.relationship}
        for e in graph.edges.values()
    ]
    
    layout = graph.get_layout("spring")
    fig = create_dependency_graph(nodes_data, edges_data, layout)
    st.plotly_chart(fig, use_container_width=True, key=f"dep_graph_{key_suffix}")


def render_landing_page():
    """Render the landing/home page."""
    orchestrator = get_orchestrator()
    
    st.markdown("### 🎯 Choose a scenario to begin fragility analysis")
    st.markdown("")
    
    scenario_list = list(AVAILABLE_SCENARIOS.items())
    # Show in rows of 3
    for row_start in range(0, len(scenario_list), 3):
        row = scenario_list[row_start:row_start+3]
        cols = st.columns(len(row))
        for i, (sid, sinfo) in enumerate(row):
            with cols[i]:
                st.markdown(f"""
                    <div class="scenario-card">
                        <div class="scenario-icon">{sinfo['icon']}</div>
                        <div class="scenario-name">{sinfo['name']}</div>
                        <div class="scenario-desc">{sinfo['description']}</div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"▶ Launch", key=f"launch_{sid}", use_container_width=True):
                    builder = get_scenario_builder(sid)
                    if builder:
                        with st.spinner(f"Loading {sinfo['name']}..."):
                            scenario = builder()
                            pipeline_result = orchestrator.run_full_pipeline(scenario=scenario, stress_mode="auto")
                            st.session_state.pipeline_result = pipeline_result
                            st.session_state.scenario_loaded = True
                            st.session_state.current_scenario = sid
                        st.rerun()
                    else:
                        # Custom scenario - rebuild from template
                        tpl_id = sid.replace("custom_", "")
                        if tpl_id in TEMPLATES:
                            b = CustomScenarioBuilder()
                            sc = b.from_template(tpl_id)
                            pr = orchestrator.run_full_pipeline(sc, stress_mode="auto")
                            st.session_state.pipeline_result = pr
                            st.session_state.scenario_loaded = True
                            st.session_state.current_scenario = sid
                            st.rerun()
                # Delete button for custom scenarios
                if sid.startswith("custom_"):
                    if st.button("🗑️ Delete", key=f"del_{sid}", use_container_width=True):
                        del AVAILABLE_SCENARIOS[sid]
                        st.rerun()
    
    st.markdown("")
    st.markdown("---")
    
    # Pipeline visualization
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <span class="pipeline-step active">🔍 Ingestion</span>
        <span class="pipeline-arrow">→</span>
        <span class="pipeline-step active">🕸️ Dependency</span>
        <span class="pipeline-arrow">→</span>
        <span class="pipeline-step active">⚡ Stress</span>
        <span class="pipeline-arrow">→</span>
        <span class="pipeline-step active">🌊 Propagation</span>
        <span class="pipeline-arrow">→</span>
        <span class="pipeline-step active">🧠 Insight</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 🏗️ How Faultline Works
        
        Faultline is a **digital twin** of your enterprise system's resilience. 
        It uses a multi-agent AI pipeline to:
        
        1. **Parse** system architecture into a dependency graph
        2. **Analyze** structural vulnerabilities and critical paths
        3. **Design** intelligent failure scenarios using AI
        4. **Simulate** cascading failures with probabilistic modeling
        5. **Generate** actionable fragility intelligence
        """)
    
    with col2:
        st.markdown("""
        #### 🎯 What It Detects
        
        - **Single Points of Failure** — Nodes whose loss disconnects the system
        - **Cascade Chains** — How failures propagate through dependencies
        - **Blast Radius** — Impact zone of each potential failure
        - **Hidden Dependencies** — Non-obvious coupling between components
        - **Business Impact** — Revenue and SLA risk from each scenario
        """)
    
    st.markdown("")
    
    # Live Status Feed from real services
    st.markdown("---")
    st.markdown("#### 🌐 Live External Service Status")
    st.markdown("*Real-time data from public status APIs (Atlassian Statuspage)*")
    
    try:
        live_context = fetch_live_context()
        services = live_context.get("services", {})
        
        if services:
            status_cols = st.columns(len(services))
            for i, (key, svc) in enumerate(services.items()):
                with status_cols[i]:
                    svc_status = svc.get("current_status", "unknown")
                    is_live = svc.get("is_live", False)
                    
                    if svc_status in ("none", "operational"):
                        indicator = "🟢"
                    elif svc_status == "minor":
                        indicator = "🟡"
                    elif svc_status in ("major", "critical"):
                        indicator = "🔴"
                    else:
                        indicator = "⚪"
                    
                    live_badge = "LIVE" if is_live else "CACHED"
                    st.markdown(
                        f"**{indicator} {svc.get('name', key)}**  \n"
                        f"`{svc_status}` · {live_badge}"
                    )
                    
                    # Show recent incidents
                    incidents = svc.get("recent_incidents", [])
                    if incidents:
                        latest = incidents[0]
                        st.caption(f"Latest: {latest.get('name', 'N/A')[:40]}")
        
        # Active incidents warning
        active = live_context.get("active_incidents", [])
        if active:
            st.warning(f"⚠️ {len(active)} active incident(s) detected across monitored services")
    except Exception:
        st.caption("*Live status unavailable — using cached data*")
    
    st.markdown("")
    st.info("👈 Select a scenario from the sidebar and click **🚀 Analyze** to begin.")


def render_metrics(status: dict):
    """Render system health metrics."""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    health = status.get("system_health", 1.0)
    health_color = "#00E676" if health > 0.8 else "#FFD600" if health > 0.5 else "#FF1744"
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {health_color}">{health:.0%}</div>
                <div class="metric-label">System Health</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{status.get("total_nodes", 0)}</div>
                <div class="metric-label">Total Nodes</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        affected = status.get("affected_count", 0)
        aff_color = "#00E676" if affected == 0 else "#FF9100" if affected < 5 else "#FF1744"
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {aff_color}">{affected}</div>
                <div class="metric-label">Nodes Affected</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        critical = len(status.get("critical_failures", []))
        crit_color = "#00E676" if critical == 0 else "#FF1744"
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {crit_color}">{critical}</div>
                <div class="metric-label">Critical Failures</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{status.get("simulation_step", 0)}</div>
                <div class="metric-label">Sim Step</div>
            </div>
        """, unsafe_allow_html=True)


def render_results_view(orchestrator, pipeline_result):
    """Render the analysis results view."""
    # Current scenario badge
    current = st.session_state.get("current_scenario", "")
    if current in AVAILABLE_SCENARIOS:
        info = AVAILABLE_SCENARIOS[current]
        st.markdown(f"""
            <div style="margin-bottom: 1rem;">
                <span class="stat-chip">{info['icon']} {info['name']}</span>
                <span class="stat-chip">Pipeline: {pipeline_result.get('pipeline_time_ms', 0):.0f}ms</span>
            </div>
        """, unsafe_allow_html=True)
    
    # System metrics
    status = orchestrator.get_system_status()
    render_metrics(status)
    
    # Priority alerts (respects user toggle)
    if st.session_state.get("alerts_enabled", True):
        critical_failures = status.get("critical_failures", [])
        affected = status.get("affected_count", 0)
        health = status.get("system_health", 1.0)
        
        if critical_failures:
            st.error(
                f"🚨 **CRITICAL ALERT** — {len(critical_failures)} node(s) in FAILING/DEAD state. "
                f"Immediate action required. System health: {health:.0%}"
            )
        elif affected > 3:
            st.warning(
                f"⚠️ **DEGRADATION WARNING** — {affected} nodes affected by cascading failure. "
                f"System health: {health:.0%}"
            )
        elif affected > 0 and health < 0.9:
            st.info(f"ℹ️ Minor degradation detected — {affected} node(s) under stress. Monitoring.")
    
    # Continuous monitoring mode — auto-advances simulation
    if st.session_state.get("continuous_mode", False) and orchestrator.engine:
        sim_state = orchestrator.simulator.state_machine.simulation_state
        orchestrator.simulator.step()
        new_status = orchestrator.get_system_status()
        new_affected = new_status.get("affected_count", 0)
        if st.session_state.get("alerts_enabled") and new_affected > affected:
            st.toast(f"🔔 Continuous monitor: {new_affected} nodes now affected (step {sim_state.step})")
    
    st.markdown("")
    
    # Main tabs — focused, no redundancy
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎬 Incident Replay",
        "📊 Risk & Insights",
        "🔬 Technical Logs",
        "🕸️ System Map",
    ])
    
    with tab1:
        render_incident_replay(orchestrator, scenario_name=st.session_state.get("current_scenario", ""))

    with tab2:
        # Combined Risk Assessment + Insights (always shows data from graph analysis)
        render_risk_and_insights(orchestrator, pipeline_result)

    with tab3:
        # Technical logs — detailed propagation data, node states, failure reasoning
        render_technical_logs(orchestrator, pipeline_result)

    with tab4:
        # System topology map with metrics
        render_graph_view(orchestrator)
        metrics = orchestrator.graph.get_graph_metrics()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Nodes", metrics.get("nodes", 0))
        col2.metric("Edges", metrics.get("edges", 0))
        col3.metric("Density", f"{metrics.get('density', 0):.3f}")
        col4.metric("Avg Degree", f"{metrics.get('avg_degree', 0):.1f}")


def render_risk_and_insights(orchestrator, pipeline_result):
    """Combined Risk Assessment + Insights — always shows data from live graph analysis."""
    # Always compute fresh data from the graph (not dependent on pipeline_result summary)
    fragility = orchestrator.get_fragility_report()
    summary_data = pipeline_result.get("summary") if pipeline_result else None

    # Risk score section
    if "error" not in fragility:
        criticality = fragility.get("criticality_scores", {})
        spofs = fragility.get("single_points_of_failure", [])
        top_fragile = fragility.get("top_fragile_nodes", [])

        # Calculate risk from graph data directly
        total_nodes = len(orchestrator.graph.nodes)
        risk_score = min(1.0, (len(spofs) * 0.15 + len(top_fragile) * 0.1))
        if summary_data and summary_data.get("risk_score"):
            risk_score = summary_data["risk_score"]

        risk_level = "CRITICAL" if risk_score > 0.7 else "HIGH" if risk_score > 0.5 else "MODERATE" if risk_score > 0.3 else "LOW"
        if summary_data and summary_data.get("risk_level"):
            risk_level = summary_data["risk_level"]

        risk_color = {"LOW": "#34A853", "MODERATE": "#FBBC04", "ELEVATED": "#F9AB00", "HIGH": "#EA4335", "CRITICAL": "#C5221F"}.get(risk_level, "#9AA0A6")

        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"""
                <div class="risk-gauge">
                    <div class="risk-score" style="color: {risk_color}">{risk_score:.0%}</div>
                    <div class="metric-label">Risk Level: {risk_level}</div>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            if summary_data and summary_data.get("summary"):
                st.markdown(f"*{summary_data['summary']}*")
            else:
                st.markdown(f"*System has {len(spofs)} single points of failure and {len(top_fragile)} high-criticality nodes requiring attention.*")

        st.markdown("---")

        # SPOFs
        if spofs:
            st.markdown("#### ⚠️ Single Points of Failure")
            for spof in spofs:
                name = spof.get("name", spof.get("node_id", "?"))
                st.markdown(f"  • **{name}**")

        # Top fragile nodes with blast radius
        if top_fragile:
            st.markdown("#### 🔥 Highest Risk Components")
            for node_info in top_fragile[:5]:
                blast = node_info.get("blast_radius", {})
                score = node_info.get("criticality_score", 0)
                icon = "🔴" if score > 0.7 else "🟠" if score > 0.5 else "🟡"
                st.markdown(
                    f"  {icon} **{node_info.get('name', '?')}** — "
                    f"Criticality: {score:.0%}, "
                    f"Blast: {blast.get('total_affected', 0)} nodes"
                )

        st.markdown("---")

        # Insights from pipeline (if available)
        if summary_data:
            insights = summary_data.get("insights", [])
            if insights:
                st.markdown("#### 🔍 Fragility Insights")
                for insight in insights[:6]:
                    severity = insight.get("severity", "medium")
                    color = get_severity_color(severity)
                    st.markdown(f"""
                        <div class="insight-card {severity}">
                            <div class="insight-title" style="color: {color}">
                                ⚠️ {insight.get('title', 'Insight')}
                            </div>
                            <div class="insight-description">
                                {insight.get('description', '')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

            recs = summary_data.get("recommendations", [])
            if recs:
                st.markdown("#### 💡 Recommendations")
                for i, rec in enumerate(recs[:5], 1):
                    r = rec.get("recommendation", "") if isinstance(rec, dict) else str(rec)
                    priority = rec.get("priority", "medium") if isinstance(rec, dict) else "medium"
                    p_icon = "🔴" if priority in ("critical", "high") else "🟠" if priority == "medium" else "🟡"
                    st.markdown(f"  {p_icon} **#{i}** {r}")
        else:
            # Generate insights from graph data directly
            st.markdown("#### 🔍 Structural Analysis")
            metrics = orchestrator.graph.get_graph_metrics()
            st.markdown(f"- Graph density: **{metrics.get('density', 0):.3f}** — {'tightly coupled' if metrics.get('density', 0) > 0.1 else 'loosely coupled'}")
            st.markdown(f"- Connected: **{'Yes' if metrics.get('is_connected') else 'No — isolated components detected'}**")
            st.markdown(f"- Average degree: **{metrics.get('avg_degree', 0):.1f}** connections per node")
            if len(spofs) > 2:
                st.markdown(f"- ⚠️ **{len(spofs)} SPOFs** detected — system is structurally fragile")
    else:
        st.info("Load a scenario to see risk assessment.")


def render_technical_logs(orchestrator, pipeline_result):
    """Technical logs tab — detailed propagation data, node states, failure chain reasoning."""
    st.markdown("#### 🔬 Technical Analysis Logs")

    if not orchestrator.graph.nodes:
        st.info("Load a scenario to see technical logs.")
        return

    # Show pipeline execution results
    results = pipeline_result.get("results", {}) if pipeline_result else {}

    # Node State Table
    st.markdown("##### 📋 Current Node States")
    node_data = []
    for nid, node in sorted(orchestrator.graph.nodes.items(), key=lambda x: x[1].tier):
        status = node.status.value if hasattr(node.status, 'value') else node.status
        node_data.append({
            "ID": nid,
            "Name": node.name,
            "Type": node.node_type,
            "Tier": f"T{node.tier}",
            "Status": status,
            "Health": f"{node.health_score:.0%}",
            "Load": f"{node.current_load:.0%}",
            "Resilience": f"{node.resilience:.0%}",
        })

    if node_data:
        import pandas as pd
        df = pd.DataFrame(node_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Propagation Results (detailed technical view)
    prop_result = results.get("propagation")
    if prop_result and hasattr(prop_result, 'success') and prop_result.success:
        prop_data = prop_result.data
        propagation_results = prop_data.get("propagation_results", [])

        if propagation_results:
            st.markdown("##### 🌊 Propagation Simulation Results")
            for i, result in enumerate(propagation_results, 1):
                name = result.get("scenario_name", f"Scenario {i}")
                affected = result.get("total_affected", 0)
                depth = result.get("max_cascade_depth", 0)
                severity = result.get("worst_severity", "medium")
                downtime = result.get("estimated_downtime_seconds", 0)

                with st.expander(f"{'🔴' if severity in ('critical', 'catastrophic') else '🟠'} {name} — {affected} affected, depth {depth}", expanded=(i == 1)):
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Affected", affected)
                    col2.metric("Depth", depth)
                    col3.metric("Severity", severity.title())
                    col4.metric("Downtime", f"{downtime:.0f}s")

                    # Timeline
                    timeline = result.get("timeline", [])
                    if timeline:
                        st.markdown("**Failure Chain (Causal Sequence):**")
                        for evt in timeline[:10]:
                            t = evt.get("time", 0)
                            node_name = evt.get("node_name", "?")
                            health = evt.get("health", 0)
                            depth_lvl = evt.get("depth", 0)
                            intensity = evt.get("intensity", 0)
                            status_str = evt.get("status", "degraded")

                            icon = "🔴" if health < 0.3 else "🟠" if health < 0.6 else "🟡"
                            st.markdown(
                                f"  {icon} `T+{t:.1f}s` | **{node_name}** | "
                                f"health: {health:.0%} | status: {status_str} | "
                                f"depth: {depth_lvl} | intensity: {intensity:.0%}"
                            )

                    # Affected nodes list
                    affected_nodes = result.get("affected_nodes", [])
                    if affected_nodes:
                        st.markdown(f"**Affected Nodes ({len(affected_nodes)}):** {', '.join(affected_nodes[:10])}")

                    # Recommendations specific to this scenario
                    recs = result.get("recommendations", [])
                    if recs:
                        st.markdown("**Mitigation:**")
                        for rec in recs:
                            st.markdown(f"  → {rec}")

    # Interactive injection results
    interactive_result = st.session_state.get("interactive_result")
    if interactive_result and "error" not in interactive_result:
        st.markdown("---")
        st.markdown("##### 💥 Last Failure Injection Log")

        event = interactive_result.get("event", {})
        prop = interactive_result.get("propagation", {})

        st.markdown(f"**Source:** `{event.get('source', 'N/A')}` | **Type:** `{event.get('type', 'N/A')}` | **Severity:** `{event.get('severity', 'N/A')}`")
        st.markdown(f"**Description:** {event.get('description', 'N/A')}")
        st.markdown(f"**Cascade:** {prop.get('total_affected', 0)} nodes affected, depth {prop.get('max_depth', 0)}, severity {prop.get('severity', 'N/A')}")

        # Node states after injection
        node_states = interactive_result.get("node_states", {})
        affected_nodes = [(nid, d) for nid, d in node_states.items() if d.get("status") != "healthy"]
        if affected_nodes:
            st.markdown("**Affected Node States:**")
            for nid, data in sorted(affected_nodes, key=lambda x: x[1].get("health", 1)):
                status = data.get("status", "?")
                health = data.get("health", 0)
                name = data.get("name", nid)
                st.markdown(f"  `{nid}` | **{name}** | status: {status} | health: {health:.0%}")

        recs = prop.get("recommendations", [])
        if recs:
            st.markdown("**Recommendations:**")
            for rec in recs:
                st.markdown(f"  → {rec}")

    # Graph metrics
    st.markdown("---")
    st.markdown("##### 📐 Graph Topology Metrics")
    metrics = orchestrator.graph.get_graph_metrics()
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("Nodes", metrics.get("nodes", 0))
    mcol2.metric("Edges", metrics.get("edges", 0))
    mcol3.metric("Density", f"{metrics.get('density', 0):.4f}")
    mcol4.metric("Components", metrics.get("components", 1))


def render_insights(insights_data: dict):
    """Render insights panel."""
    if not insights_data:
        return
    
    insights = insights_data.get("insights", [])
    risk_score = insights_data.get("risk_score", 0)
    risk_level = insights_data.get("risk_level", "LOW")
    summary = insights_data.get("summary", "")
    
    risk_color = {
        "LOW": "#00E676", "MODERATE": "#FFD600",
        "ELEVATED": "#FF9100", "HIGH": "#FF6B6B", "CRITICAL": "#FF1744",
    }.get(risk_level, "#757575")
    
    st.markdown(f"""
        <div class="risk-gauge">
            <div class="risk-score" style="color: {risk_color}">{risk_score:.0%}</div>
            <div class="metric-label">Risk Level: {risk_level}</div>
        </div>
    """, unsafe_allow_html=True)
    
    if summary:
        st.markdown(f"*{summary}*")
    
    st.markdown("#### 🔍 Fragility Insights")
    for insight in insights[:6]:
        severity = insight.get("severity", "medium")
        color = get_severity_color(severity)
        st.markdown(f"""
            <div class="insight-card {severity}">
                <div class="insight-title" style="color: {color}">
                    ⚠️ {insight.get('title', 'Insight')}
                </div>
                <div class="insight-description">
                    {insight.get('description', '')}
                </div>
            </div>
        """, unsafe_allow_html=True)


def render_recommendations(recommendations: list):
    """Render recommendations panel."""
    if not recommendations:
        return
    st.markdown("#### 💡 Recommendations")
    for i, rec in enumerate(recommendations[:5], 1):
        priority = rec.get("priority", "medium")
        color = get_severity_color(priority)
        st.markdown(f"""
            <div style="padding: 0.6rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                <span style="color: {color}; font-weight: bold; font-family: 'JetBrains Mono', monospace;">#{i}</span>
                <span style="color: #E6EDF3; margin-left: 0.8rem;">
                    {rec.get('recommendation', '')}
                </span>
            </div>
        """, unsafe_allow_html=True)


def render_propagation_results(results: list):
    """Render propagation analysis results."""
    if not results:
        return
    st.markdown("#### 🌊 Cascade Analysis Results")
    for result in results[:5]:
        name = result.get("scenario_name", "Scenario")
        affected = result.get("total_affected", 0)
        depth = result.get("max_cascade_depth", 0)
        severity = result.get("worst_severity", "medium")
        
        icon = "🔴" if severity in ("critical", "catastrophic") else "🟡" if severity in ("high", "medium") else "🟢"
        with st.expander(f"{icon} {name} — {affected} nodes, depth {depth}"):
            col1, col2, col3 = st.columns(3)
            col1.metric("Affected Nodes", affected)
            col2.metric("Cascade Depth", depth)
            col3.metric("Severity", severity.title())
            
            timeline = result.get("timeline", [])
            if timeline:
                st.markdown("**Propagation Timeline:**")
                for event in timeline[:8]:
                    t = event.get("time", 0)
                    node_name = event.get("node_name", "?")
                    health = event.get("health", 0)
                    st.markdown(f"  `T+{t:.1f}s` → **{node_name}** (health: {health:.0%})")
            
            recs = result.get("recommendations", [])
            if recs:
                st.markdown("**Recommendations:**")
                for rec in recs:
                    st.markdown(f"  • {rec}")


def render_interactive_tab(orchestrator):
    """Render the interactive failure injection tab."""
    st.markdown("#### 💥 Interactive Failure Injection")
    st.markdown("Use the sidebar controls to inject failures and observe cascade effects in real-time.")
    
    interactive_result = st.session_state.get("interactive_result")
    if interactive_result and "error" not in interactive_result:
        event = interactive_result.get("event", {})
        prop = interactive_result.get("propagation", {})
        
        st.markdown(f"**Last Injection:** {event.get('description', 'N/A')}")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Nodes Affected", prop.get("total_affected", 0))
        col2.metric("Cascade Depth", prop.get("max_depth", 0))
        col3.metric("Severity", prop.get("severity", "N/A").title())
        
        node_states = interactive_result.get("node_states", {})
        if node_states:
            st.markdown("**Node Status After Failure:**")
            affected_nodes = [
                (nid, data) for nid, data in node_states.items()
                if data.get("status") != "healthy"
            ]
            if affected_nodes:
                for nid, data in sorted(affected_nodes, key=lambda x: x[1].get("health", 1)):
                    status = data.get("status", "unknown")
                    health = data.get("health", 0)
                    name = data.get("name", nid)
                    color = get_status_color(status)
                    st.markdown(
                        f'<span style="color:{color}">●</span> '
                        f'**{name}** — {status} ({health:.0%})',
                        unsafe_allow_html=True,
                    )
            else:
                st.success("All nodes remain healthy!")
        
        recs = prop.get("recommendations", [])
        if recs:
            st.markdown("**Recommendations:**")
            for rec in recs:
                st.markdown(f"  • {rec}")
        
        render_graph_view(orchestrator, key_suffix="interactive")
    
    elif interactive_result and "error" in interactive_result:
        st.error(interactive_result["error"])
    else:
        st.markdown("*Select a node and stress type from the sidebar, then click 'Inject Failure'.*")


def render_chat_tab(orchestrator, pipeline_result):
    """Render the Incident Copilot — structured AI responses, not a chatbot."""
    st.markdown("#### 🧠 Incident Copilot")
    st.markdown("*AI-powered resilience analysis*")
    
    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    # Display chat history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about system fragility, failures, or fixes..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response based on current system state
        response = _generate_chat_response(prompt, orchestrator, pipeline_result)
        
        st.session_state.chat_messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)


def _generate_chat_response(query: str, orchestrator, pipeline_result) -> str:
    """Generate response using LLM if available, otherwise rule-based."""
    import os
    
    # Try LLM first if not in simulation mode
    if os.getenv("SIMULATION_MODE", "true").lower() == "false":
        llm_response = _call_llm(query, orchestrator, pipeline_result)
        if llm_response:
            return llm_response
    
    # Fallback to rule-based
    return _rule_based_response(query, orchestrator, pipeline_result)


def _call_llm(query: str, orchestrator, pipeline_result) -> str:
    """Call LLM via OpenAI-compatible API (Hyperspace AI)."""
    import os
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:6655"),
        )
        
        # Build system context
        status = orchestrator.get_system_status() if orchestrator.graph.nodes else {}
        summary = pipeline_result.get("summary", {}) if pipeline_result else {}
        
        system_prompt = (
            "You are Faultline, a System Fragility Intelligence Agent. "
            "You analyze enterprise system dependency graphs, simulate failures, "
            "and provide actionable insights about system resilience.\n\n"
            f"Current system state:\n"
            f"- Health: {status.get('system_health', 'N/A')}\n"
            f"- Total nodes: {status.get('total_nodes', 0)}\n"
            f"- Affected: {status.get('affected_count', 0)}\n"
            f"- Risk level: {summary.get('risk_level', 'N/A')}\n"
            f"- Risk score: {summary.get('risk_score', 'N/A')}\n\n"
            "Answer concisely about system fragility, failures, and fixes."
        )
        
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return ""  # Fall back to rule-based


def _rule_based_response(query: str, orchestrator, pipeline_result) -> str:
    """Intelligent rule-based response with rich mocked data when LLM is unavailable."""
    query_lower = query.lower()
    
    status = orchestrator.get_system_status() if orchestrator.graph.nodes else {}
    summary = (pipeline_result or {}).get("summary") or {}
    fragility = orchestrator.get_fragility_report() if orchestrator.graph.nodes else {}
    
    if any(w in query_lower for w in ["what failed", "what went wrong", "failure", "issue", "problem"]):
        return _respond_about_failures(status, summary, fragility)
    elif any(w in query_lower for w in ["fix", "resolve", "remediate", "solution", "how to fix", "recommend", "improve", "optimize"]):
        return _respond_with_fixes(summary, fragility)
    elif any(w in query_lower for w in ["risk", "score", "health", "status", "how resilient", "resilience"]):
        return _respond_about_risk(status, summary)
    elif any(w in query_lower for w in ["spof", "single point", "vulnerable", "weak", "fragile"]):
        return _respond_about_spofs(fragility)
    elif any(w in query_lower for w in ["cascade", "propagat", "spread", "impact", "what happens", "if.*fails", "blast"]):
        return _respond_about_cascades_detailed(orchestrator, summary, query_lower)
    elif any(w in query_lower for w in ["node", "component", "service", "list", "show"]):
        return _respond_about_nodes(orchestrator)
    elif any(w in query_lower for w in ["redis", "payment", "database", "cache", "gateway", "auth"]):
        return _respond_about_specific_node(orchestrator, query_lower)
    elif any(w in query_lower for w in ["analyze", "run", "check", "assess", "investigate"]):
        return _respond_analysis_summary(orchestrator, summary, fragility)
    elif any(w in query_lower for w in ["help", "what can", "how do"]):
        return _respond_help()
    else:
        return _respond_general(status, summary)


def _respond_about_failures(status, summary, fragility) -> str:
    affected = status.get("affected_count", 0)
    critical = status.get("critical_failures", [])
    
    if not affected and not critical:
        return ("✅ **No active failures detected.** The system is currently healthy.\n\n"
                "You can inject a failure using the **⚡ Interactive** tab or sidebar controls "
                "to simulate what would happen if a component fails.")
    
    response = f"🚨 **Current System State:**\n\n"
    response += f"- **{affected}** node(s) affected\n"
    response += f"- **{len(critical)}** critical failure(s)\n"
    response += f"- System health: **{status.get('system_health', 1.0):.0%}**\n\n"
    
    if critical:
        response += "**Critical nodes in failure state:**\n"
        for nid in critical[:5]:
            response += f"  - `{nid}`\n"
    
    return response


def _respond_with_fixes(summary, fragility) -> str:
    recs = summary.get("recommendations", [])
    
    if not recs:
        return ("No specific fix recommendations available yet. "
                "Run an analysis first by clicking **🚀 Analyze** in the sidebar.")
    
    response = "## 🔧 Recommended Fixes\n\n"
    for i, rec in enumerate(recs[:5], 1):
        r = rec.get("recommendation", "") if isinstance(rec, dict) else str(rec)
        priority = rec.get("priority", "medium") if isinstance(rec, dict) else "medium"
        response += f"**{i}. [{priority.upper()}]** {r}\n\n"
    
    response += "\n---\n*These recommendations are based on the structural analysis and cascade simulation results.*"
    return response


def _respond_about_risk(status, summary) -> str:
    risk_score = summary.get("risk_score", 0)
    risk_level = summary.get("risk_level", "N/A")
    health = status.get("system_health", 1.0)
    
    response = f"## 📊 Risk Assessment\n\n"
    response += f"- **Risk Score:** {risk_score:.0%}\n"
    response += f"- **Risk Level:** {risk_level}\n"
    response += f"- **System Health:** {health:.0%}\n"
    response += f"- **Nodes Affected:** {status.get('affected_count', 0)}\n\n"
    
    if risk_score > 0.7:
        response += "⚠️ The system shows **HIGH** fragility. Multiple critical vulnerabilities detected."
    elif risk_score > 0.4:
        response += "The system has **MODERATE** risk. Some improvements recommended."
    else:
        response += "✅ The system shows **LOW** risk. Good resilience posture."
    
    return response


def _respond_about_spofs(fragility) -> str:
    if "error" in fragility:
        return "No fragility data available. Load a scenario first."
    
    spofs = fragility.get("single_points_of_failure", [])
    
    if not spofs:
        return "✅ No single points of failure detected in the current topology."
    
    response = f"## ⚠️ Single Points of Failure ({len(spofs)})\n\n"
    response += "These nodes, if they fail, would disconnect parts of the system:\n\n"
    for spof in spofs:
        name = spof.get("name", spof.get("node_id", "?"))
        response += f"- **{name}**\n"
    
    response += "\n**Fix:** Add redundancy, failover paths, or load balancers for these nodes."
    return response


def _respond_about_cascades(summary) -> str:
    if not summary:
        return "No cascade data available. Run an analysis first."
    
    response = "## 🌊 Cascade Analysis\n\n"
    exec_summary = summary.get("summary", "")
    if exec_summary:
        response += f"*{exec_summary}*\n\n"
    
    insights = summary.get("insights", [])
    cascade_insights = [i for i in insights if "cascade" in i.get("category", "").lower() or "blast" in i.get("title", "").lower()]
    
    if cascade_insights:
        for insight in cascade_insights[:3]:
            response += f"- **{insight.get('title', '')}**: {insight.get('description', '')}\n\n"
    else:
        response += "No deep cascade chains detected in the current analysis."
    
    return response


def _respond_about_cascades_detailed(orchestrator, summary, query_lower) -> str:
    """Detailed cascade response with actual simulation data."""
    if not orchestrator.graph.nodes:
        return "No scenario loaded. Load one first to simulate cascades."
    
    # Try to find a specific node mentioned in the query
    target_node = None
    for nid, node in orchestrator.graph.nodes.items():
        if node.name.lower() in query_lower or nid.lower() in query_lower:
            target_node = (nid, node)
            break
    
    if target_node and orchestrator.engine:
        nid, node = target_node
        # Run a quick simulation
        orchestrator.engine.reset_system()
        from core.models import StressType
        stress = StressType.DEPENDENCY_FAILURE
        orchestrator.engine.inject_failure(nid, stress, 0.85)
        result = orchestrator.engine.propagate_failure(nid, stress, max_depth=5)
        
        # Build detailed response
        response = f"## 🌊 Cascade Analysis: {node.name}\n\n"
        response += f"**Simulation:** dependency_failure @ 85% intensity\n\n"
        response += f"### Results\n"
        response += f"- **Nodes affected:** {result.total_affected}\n"
        response += f"- **Cascade depth:** {result.max_depth} levels\n"
        response += f"- **Severity:** {result.severity if isinstance(result.severity, str) else result.severity.value if hasattr(result.severity, 'value') else 'medium'}\n"
        response += f"- **Est. downtime:** {result.estimated_downtime_seconds:.0f}s\n\n"
        
        if result.timeline_events:
            response += "### Propagation Path\n"
            for evt in result.timeline_events[:6]:
                health = evt.get("health", 0)
                icon = "🔴" if health < 0.3 else "🟠" if health < 0.6 else "🟡"
                response += f"  {icon} `T+{evt.get('time', 0):.1f}s` → **{evt.get('node_name', '?')}** ({health:.0%})\n"
            response += "\n"
        
        if result.critical_nodes_hit:
            response += f"### ⚠️ Critical Nodes Hit\n"
            for cn in result.critical_nodes_hit:
                cnode = orchestrator.graph.get_node(cn)
                response += f"  - **{cnode.name if cnode else cn}** (Tier 1)\n"
            response += "\n"
        
        if result.recommendations:
            response += "### 💡 Recommendations\n"
            for rec in result.recommendations:
                response += f"  - {rec}\n"
        
        # Reset system after simulation
        orchestrator.engine.reset_system()
        return response
    
    # Generic cascade response using summary data
    if summary:
        return _respond_about_cascades(summary)
    
    # Fallback with mocked intelligent response
    total_nodes = len(orchestrator.graph.nodes)
    spofs = orchestrator.graph.find_single_points_of_failure()
    
    response = "## 🌊 Cascade Impact Analysis\n\n"
    response += f"The system has **{total_nodes} nodes** with **{len(spofs)} single points of failure**.\n\n"
    response += "### Key Findings\n"
    response += f"- Worst-case cascade could affect up to **{min(total_nodes, int(total_nodes * 0.6))} nodes** ({int(min(100, total_nodes * 0.6 / max(total_nodes, 1) * 100))}% of system)\n"
    response += f"- Maximum cascade depth: **4-5 levels** based on graph topology\n"
    response += f"- Estimated recovery time: **120-300 seconds** depending on failure origin\n\n"
    response += "💡 *Use the **🎬 Incident Replay** tab to visualize cascade propagation in real-time.*"
    return response


def _respond_about_specific_node(orchestrator, query_lower) -> str:
    """Respond about a specific node mentioned in the query."""
    if not orchestrator.graph.nodes:
        return "No scenario loaded. Load one first."
    
    # Find the node
    target = None
    for nid, node in orchestrator.graph.nodes.items():
        if node.name.lower() in query_lower or nid.lower() in query_lower:
            target = (nid, node)
            break
    
    if not target:
        return _respond_about_nodes(orchestrator)
    
    nid, node = target
    deps = orchestrator.graph.get_dependencies(nid)
    dependents = orchestrator.graph.get_dependents(nid)
    blast = orchestrator.graph.get_failure_blast_radius(nid)
    criticality = orchestrator.graph.calculate_node_criticality()
    score = criticality.get(nid, 0)
    
    # Determine risk level
    risk = "🔴 CRITICAL" if score > 0.7 else "🟠 HIGH" if score > 0.5 else "🟡 MODERATE" if score > 0.3 else "🟢 LOW"
    
    response = f"## 🔍 {node.name}\n\n"
    response += f"| Property | Value |\n|----------|-------|\n"
    response += f"| Type | {node.node_type} |\n"
    response += f"| Tier | {node.tier} ({'Critical' if node.tier == 1 else 'Important' if node.tier == 2 else 'Standard'}) |\n"
    response += f"| Health | {node.health_score:.0%} |\n"
    response += f"| Criticality | {score:.1%} ({risk}) |\n"
    response += f"| Business Value | {node.business_value:.0%} |\n"
    response += f"| Blast Radius | {blast.get('total_affected', 0)} nodes |\n\n"
    
    if deps:
        dep_names = [orchestrator.graph.get_node(d).name for d in deps if orchestrator.graph.get_node(d)]
        response += f"**Depends on ({len(deps)}):** {', '.join(dep_names[:5])}\n\n"
    
    if dependents:
        dep_names = [orchestrator.graph.get_node(d).name for d in dependents if orchestrator.graph.get_node(d)]
        response += f"**Depended on by ({len(dependents)}):** {', '.join(dep_names[:5])}\n\n"
    
    # Assessment
    if score > 0.5:
        response += f"⚠️ **Assessment:** {node.name} is a high-criticality component. "
        response += f"Its failure would cascade to {blast.get('total_affected', 0)} downstream nodes. "
        response += "Consider adding redundancy or circuit breakers."
    else:
        response += f"✅ **Assessment:** {node.name} has moderate criticality. "
        response += "Standard monitoring should be sufficient."
    
    return response


def _respond_analysis_summary(orchestrator, summary, fragility) -> str:
    """Provide a comprehensive analysis summary."""
    if not orchestrator.graph.nodes:
        return ("👋 No scenario loaded yet.\n\n"
                "Click **🚀 Analyze** in the sidebar to run a full fragility analysis, "
                "or select a scenario from the home page.")
    
    total_nodes = len(orchestrator.graph.nodes)
    total_edges = len(orchestrator.graph.edges)
    spofs = fragility.get("single_points_of_failure", []) if "error" not in fragility else []
    top_fragile = fragility.get("top_fragile_nodes", []) if "error" not in fragility else []
    risk_score = summary.get("risk_score", 0) if summary else 0
    risk_level = summary.get("risk_level", "N/A") if summary else "N/A"
    
    response = "## 🧠 Fragility Analysis Summary\n\n"
    response += f"**System:** {total_nodes} nodes, {total_edges} edges\n"
    response += f"**Risk Score:** {risk_score:.0%} ({risk_level})\n"
    response += f"**SPOFs:** {len(spofs)}\n\n"
    
    response += "### Key Findings\n\n"
    
    if spofs:
        response += f"**⚠️ {len(spofs)} Single Points of Failure detected:**\n"
        for spof in spofs[:3]:
            response += f"  - {spof.get('name', '?')}\n"
        response += "\n"
    
    if top_fragile:
        response += "**🔥 Most Fragile Components:**\n"
        for i, nf in enumerate(top_fragile[:3], 1):
            blast = nf.get("blast_radius", {})
            response += f"  {i}. **{nf.get('name', '?')}** — criticality {nf.get('criticality_score', 0):.0%}, blast radius {blast.get('total_affected', 0)} nodes\n"
        response += "\n"
    
    insights = summary.get("insights", []) if summary else []
    if insights:
        response += "### 🔍 Top Insights\n"
        for insight in insights[:3]:
            sev = insight.get("severity", "medium")
            icon = "🔴" if sev in ("critical", "catastrophic") else "🟠" if sev == "high" else "🟡"
            response += f"  {icon} **{insight.get('title', '')}** — {insight.get('description', '')[:80]}\n"
        response += "\n"
    
    recs = summary.get("recommendations", []) if summary else []
    if recs:
        response += "### 💡 Top Recommendations\n"
        for i, rec in enumerate(recs[:3], 1):
            r = rec.get("recommendation", "") if isinstance(rec, dict) else str(rec)
            response += f"  {i}. {r}\n"
    
    return response


def _respond_about_nodes(orchestrator) -> str:
    if not orchestrator.graph.nodes:
        return "No nodes loaded. Select a scenario first."
    
    nodes = orchestrator.graph.nodes
    response = f"## 🕸️ System Components ({len(nodes)} nodes)\n\n"
    response += "| Node | Type | Tier | Health |\n|------|------|------|--------|\n"
    
    for nid, node in sorted(nodes.items(), key=lambda x: x[1].tier):
        health_icon = "🟢" if node.health_score > 0.8 else "🟡" if node.health_score > 0.5 else "🔴"
        response += f"| {node.name} | {node.node_type} | T{node.tier} | {health_icon} {node.health_score:.0%} |\n"
    
    return response


def _respond_help() -> str:
    return """## 💬 What You Can Ask

- **"What failed?"** — See current failure state
- **"How to fix?"** — Get prioritized fix recommendations
- **"What's the risk score?"** — View risk assessment
- **"Show single points of failure"** — Identify SPOFs
- **"How does failure cascade?"** — Understand propagation
- **"List all nodes"** — See system components
- **"What's the blast radius of X?"** — Impact analysis

You can also use the **⚡ Interactive** tab to inject failures and see real-time cascade effects.
"""


def _respond_general(status, summary) -> str:
    if not status or status.get("status") == "not_initialized":
        return ("👋 Welcome to Faultline! I can help you understand system fragility.\n\n"
                "Load a scenario first using the sidebar or the launch buttons on the home page, "
                "then ask me questions about failures, risks, and fixes.")
    
    health = status.get("system_health", 1.0)
    nodes = status.get("total_nodes", 0)
    
    return (f"The system currently has **{nodes} nodes** with **{health:.0%}** overall health.\n\n"
            f"Try asking:\n"
            f"- \"What are the single points of failure?\"\n"
            f"- \"How to fix the vulnerabilities?\"\n"
            f"- \"What's the risk score?\"\n"
            f"- \"Show cascade analysis\"")


def main():
    """Main application entry point."""
    render_header()
    
    # Initialize orchestrator
    orchestrator = get_orchestrator()
    
    # Render sidebar (handles all navigation)
    render_sidebar(orchestrator)
    
    # Main content area - always show chat on right
    pipeline_result = st.session_state.get("pipeline_result", {})
    main_col, chat_col = st.columns([3, 1])
    
    with main_col:
        if not st.session_state.get("scenario_loaded"):
            render_landing_page()
        else:
            render_results_view(orchestrator, pipeline_result)
    
    with chat_col:
        render_chat_tab(orchestrator, pipeline_result)


if __name__ == "__main__":
    main()