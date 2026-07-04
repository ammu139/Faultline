"""
Faultline Incident Replay Visualization
The "hero" feature — an animated cascade visualization showing failure
propagation in real-time with live event log, KPI ribbon, and controls.

Design: This creates a cinematic incident replay experience that makes
the underlying graph theory and simulation immediately intuitive.
"""

from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
import time
from typing import Any

from ui.styles import get_status_color


def render_incident_replay(orchestrator, scenario_name: str = ""):
    """
    Render the animated incident replay dashboard.
    Shows cascade propagation step-by-step with synchronized:
    - Dependency graph (nodes light up as cascade spreads)
    - Live event log (explains each step)
    - KPI ribbon (metrics update in real-time)
    - Simulation controls (play/pause/speed)
    """
    st.markdown("### 🎬 Incident Replay")
    st.markdown("*Watch failure cascade through the system in real-time*")

    if not orchestrator.graph.nodes:
        st.info("Load a scenario and run analysis first.")
        return

    # ─── Simulation Controls ─────────────────────────────────────────────
    ctrl_cols = st.columns([1, 1, 1, 1, 2, 2, 2])
    with ctrl_cols[0]:
        play = st.button("▶ Play", use_container_width=True, type="primary")
    with ctrl_cols[1]:
        pause = st.button("⏸ Pause", use_container_width=True)
    with ctrl_cols[2]:
        reset = st.button("⏮ Reset", use_container_width=True)
    with ctrl_cols[3]:
        step_btn = st.button("⏭ Step", use_container_width=True)
    with ctrl_cols[4]:
        target_node = st.selectbox(
            "Failure Target",
            options=list(orchestrator.graph.nodes.keys()),
            format_func=lambda x: orchestrator.graph.nodes[x].name if x in orchestrator.graph.nodes else x,
        )
    with ctrl_cols[5]:
        from core.models import StressType as _ST
        _stress_options = [s.value for s in _ST]
        replay_stress_type = st.selectbox(
            "Stress Type",
            options=_stress_options,
            format_func=lambda x: x.replace("_", " ").title(),
            index=5,  # dependency_failure
        )
    with ctrl_cols[6]:
        speed = st.select_slider("Speed", options=["0.5x", "1x", "2x", "4x"], value="1x")

    speed_map = {"0.5x": 2.0, "1x": 1.0, "2x": 0.5, "4x": 0.25}
    delay = speed_map.get(speed, 1.0)

    # ─── Initialize replay state ─────────────────────────────────────────
    if "replay_step" not in st.session_state:
        st.session_state.replay_step = 0
        st.session_state.replay_events = []
        st.session_state.replay_running = False
        st.session_state.replay_node_states = {}
        st.session_state.replay_kpis = {
            "health": 100, "affected": 0, "risk": 0, "revenue_loss": 0
        }

    if reset:
        st.session_state.replay_step = 0
        st.session_state.replay_events = []
        st.session_state.replay_running = False
        st.session_state.replay_node_states = {
            nid: {"status": "healthy", "health": 1.0}
            for nid in orchestrator.graph.nodes
        }
        st.session_state.replay_kpis = {
            "health": 100, "affected": 0, "risk": 0, "revenue_loss": 0
        }
        st.rerun()

    if pause:
        st.session_state.replay_running = False

    # ─── Run simulation on Play ──────────────────────────────────────────
    if play and target_node and orchestrator.engine:
        st.session_state.replay_running = True
        st.session_state.replay_step = 0
        st.session_state.replay_events = []

        # Reset engine and run propagation to capture timeline
        orchestrator.engine.reset_system()
        from core.models import StressType
        stress = StressType(replay_stress_type)
        orchestrator.engine.inject_failure(target_node, stress, 0.85)
        result = orchestrator.engine.propagate_failure(target_node, stress, max_depth=6)

        # Build replay timeline from propagation result
        source_node = orchestrator.graph.get_node(target_node)
        events = [{
            "step": 0,
            "time": "T+0.0s",
            "node_id": target_node,
            "node_name": source_node.name if source_node else target_node,
            "status": "failing",
            "health": 0.2,
            "description": f"🔴 {source_node.name if source_node else target_node} — FAILURE INJECTED",
            "severity": "critical",
        }]

        for evt in result.timeline_events:
            events.append({
                "step": len(events),
                "time": f"T+{evt.get('time', 0):.1f}s",
                "node_id": evt.get("node", ""),
                "node_name": evt.get("node_name", ""),
                "status": evt.get("status", "degraded"),
                "health": evt.get("health", 0.5),
                "description": f"{'🔴' if evt.get('health', 1) < 0.3 else '🟠' if evt.get('health', 1) < 0.6 else '🟡'} {evt.get('node_name', '?')} — health {evt.get('health', 0):.0%} (depth {evt.get('depth', 0)})",
                "severity": "critical" if evt.get("health", 1) < 0.3 else "high" if evt.get("health", 1) < 0.6 else "medium",
            })

        # Add recovery event
        events.append({
            "step": len(events),
            "time": f"T+{result.estimated_downtime_seconds:.0f}s",
            "node_id": "",
            "node_name": "System",
            "status": "recovering",
            "health": 0.6,
            "description": f"🟦 Recovery initiated — estimated {result.estimated_downtime_seconds:.0f}s to restore",
            "severity": "medium",
        })

        st.session_state.replay_events = events
        st.session_state.replay_node_states = {
            nid: {"status": "healthy", "health": 1.0}
            for nid in orchestrator.graph.nodes
        }
        st.session_state.replay_propagation_result = {
            "total_affected": result.total_affected,
            "max_depth": result.max_depth,
            "severity": result.severity if isinstance(result.severity, str) else result.severity.value if hasattr(result.severity, 'value') else str(result.severity),
            "downtime": result.estimated_downtime_seconds,
            "recommendations": result.recommendations,
        }

    # ─── Step through animation ──────────────────────────────────────────
    if step_btn and st.session_state.replay_events:
        if st.session_state.replay_step < len(st.session_state.replay_events):
            st.session_state.replay_step += 1

    # Apply events up to current step
    current_step = st.session_state.replay_step
    events = st.session_state.replay_events
    visible_events = events[:current_step] if events else []

    # Update node states based on visible events
    node_states = {
        nid: {"status": "healthy", "health": 1.0}
        for nid in orchestrator.graph.nodes
    }
    for evt in visible_events:
        nid = evt.get("node_id", "")
        if nid and nid in node_states:
            node_states[nid] = {
                "status": evt.get("status", "healthy"),
                "health": evt.get("health", 1.0),
            }

    # Calculate KPIs
    affected_count = sum(1 for s in node_states.values() if s["status"] != "healthy")
    avg_health = sum(s["health"] for s in node_states.values()) / max(len(node_states), 1)
    risk_pct = min(100, int((1 - avg_health) * 100 * 1.5))
    revenue_loss = affected_count * 2.1  # $K/min estimate

    # ─── KPI Ribbon ──────────────────────────────────────────────────────
    st.markdown("")
    kpi_cols = st.columns(5)

    health_color = "#34A853" if avg_health > 0.8 else "#FBBC04" if avg_health > 0.5 else "#EA4335"
    with kpi_cols[0]:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {health_color}">{avg_health:.0%}</div>
                <div class="metric-label">System Health</div>
            </div>
        """, unsafe_allow_html=True)
    with kpi_cols[1]:
        aff_color = "#34A853" if affected_count == 0 else "#F9AB00" if affected_count < 5 else "#EA4335"
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {aff_color}">{affected_count}</div>
                <div class="metric-label">Nodes Affected</div>
            </div>
        """, unsafe_allow_html=True)
    with kpi_cols[2]:
        risk_color = "#34A853" if risk_pct < 30 else "#FBBC04" if risk_pct < 60 else "#EA4335"
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {risk_color}">{risk_pct}%</div>
                <div class="metric-label">Risk Score</div>
            </div>
        """, unsafe_allow_html=True)
    with kpi_cols[3]:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #EA4335">${revenue_loss:.1f}K</div>
                <div class="metric-label">Revenue Loss/min</div>
            </div>
        """, unsafe_allow_html=True)
    with kpi_cols[4]:
        prop_result = st.session_state.get("replay_propagation_result", {})
        depth = prop_result.get("max_depth", 0) if current_step > 0 else 0
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{min(current_step, depth)}</div>
                <div class="metric-label">Cascade Depth</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # ─── Main Layout: Graph + Event Log ──────────────────────────────────
    graph_col, log_col = st.columns([3, 2])

    with graph_col:
        # Render animated dependency graph
        fig = _create_animated_graph(orchestrator, node_states)
        st.plotly_chart(fig, use_container_width=True, key="replay_graph")

    with log_col:
        st.markdown("#### 📋 Live Event Log")

        # Progress bar
        total_events = len(events)
        if total_events > 0:
            progress = current_step / total_events
            st.progress(progress, text=f"Step {current_step}/{total_events}")

        # Event log (scrollable)
        if visible_events:
            for evt in reversed(visible_events[-8:]):
                severity = evt.get("severity", "medium")
                border_color = "#EA4335" if severity == "critical" else "#F9AB00" if severity == "high" else "#FBBC04"
                st.markdown(f"""
                    <div style="padding: 0.5rem 0.8rem; margin-bottom: 0.4rem; 
                                border-left: 3px solid {border_color}; 
                                background: #F8F9FA; border-radius: 0 6px 6px 0;">
                        <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #5F6368;">
                            {evt.get('time', '')}
                        </span><br>
                        <span style="font-size: 0.85rem; color: #202124;">
                            {evt.get('description', '')}
                        </span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("*Press ▶ Play to start the incident replay*")

        # Recommendations (show after replay completes)
        if current_step >= total_events and total_events > 0:
            st.markdown("---")
            st.markdown("#### 💡 Recommendations")
            prop_result = st.session_state.get("replay_propagation_result", {})
            recs = prop_result.get("recommendations", [])
            for i, rec in enumerate(recs[:4], 1):
                st.markdown(f"**{i}.** {rec}")

    # ─── Auto-advance if running ─────────────────────────────────────────
    if st.session_state.replay_running and current_step < len(events):
        time.sleep(delay)
        st.session_state.replay_step += 1
        st.rerun()
    elif st.session_state.replay_running and current_step >= len(events):
        st.session_state.replay_running = False


def _create_animated_graph(orchestrator, node_states: dict) -> go.Figure:
    """Create the dependency graph with animated node states showing cascade propagation."""
    graph = orchestrator.graph
    layout = graph.get_layout("spring")

    # Build edge traces — color edges based on whether connected nodes are affected
    edge_x, edge_y, edge_colors_x, edge_colors_y = [], [], [], []
    affected_edge_x, affected_edge_y = [], []

    for edge in graph.edges.values():
        src = edge.source_id
        tgt = edge.target_id
        if src in layout and tgt in layout:
            x0, y0 = layout[src]
            x1, y1 = layout[tgt]

            src_state = node_states.get(src, {}).get("status", "healthy")
            tgt_state = node_states.get(tgt, {}).get("status", "healthy")

            if src_state != "healthy" and tgt_state != "healthy":
                # Both affected — highlight edge (propagation path)
                affected_edge_x.extend([x0, x1, None])
                affected_edge_y.extend([y0, y1, None])
            else:
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

    # Normal edges (grey)
    traces = []
    if edge_x:
        traces.append(go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=1, color='rgba(154, 160, 166, 0.3)'),
            hoverinfo='none', mode='lines', showlegend=False,
        ))

    # Affected edges (red/orange glow)
    if affected_edge_x:
        traces.append(go.Scatter(
            x=affected_edge_x, y=affected_edge_y,
            line=dict(width=3, color='rgba(234, 67, 53, 0.7)'),
            hoverinfo='none', mode='lines', showlegend=False,
        ))

    # Build node traces
    node_x, node_y, colors, sizes, texts, hovers = [], [], [], [], [], []

    for nid, node in graph.nodes.items():
        if nid not in layout:
            continue
        x, y = layout[nid]
        node_x.append(x)
        node_y.append(y)

        state = node_states.get(nid, {})
        status = state.get("status", "healthy")
        health = state.get("health", 1.0)

        # Color based on current state
        color = get_status_color(status)
        colors.append(color)

        # Size: larger for affected nodes (visual emphasis)
        base_size = max(15, 35 - node.tier * 5)
        if status in ("failing", "dead"):
            sizes.append(base_size + 12)  # Pulsing effect via larger size
        elif status in ("stressed", "degraded"):
            sizes.append(base_size + 6)
        else:
            sizes.append(base_size)

        texts.append(node.name)
        hovers.append(
            f"<b>{node.name}</b><br>"
            f"Status: {status.upper()}<br>"
            f"Health: {health:.0%}<br>"
            f"Tier: {node.tier}<br>"
            f"Type: {node.node_type}"
        )

    # Node trace with marker styling
    traces.append(go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        hovertext=hovers,
        text=texts,
        textposition="top center",
        textfont=dict(size=9, color="#202124"),
        marker=dict(
            size=sizes,
            color=colors,
            line=dict(
                width=[3 if node_states.get(nid, {}).get("status", "healthy") != "healthy" else 1
                       for nid in graph.nodes if nid in layout],
                color=[
                    "rgba(234, 67, 53, 0.8)" if node_states.get(nid, {}).get("status", "healthy") in ("failing", "dead")
                    else "rgba(249, 171, 0, 0.6)" if node_states.get(nid, {}).get("status", "healthy") in ("stressed", "degraded")
                    else "rgba(154, 160, 166, 0.3)"
                    for nid in graph.nodes if nid in layout
                ],
            ),
            opacity=[
                1.0 if node_states.get(nid, {}).get("status", "healthy") != "healthy" else 0.7
                for nid in graph.nodes if nid in layout
            ],
        ),
        showlegend=False,
    ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        showlegend=False,
        hovermode='closest',
        margin=dict(l=0, r=0, t=30, b=0),
        height=450,
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        title=dict(text="Dependency Graph — Cascade Propagation", font=dict(size=14, color="#202124")),
    )

    return fig