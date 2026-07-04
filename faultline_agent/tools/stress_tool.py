"""
Stress Tool
Provides stress testing capabilities for agents.
"""

from __future__ import annotations
from typing import Any
from core.models import StressType


class StressTool:
    """Tool for designing and applying stress conditions."""
    
    @staticmethod
    def get_stress_types() -> list[dict[str, str]]:
        """Get all available stress types with descriptions."""
        descriptions = {
            StressType.LOAD_SPIKE: "Sudden increase in traffic/requests beyond capacity",
            StressType.LATENCY: "Network or processing delays exceeding thresholds",
            StressType.MEMORY_PRESSURE: "Memory exhaustion causing OOM conditions",
            StressType.DISK_FULL: "Storage capacity exhausted, writes failing",
            StressType.NETWORK_PARTITION: "Network split isolating components",
            StressType.DEPENDENCY_FAILURE: "Upstream service becomes unavailable",
            StressType.DATA_CORRUPTION: "Data integrity violations detected",
            StressType.SECURITY_BREACH: "Security incident compromising a component",
            StressType.EXTERNAL_OUTAGE: "Third-party service outage",
            StressType.NATURAL_DISASTER: "Physical infrastructure damage",
            StressType.HUMAN_ERROR: "Misconfiguration or operational mistake",
            StressType.CASCADING_FAILURE: "Failure propagating from another component",
        }
        
        return [
            {"type": st.value, "description": descriptions.get(st, "")}
            for st in StressType
        ]
    
    @staticmethod
    def calculate_stress_intensity(
        base_load: float,
        capacity: float,
        spike_factor: float = 2.0,
    ) -> float:
        """Calculate stress intensity based on load parameters."""
        if capacity <= 0:
            return 1.0
        
        stressed_load = base_load * spike_factor
        intensity = min(1.0, stressed_load / capacity)
        return intensity
    
    @staticmethod
    def recommend_stress_type(node_type: str) -> list[str]:
        """Recommend appropriate stress types for a given node type."""
        recommendations = {
            "service": ["load_spike", "latency", "memory_pressure"],
            "database": ["disk_full", "latency", "data_corruption"],
            "api": ["load_spike", "latency", "dependency_failure"],
            "queue": ["memory_pressure", "load_spike", "disk_full"],
            "cache": ["memory_pressure", "network_partition", "latency"],
            "gateway": ["network_partition", "load_spike", "latency"],
            "external": ["external_outage", "latency", "network_partition"],
            "payment": ["latency", "security_breach", "dependency_failure"],
            "auth": ["security_breach", "load_spike", "dependency_failure"],
            "cdn": ["network_partition", "external_outage", "load_spike"],
            "load_balancer": ["load_spike", "network_partition", "latency"],
            "monitoring": ["dependency_failure", "network_partition", "disk_full"],
            "network": ["network_partition", "latency", "natural_disaster"],
            "human": ["human_error", "security_breach"],
            "process": ["human_error", "dependency_failure"],
        }
        
        return recommendations.get(node_type, ["load_spike", "latency"])
    
    @staticmethod
    def build_stress_config(
        node_id: str,
        stress_type: str,
        intensity: float = 0.8,
        duration_seconds: float = 60.0,
    ) -> dict[str, Any]:
        """Build a stress configuration object."""
        return {
            "node_id": node_id,
            "stress_type": stress_type,
            "intensity": max(0.0, min(1.0, intensity)),
            "duration_seconds": duration_seconds,
            "max_depth": 5,
        }