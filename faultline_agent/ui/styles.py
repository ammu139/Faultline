"""
Faultline UI Styles
Light theme with Google Material Design colors.
"""

MAIN_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Make sidebar uncollapsable */
    button[kind="header"] {display: none !important;}
    [data-testid="collapsedControl"] {display: none !important;}
    
    /* Header */
    .faultline-header {
        background: linear-gradient(135deg, #4285F4 0%, #34A853 50%, #4285F4 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    
    .faultline-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: white;
        margin: 0;
    }
    
    .faultline-subtitle {
        color: rgba(255,255,255,0.85);
        font-size: 1rem;
        margin-top: 0.3rem;
    }
    
    .faultline-version {
        position: absolute;
        top: 1.2rem;
        right: 1.5rem;
        background: rgba(255,255,255,0.2);
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.7rem;
        color: white;
        font-weight: 600;
    }
    
    /* Metric Cards */
    .metric-card {
        background: #F8F9FA;
        border: 1px solid #E8EAED;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .metric-label {
        font-size: 0.7rem;
        color: #5F6368;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.4rem;
    }
    
    /* Insight Cards */
    .insight-card {
        background: #F8F9FA;
        border-left: 4px solid #4285F4;
        border-radius: 0 8px 8px 0;
        padding: 1rem;
        margin-bottom: 0.8rem;
    }
    .insight-card.critical { border-left-color: #EA4335; }
    .insight-card.catastrophic { border-left-color: #EA4335; }
    .insight-card.high { border-left-color: #F9AB00; }
    .insight-card.medium { border-left-color: #FBBC04; }
    .insight-card.low { border-left-color: #34A853; }
    
    .insight-title { font-weight: 600; color: #202124; margin-bottom: 0.3rem; }
    .insight-description { color: #5F6368; font-size: 0.85rem; }
    
    /* Scenario Cards */
    .scenario-card {
        background: #F8F9FA;
        border: 1px solid #E8EAED;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        min-height: 160px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    .scenario-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
    .scenario-name { font-size: 1.1rem; font-weight: 600; color: #202124; }
    .scenario-desc { color: #5F6368; font-size: 0.82rem; margin-top: 0.3rem; }
    
    /* Risk Gauge */
    .risk-gauge {
        text-align: center;
        padding: 1.5rem;
        background: #F8F9FA;
        border-radius: 12px;
    }
    .risk-score { font-size: 3.5rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    
    /* Pipeline Steps */
    .pipeline-step {
        display: inline-flex;
        background: #E8F0FE;
        border: 1px solid #4285F4;
        border-radius: 20px;
        padding: 0.4rem 0.8rem;
        margin: 0.2rem;
        font-size: 0.75rem;
        color: #4285F4;
        font-weight: 500;
    }
    .pipeline-step.active { background: #4285F4; color: white; }
    .pipeline-arrow { color: #9AA0A6; margin: 0 0.3rem; }
    
    /* Stat Chips */
    .stat-chip {
        background: #E8F0FE;
        border: 1px solid #4285F4;
        border-radius: 20px;
        padding: 0.3rem 0.8rem;
        font-size: 0.78rem;
        color: #4285F4;
        font-weight: 500;
        display: inline-block;
        margin-right: 0.5rem;
    }
    
    /* Hide branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""


def get_status_color(status: str) -> str:
    """Get color for a node status (Google Material Design)."""
    colors = {
        "healthy": "#34A853",
        "stressed": "#FBBC04",
        "degraded": "#F9AB00",
        "failing": "#EA4335",
        "dead": "#C5221F",
        "recovering": "#4285F4",
        "unknown": "#9AA0A6",
    }
    return colors.get(status, "#9AA0A6")


def get_severity_color(severity: str) -> str:
    """Get color for a severity level (Google Material Design)."""
    colors = {
        "negligible": "#9AA0A6",
        "low": "#34A853",
        "medium": "#FBBC04",
        "high": "#F9AB00",
        "critical": "#EA4335",
        "catastrophic": "#C5221F",
    }
    return colors.get(severity, "#9AA0A6")


def get_risk_class(level: str) -> str:
    return f"risk-{level.lower()}"