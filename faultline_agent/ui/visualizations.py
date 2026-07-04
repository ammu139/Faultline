"""
Faultline Visualizations
Plotly-based graph visualizations and animated charts.
"""

from __future__ import annotations
from typing import Any, Optional
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from ui.styles import get_status_color, get_severity_color


def create_dependency_graph(
    nodes: dict[str, dict],
    edges: list[dict],
    layout: dict[str, tuple[float, float]],
    title: str = "System Dependency Graph",
) -> go.Figure:
    """Create an interactive dependency graph visualization."""
    
    # Create edge traces
    edge_x = []
    edge_y = []
    edge_colors = []
    
    for edge in edges:
        source = edge.get("source", "")
        target = edge.get("target", "")
        
        if source in layout and target in layout:
            x0, y0 = layout[source]
            x1, y1 = layout[target]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1, color='rgba(88, 166, 255, 0.3)'),
        hoverinfo='none',
        mode='lines',
    )
    
    # Create node traces
    node_x = []
    node_y = []
    node_colors = []
    node_sizes = []
    node_text = []
    node_hover = []
    
    for node_id, node_data in nodes.items():
        if node_id in layout:
            x, y = layout[node_id]
            node_x.append(x)
            node_y.append(y)
            
            status = node_data.get("status", "healthy")
            health = node_data.get("health", 1.0)
            name = node_data.get("name", node_id)
            tier = node_data.get("tier", 2)
            
            node_colors.append(get_status_color(status))
            node_sizes.append(max(15, 35 - tier * 5))
            node_text.append(name)
            node_hover.append(
                f"<b>{name}</b><br>"
                f"Status: {status}<br>"
                f"Health: {health:.0%}<br>"
                f"Tier: {tier}<br>"
                f"Type: {node_data.get('type', 'unknown')}"
            )
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        hovertext=node_hover,
        text=node_text,
        textposition="top center",
        textfont=dict(size=9, color='#8b949e'),
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color='rgba(255,255,255,0.2)'),
            opacity=0.9,
        ),
    )
    
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=dict(text=title, font=dict(color='#E6EDF3', size=16)),
            showlegend=False,
            hovermode='closest',
            paper_bgcolor='#0D1117',
            plot_bgcolor='#0D1117',
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            margin=dict(l=20, r=20, t=50, b=20),
            height=500,
        )
    )
    
    return fig


def create_health_timeline(
    snapshots: list[dict],
    title: str = "System Health Over Time",
) -> go.Figure:
    """Create an animated health timeline chart."""
    
    if not snapshots:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor='#0D1117',
            plot_bgcolor='#161B22',
            title=dict(text="No data yet", font=dict(color='#8b949e')),
        )
        return fig
    
    steps = [s.get("step", i) for i, s in enumerate(snapshots)]
    health_scores = [s.get("system_health", 1.0) for s in snapshots]
    affected_counts = [s.get("active_failures", 0) for s in snapshots]
    
    fig = go.Figure()
    
    # Health score line
    fig.add_trace(go.Scatter(
        x=steps, y=health_scores,
        mode='lines+markers',
        name='System Health',
        line=dict(color='#00E676', width=2),
        marker=dict(size=4),
        fill='tozeroy',
        fillcolor='rgba(0, 230, 118, 0.1)',
    ))
    
    # Affected nodes
    fig.add_trace(go.Scatter(
        x=steps, y=[a / max(max(affected_counts, default=1), 1) for a in affected_counts],
        mode='lines',
        name='Failure Intensity',
        line=dict(color='#FF6B6B', width=2, dash='dot'),
        yaxis='y2',
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(color='#E6EDF3', size=14)),
        paper_bgcolor='#0D1117',
        plot_bgcolor='#161B22',
        xaxis=dict(
            title='Simulation Step',
            gridcolor='#21262d',
            color='#8b949e',
        ),
        yaxis=dict(
            title='Health Score',
            range=[0, 1.1],
            gridcolor='#21262d',
            color='#8b949e',
        ),
        yaxis2=dict(
            title='Failure Intensity',
            overlaying='y',
            side='right',
            range=[0, 1.1],
            color='#8b949e',
        ),
        legend=dict(
            font=dict(color='#8b949e'),
            bgcolor='rgba(0,0,0,0)',
        ),
        margin=dict(l=50, r=50, t=50, b=40),
        height=300,
    )
    
    return fig


