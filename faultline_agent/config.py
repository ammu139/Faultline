"""
Faultline Configuration Module
Centralized configuration management for the system fragility intelligence agent.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).parent


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    api_key: str = Field(default="")
    model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o"))
    temperature: float = Field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.3")))
    simulation_mode: bool = Field(
        default_factory=lambda: os.getenv("SIMULATION_MODE", "true").lower() == "true"
    )


class GraphConfig(BaseModel):
    """Graph engine configuration."""
    max_nodes: int = Field(default_factory=lambda: int(os.getenv("MAX_GRAPH_NODES", "200")))
    default_propagation_depth: int = Field(
        default_factory=lambda: int(os.getenv("DEFAULT_PROPAGATION_DEPTH", "5"))
    )
    layout_algorithm: str = "spring"
    edge_weight_default: float = 0.5


class SimulationConfig(BaseModel):
    """Simulation engine configuration."""
    default_speed: float = Field(
        default_factory=lambda: float(os.getenv("DEFAULT_SIMULATION_SPEED", "1.0"))
    )
    max_cascade_steps: int = Field(
        default_factory=lambda: int(os.getenv("MAX_CASCADE_STEPS", "50"))
    )
    failure_threshold: float = 0.7
    recovery_rate: float = 0.1
    external_shock_probability: float = 0.05
    time_step_seconds: float = 1.0


class UIConfig(BaseModel):
    """UI configuration."""
    theme: str = "dark"
    animation_fps: int = 30
    graph_height: int = 600
    sidebar_width: int = 300
    color_scheme: dict = Field(default_factory=lambda: {
        "healthy": "#00E676",
        "stressed": "#FFD600",
        "degraded": "#FF9100",
        "failing": "#FF1744",
        "dead": "#B71C1C",
        "recovering": "#00B0FF",
        "unknown": "#757575",
        "background": "#0D1117",
        "surface": "#161B22",
        "text": "#E6EDF3",
        "accent": "#58A6FF",
    })


class AppConfig(BaseModel):
    """Main application configuration."""
    app_name: str = "Faultline"
    app_subtitle: str = "System Fragility Intelligence Agent"
    version: str = "1.0.0"
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    
    llm: LLMConfig = Field(default_factory=LLMConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    ui: UIConfig = Field(default_factory=UIConfig)


# Global configuration instance
config = AppConfig()


# Scenario registry
AVAILABLE_SCENARIOS = {
    "ecommerce": {
        "name": "E-Commerce Platform",
        "description": "Checkout software collapse simulation",
        "icon": "🛒",
        "complexity": "high",
    },
    "banking": {
        "name": "Banking System",
        "description": "Transaction and fraud cascade analysis",
        "icon": "🏦",
        "complexity": "critical",
    },
    "cicd": {
        "name": "Software Ops / CI-CD",
        "description": "Microservices and CI/CD fragility mapping",
        "icon": "⚙️",
        "complexity": "high",
    },
}

# Node type definitions
NODE_TYPES = {
    "service": {"icon": "🔧", "base_resilience": 0.7},
    "database": {"icon": "🗄️", "base_resilience": 0.8},
    "api": {"icon": "🔌", "base_resilience": 0.6},
    "queue": {"icon": "📬", "base_resilience": 0.75},
    "cache": {"icon": "⚡", "base_resilience": 0.65},
    "gateway": {"icon": "🚪", "base_resilience": 0.7},
    "external": {"icon": "🌐", "base_resilience": 0.4},
    "payment": {"icon": "💳", "base_resilience": 0.85},
    "auth": {"icon": "🔐", "base_resilience": 0.8},
    "cdn": {"icon": "📡", "base_resilience": 0.7},
    "load_balancer": {"icon": "⚖️", "base_resilience": 0.75},
    "monitoring": {"icon": "📊", "base_resilience": 0.6},
    "network": {"icon": "🌐", "base_resilience": 0.5},
    "human": {"icon": "👤", "base_resilience": 0.3},
    "process": {"icon": "📋", "base_resilience": 0.5},
}

# Edge relationship types
EDGE_TYPES = {
    "depends_on": {"weight": 0.8, "color": "#FF6B6B"},
    "calls": {"weight": 0.6, "color": "#4ECDC4"},
    "reads_from": {"weight": 0.5, "color": "#45B7D1"},
    "writes_to": {"weight": 0.7, "color": "#96CEB4"},
    "authenticates_via": {"weight": 0.9, "color": "#FFEAA7"},
    "routes_through": {"weight": 0.7, "color": "#DDA0DD"},
    "monitors": {"weight": 0.3, "color": "#98D8C8"},
    "triggers": {"weight": 0.6, "color": "#F7DC6F"},
    "fallback_to": {"weight": 0.4, "color": "#82E0AA"},
}