def create_cascade_animation(
    timeline_events: list[dict],
    nodes: dict[str, dict],
    layout: dict[str, tuple[float, float]],
) -> go.Figure:
    """Create an animated cascade propagation visualization."""
    
    if not timeline_events:
        return create_dependency_graph(nodes, [], layout, "No cascade data")
    
    # Sort events by time
    sorted_events = sorted(timeline_events, key=lambda x: x.get("time", 0))
    
    # Create frames for animation
    frames = []
    affected_so_far = set()
    
    for i, event in enumerate(sorted_events):
        node_id = event.get("node", "")
        affected_so_far.add(node_id)
        
        node_x = []
        node_y = []
        node_colors = []
        node_sizes = []
        
        for nid, ndata in nodes.items():
            if nid in layout:
                x, y = layout[nid]
                node_x.append(x)
                node_y.append(y)
                
                if nid in affected_so_far:
                    node_colors.append('#FF1744')
                    node_sizes.append(25)
                else:
                    node_colors.append(get_status_color(ndata.get("status", "healthy")))
                    node_sizes.append(15)
        
        frames.append(go.Frame(
            data=[go.Scatter(
                x=node_x, y=node_y,
                mode='markers',
                marker=dict(size=node_sizes, color=node_colors),
            )],
            name=f"step_{i}",
        ))
    
    # Initial figure
    fig = create_dependency_graph(nodes, [], layout, "Cascade Propagation")
    fig.frames = frames
    
    # Add animation controls
    fig.update_layout(
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            y=0,
            x=0.5,
            xanchor="center",
            buttons=[
                dict(label="▶ Play",
                     method="animate",
                     args=[None, {"frame": {"duration": 500}, "fromcurrent": True}]),
                dict(label="⏸ Pause",
                     method="animate",
                     args=[[None], {"frame": {"duration": 0}, "mode": "immediate"}]),
            ],
        )],
    )
    
    return fig


def create_risk_heatmap(
    criticality_scores: dict[str, float],
    nodes: dict[str, dict],
) -> go.Figure:
    """Create a risk heatmap showing node criticality."""
    
    if not criticality_scores:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor='#0D1117', plot_bgcolor='#161B22')
        return fig
    
    # Sort by criticality
    sorted_nodes = sorted(criticality_scores.items(), key=lambda x: x[1], reverse=True)
    
    names = []
    scores = []
    colors = []
    
    for node_id, score in sorted_nodes[:15]:
        node_data = nodes.get(node_id, {})
        name = node_data.get("name", node_id)
        names.append(name)
        scores.append(score)
        
        if score > 0.7:
            colors.append('#FF1744')
        elif score > 0.5:
            colors.append('#FF9100')
        elif score > 0.3:
            colors.append('#FFD600')
        else:
            colors.append('#00E676')
    
    fig = go.Figure(go.Bar(
        x=scores,
        y=names,
        orientation='h',
        marker=dict(color=colors, opacity=0.85),
        text=[f"{s:.0%}" for s in scores],
        textposition='outside',
        textfont=dict(color='#8b949e'),
    ))
    
    fig.update_layout(
        title=dict(text="Node Criticality Ranking", font=dict(color='#E6EDF3', size=14)),
        paper_bgcolor='#0D1117',
        plot_bgcolor='#161B22',
        xaxis=dict(
            title='Criticality Score',
            range=[0, 1.1],
            gridcolor='#21262d',
            color='#8b949e',
        ),
        yaxis=dict(
            color='#8b949e',
            autorange='reversed',
        ),
        margin=dict(l=150, r=50, t=50, b=40),
        height=400,
    )
    
    return fig


def create_blast_radius_chart(
    blast_data: dict[str, Any],
    nodes: dict[str, dict],
) -> go.Figure:
    """Create a blast radius visualization."""
    
    affected = blast_data.get("affected_nodes", [])
    waves = blast_data.get("cascade_waves", [])
    
    if not waves:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor='#0D1117', plot_bgcolor='#161B22')
        return fig
    
    # Create sunburst-like visualization
    labels = ["Source"]
    parents = [""]
    values = [1]
    colors_list = ["#FF1744"]
    
    source_name = nodes.get(blast_data.get("source", ""), {}).get("name", "Source")
    labels[0] = source_name
    
    for depth, wave in enumerate(waves):
        for node_id in wave:
            node_name = nodes.get(node_id, {}).get("name", node_id)
            labels.append(node_name)
            parents.append(source_name if depth == 0 else labels[len(labels) - len(wave) - 1])
            values.append(1)
            
            intensity = 1.0 - (depth * 0.2)
            if intensity > 0.7:
                colors_list.append('#FF6B6B')
            elif intensity > 0.4:
                colors_list.append('#FF9100')
            else:
                colors_list.append('#FFD600')
    
    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(colors=colors_list),
        textfont=dict(color='white'),
    ))
    
    fig.update_layout(
        title=dict(
            text=f"Blast Radius: {len(affected)} nodes affected",
            font=dict(color='#E6EDF3', size=14),
        ),
        paper_bgcolor='#0D1117',
        margin=dict(l=10, r=10, t=50, b=10),
        height=350,
    )
    
    return fig


def create_severity_distribution(results: list[dict]) -> go.Figure:
    """Create a severity distribution pie chart."""
    
    severity_counts = {}
    for r in results:
        sev = r.get("worst_severity", "medium")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    
    if not severity_counts:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor='#0D1117')
        return fig
    
    labels = list(severity_counts.keys())
    values = list(severity_counts.values())
    colors = [get_severity_color(s) for s in labels]
    
    fig = go.Figure(go.Pie(
        labels=[s.title() for s in labels],
        values=values,
        marker=dict(colors=colors),
        textfont=dict(color='white'),
        hole=0.4,
    ))
    
    fig.update_layout(
        title=dict(text="Severity Distribution", font=dict(color='#E6EDF3', size=14)),
        paper_bgcolor='#0D1117',
        legend=dict(font=dict(color='#8b949e')),
        margin=dict(l=20, r=20, t=50, b=20),
        height=300,
    )
    
    return fig