"""
Custom Scenario Builder
Allows dynamic creation of scenarios at runtime without code changes.

Supports 3 input methods:
1. Structured dict/JSON input — Parse a JSON description into a full scenario
2. Template-based generation — Parameterized templates for common architectures
3. Interactive node/edge addition — Build incrementally via UI or API

Design: Converts any user-provided system description into a valid ScenarioConfig
that can be immediately analyzed by the multi-agent pipeline.
"""

from typing import Any, Optional
from core.models import SystemNode, SystemEdge, ScenarioConfig
from config import NODE_TYPES


# ============================================================================
# TEMPLATES: Parameterized architecture patterns
# ============================================================================

TEMPLATES = {
    "microservices": {
        "name": "Microservices Architecture",
        "description": "N microservices with shared database, cache, and message queue",
        "icon": "🔧",
        "parameters": {
            "num_services": {"type": "int", "default": 5, "min": 2, "max": 20, "label": "Number of Services"},
            "num_databases": {"type": "int", "default": 2, "min": 1, "max": 5, "label": "Number of Databases"},
            "has_cache": {"type": "bool", "default": True, "label": "Include Cache Layer"},
            "has_queue": {"type": "bool", "default": True, "label": "Include Message Queue"},
            "has_gateway": {"type": "bool", "default": True, "label": "Include API Gateway"},
            "external_apis": {"type": "int", "default": 2, "min": 0, "max": 5, "label": "External API Dependencies"},
        },
    },
    "monolith": {
        "name": "Monolith + Database",
        "description": "Traditional monolithic application with primary/replica databases",
        "icon": "🏢",
        "parameters": {
            "has_replica": {"type": "bool", "default": True, "label": "Database Replica"},
            "has_cache": {"type": "bool", "default": True, "label": "Cache Layer"},
            "has_cdn": {"type": "bool", "default": True, "label": "CDN"},
            "has_queue": {"type": "bool", "default": False, "label": "Background Job Queue"},
            "external_apis": {"type": "int", "default": 1, "min": 0, "max": 3, "label": "External APIs"},
        },
    },
    "event_driven": {
        "name": "Event-Driven Architecture",
        "description": "Event sourcing with multiple consumers and producers",
        "icon": "📨",
        "parameters": {
            "num_producers": {"type": "int", "default": 3, "min": 1, "max": 10, "label": "Event Producers"},
            "num_consumers": {"type": "int", "default": 4, "min": 1, "max": 10, "label": "Event Consumers"},
            "num_topics": {"type": "int", "default": 3, "min": 1, "max": 8, "label": "Event Topics/Queues"},
            "has_dlq": {"type": "bool", "default": True, "label": "Dead Letter Queue"},
            "has_schema_registry": {"type": "bool", "default": True, "label": "Schema Registry"},
        },
    },
    "multi_cloud": {
        "name": "Multi-Cloud Deployment",
        "description": "Services distributed across multiple cloud providers",
        "icon": "☁️",
        "parameters": {
            "num_services": {"type": "int", "default": 4, "min": 2, "max": 10, "label": "Services"},
            "clouds": {"type": "int", "default": 2, "min": 2, "max": 3, "label": "Cloud Providers"},
            "has_global_lb": {"type": "bool", "default": True, "label": "Global Load Balancer"},
            "has_shared_db": {"type": "bool", "default": False, "label": "Shared Database"},
            "cross_cloud_deps": {"type": "int", "default": 2, "min": 0, "max": 5, "label": "Cross-Cloud Dependencies"},
        },
    },
    "data_pipeline": {
        "name": "Data Pipeline / ML Platform",
        "description": "ETL pipeline with data lake, processing, and ML serving",
        "icon": "📊",
        "parameters": {
            "num_sources": {"type": "int", "default": 3, "min": 1, "max": 8, "label": "Data Sources"},
            "num_transforms": {"type": "int", "default": 3, "min": 1, "max": 6, "label": "Transform Steps"},
            "has_ml_serving": {"type": "bool", "default": True, "label": "ML Model Serving"},
            "has_monitoring": {"type": "bool", "default": True, "label": "Data Quality Monitoring"},
            "has_scheduler": {"type": "bool", "default": True, "label": "Job Scheduler"},
        },
    },
}


class CustomScenarioBuilder:
    """
    Builds custom scenarios from user input.
    
    Behavior: Validates all inputs, assigns reasonable defaults for
    missing parameters, and produces a complete ScenarioConfig ready
    for the analysis pipeline.
    """
    
    def __init__(self):
        self._nodes: list[SystemNode] = []
        self._edges: list[SystemEdge] = []
        self._name: str = "Custom Scenario"
        self._description: str = ""
        self._business_context: dict[str, Any] = {}
    
    def reset(self) -> None:
        """Clear the builder state."""
        self._nodes.clear()
        self._edges.clear()
        self._name = "Custom Scenario"
        self._description = ""
        self._business_context = {}
    
    # ========================================================================
    # METHOD 1: JSON/Dict Import
    # ========================================================================
    
    def from_json(self, data: dict[str, Any]) -> ScenarioConfig:
        """
        Build a scenario from a JSON/dict description.
        
        Expected format:
        {
            "name": "My System",
            "description": "...",
            "nodes": [
                {"id": "svc1", "name": "Service 1", "type": "service", "tier": 1},
                {"id": "db1", "name": "Database", "type": "database", "tier": 1},
                ...
            ],
            "edges": [
                {"source": "svc1", "target": "db1", "relationship": "reads_from"},
                ...
            ],
            "business_context": {"revenue_per_minute": 10000, ...},
            "initial_failures": [...]  // optional
        }
        """
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary/JSON object")
        
        name = str(data.get("name", "Custom Scenario"))[:100]
        description = str(data.get("description", ""))[:500]
        
        # Parse nodes
        nodes = []
        for node_data in data.get("nodes", []):
            node = self._parse_node(node_data)
            if node:
                nodes.append(node)
        
        if not nodes:
            raise ValueError("At least one node is required")
        
        # Parse edges
        node_ids = {n.id for n in nodes}
        edges = []
        for edge_data in data.get("edges", []):
            edge = self._parse_edge(edge_data, node_ids)
            if edge:
                edges.append(edge)
        
        # Business context
        business_context = data.get("business_context", {})
        if not isinstance(business_context, dict):
            business_context = {}
        
        # Initial failures
        initial_failures = data.get("initial_failures", [])
        if not isinstance(initial_failures, list):
            initial_failures = []
        
        return ScenarioConfig(
            name=name,
            description=description,
            nodes=nodes,
            edges=edges,
            initial_failures=initial_failures,
            business_context=business_context,
            simulation_duration_seconds=data.get("duration", 300.0),
            complexity_level=self._infer_complexity(nodes, edges),
        )
    
    # ========================================================================
    # METHOD 2: Template-Based Generation
    # ========================================================================
    
    def from_template(self, template_id: str, params: dict[str, Any] = None) -> ScenarioConfig:
        """
        Generate a scenario from a parameterized template.
        
        Args:
            template_id: One of the available template keys
            params: Parameter overrides for the template
        """
        if template_id not in TEMPLATES:
            available = list(TEMPLATES.keys())
            raise ValueError(f"Unknown template: {template_id}. Available: {available}")
        
        template = TEMPLATES[template_id]
        resolved_params = self._resolve_params(template["parameters"], params or {})
        
        # Route to specific template builder
        builders = {
            "microservices": self._build_microservices,
            "monolith": self._build_monolith,
            "event_driven": self._build_event_driven,
            "multi_cloud": self._build_multi_cloud,
            "data_pipeline": self._build_data_pipeline,
        }
        
        builder = builders.get(template_id)
        if not builder:
            raise ValueError(f"Template builder not implemented: {template_id}")
        
        nodes, edges = builder(resolved_params)
        
        return ScenarioConfig(
            name=template["name"],
            description=template["description"],
            nodes=nodes,
            edges=edges,
            initial_failures=[],
            business_context={"template": template_id, "params": resolved_params},
            simulation_duration_seconds=300.0,
            complexity_level=self._infer_complexity(nodes, edges),
        )
    
    # ========================================================================
    # METHOD 3: Interactive Builder (node-by-node)
    # ========================================================================
    
    def add_node(
        self,
        node_id: str,
        name: str,
        node_type: str = "service",
        tier: int = 2,
        business_value: float = 0.5,
        resilience: float = 0.7,
    ) -> None:
        """Add a node interactively."""
        node = SystemNode(
            id=node_id,
            name=name,
            node_type=node_type,
            tier=max(1, min(4, tier)),
            business_value=max(0.0, min(1.0, business_value)),
            resilience=max(0.0, min(1.0, resilience)),
        )
        self._nodes.append(node)
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str = "depends_on",
        weight: float = 0.5,
        is_critical: bool = False,
    ) -> None:
        """Add an edge interactively."""
        edge = SystemEdge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            weight=max(0.0, min(1.0, weight)),
            is_critical=is_critical,
        )
        self._edges.append(edge)
    
    def set_metadata(self, name: str, description: str = "", business_context: dict = None) -> None:
        """Set scenario metadata."""
        self._name = name
        self._description = description
        self._business_context = business_context or {}
    
    def build(self) -> ScenarioConfig:
        """Build the scenario from interactively added components."""
        if not self._nodes:
            raise ValueError("No nodes added. Use add_node() first.")
        
        return ScenarioConfig(
            name=self._name,
            description=self._description,
            nodes=list(self._nodes),
            edges=list(self._edges),
            business_context=self._business_context,
            simulation_duration_seconds=300.0,
            complexity_level=self._infer_complexity(self._nodes, self._edges),
        )
    
    # ========================================================================
    # Template Builders
    # ========================================================================
    
    def _build_microservices(self, params: dict) -> tuple[list, list]:
        """Generate a microservices architecture."""
        nodes = []
        edges = []
        
        # API Gateway
        if params.get("has_gateway", True):
            nodes.append(SystemNode(id="api_gateway", name="API Gateway", node_type="gateway", tier=1, business_value=0.9, resilience=0.8))
        
        # Services
        for i in range(params.get("num_services", 5)):
            svc_id = f"service_{i+1}"
            tier = 1 if i < 2 else 2
            nodes.append(SystemNode(
                id=svc_id, name=f"Service {i+1}", node_type="service",
                tier=tier, business_value=0.8 - i * 0.05, resilience=0.75,
            ))
            if params.get("has_gateway"):
                edges.append(SystemEdge(source_id="api_gateway", target_id=svc_id, relationship="routes_through", weight=0.8))
        
        # Databases
        for i in range(params.get("num_databases", 2)):
            db_id = f"database_{i+1}"
            nodes.append(SystemNode(id=db_id, name=f"Database {i+1}", node_type="database", tier=1, business_value=0.9, resilience=0.85))
            # Connect first few services to databases
            for j in range(min(3, params.get("num_services", 5))):
                edges.append(SystemEdge(source_id=f"service_{j+1}", target_id=db_id, relationship="reads_from", weight=0.7))
        
        # Cache
        if params.get("has_cache", True):
            nodes.append(SystemNode(id="cache", name="Redis Cache", node_type="cache", tier=2, business_value=0.6, resilience=0.65))
            for i in range(min(3, params.get("num_services", 5))):
                edges.append(SystemEdge(source_id=f"service_{i+1}", target_id="cache", relationship="reads_from", weight=0.5))
        
        # Message Queue
        if params.get("has_queue", True):
            nodes.append(SystemNode(id="queue", name="Message Queue", node_type="queue", tier=2, business_value=0.7, resilience=0.75))
            edges.append(SystemEdge(source_id=f"service_1", target_id="queue", relationship="writes_to", weight=0.6))
            if params.get("num_services", 5) > 2:
                edges.append(SystemEdge(source_id="queue", target_id=f"service_3", relationship="triggers", weight=0.5))
        
        # External APIs
        for i in range(params.get("external_apis", 2)):
            ext_id = f"external_api_{i+1}"
            nodes.append(SystemNode(id=ext_id, name=f"External API {i+1}", node_type="external", tier=3, business_value=0.5, resilience=0.4))
            svc_idx = min(i, params.get("num_services", 5) - 1)
            edges.append(SystemEdge(source_id=f"service_{svc_idx+1}", target_id=ext_id, relationship="calls", weight=0.5))
        
        return nodes, edges
    
    def _build_monolith(self, params: dict) -> tuple[list, list]:
        """Generate a monolithic architecture."""
        nodes = []
        edges = []
        
        # Core monolith
        nodes.append(SystemNode(id="monolith", name="Application Server", node_type="service", tier=1, business_value=0.95, resilience=0.7))
        nodes.append(SystemNode(id="primary_db", name="Primary Database", node_type="database", tier=1, business_value=0.95, resilience=0.85))
        edges.append(SystemEdge(source_id="monolith", target_id="primary_db", relationship="reads_from", weight=0.95, is_critical=True))
        
        # Load balancer
        nodes.append(SystemNode(id="lb", name="Load Balancer", node_type="load_balancer", tier=1, business_value=0.9, resilience=0.8))
        edges.append(SystemEdge(source_id="lb", target_id="monolith", relationship="routes_through", weight=0.9, is_critical=True))
        
        if params.get("has_replica"):
            nodes.append(SystemNode(id="replica_db", name="DB Replica", node_type="database", tier=2, business_value=0.6, resilience=0.7))
            edges.append(SystemEdge(source_id="primary_db", target_id="replica_db", relationship="writes_to", weight=0.6))
        
        if params.get("has_cache"):
            nodes.append(SystemNode(id="cache", name="Cache Layer", node_type="cache", tier=2, business_value=0.6, resilience=0.65))
            edges.append(SystemEdge(source_id="monolith", target_id="cache", relationship="reads_from", weight=0.7))
        
        if params.get("has_cdn"):
            nodes.append(SystemNode(id="cdn", name="CDN", node_type="cdn", tier=2, business_value=0.6, resilience=0.7))
            edges.append(SystemEdge(source_id="lb", target_id="cdn", relationship="depends_on", weight=0.5))
        
        if params.get("has_queue"):
            nodes.append(SystemNode(id="job_queue", name="Job Queue", node_type="queue", tier=3, business_value=0.5, resilience=0.7))
            edges.append(SystemEdge(source_id="monolith", target_id="job_queue", relationship="writes_to", weight=0.4))
        
        for i in range(params.get("external_apis", 1)):
            ext_id = f"ext_{i+1}"
            nodes.append(SystemNode(id=ext_id, name=f"External Service {i+1}", node_type="external", tier=3, business_value=0.4, resilience=0.4))
            edges.append(SystemEdge(source_id="monolith", target_id=ext_id, relationship="calls", weight=0.4))
        
        return nodes, edges
    
    def _build_event_driven(self, params: dict) -> tuple[list, list]:
        """Generate an event-driven architecture."""
        nodes = []
        edges = []
        
        # Event broker
        nodes.append(SystemNode(id="event_broker", name="Event Broker (Kafka)", node_type="queue", tier=1, business_value=0.9, resilience=0.8))
        
        # Producers
        for i in range(params.get("num_producers", 3)):
            pid = f"producer_{i+1}"
            nodes.append(SystemNode(id=pid, name=f"Producer {i+1}", node_type="service", tier=2, business_value=0.7, resilience=0.7))
            edges.append(SystemEdge(source_id=pid, target_id="event_broker", relationship="writes_to", weight=0.8))
        
        # Consumers
        for i in range(params.get("num_consumers", 4)):
            cid = f"consumer_{i+1}"
            nodes.append(SystemNode(id=cid, name=f"Consumer {i+1}", node_type="service", tier=2, business_value=0.6, resilience=0.7))
            edges.append(SystemEdge(source_id="event_broker", target_id=cid, relationship="triggers", weight=0.7))
        
        # Database for consumers
        nodes.append(SystemNode(id="event_store", name="Event Store DB", node_type="database", tier=1, business_value=0.85, resilience=0.85))
        edges.append(SystemEdge(source_id="consumer_1", target_id="event_store", relationship="writes_to", weight=0.8))
        
        if params.get("has_dlq"):
            nodes.append(SystemNode(id="dlq", name="Dead Letter Queue", node_type="queue", tier=3, business_value=0.4, resilience=0.7))
            edges.append(SystemEdge(source_id="event_broker", target_id="dlq", relationship="writes_to", weight=0.3))
        
        if params.get("has_schema_registry"):
            nodes.append(SystemNode(id="schema_reg", name="Schema Registry", node_type="service", tier=2, business_value=0.6, resilience=0.7))
            edges.append(SystemEdge(source_id="event_broker", target_id="schema_reg", relationship="depends_on", weight=0.6))
        
        return nodes, edges
    
    def _build_multi_cloud(self, params: dict) -> tuple[list, list]:
        """Generate a multi-cloud architecture."""
        nodes = []
        edges = []
        
        cloud_names = ["AWS", "GCP", "Azure"][:params.get("clouds", 2)]
        
        if params.get("has_global_lb"):
            nodes.append(SystemNode(id="global_lb", name="Global Load Balancer", node_type="load_balancer", tier=1, business_value=0.95, resilience=0.8))
        
        for ci, cloud in enumerate(cloud_names):
            # Cloud provider node
            cloud_id = f"cloud_{ci+1}"
            nodes.append(SystemNode(id=cloud_id, name=f"{cloud} Region", node_type="external", tier=1, business_value=0.9, resilience=0.45))
            
            if params.get("has_global_lb"):
                edges.append(SystemEdge(source_id="global_lb", target_id=cloud_id, relationship="routes_through", weight=0.8))
            
            # Services per cloud
            svcs_per_cloud = max(1, params.get("num_services", 4) // len(cloud_names))
            for si in range(svcs_per_cloud):
                svc_id = f"svc_{cloud.lower()}_{si+1}"
                nodes.append(SystemNode(id=svc_id, name=f"{cloud} Service {si+1}", node_type="service", tier=2, business_value=0.7, resilience=0.7))
                edges.append(SystemEdge(source_id=svc_id, target_id=cloud_id, relationship="depends_on", weight=0.9))
        
        # Cross-cloud dependencies
        all_svcs = [n.id for n in nodes if n.node_type == "service"]
        for i in range(min(params.get("cross_cloud_deps", 2), len(all_svcs) - 1)):
            if i + 1 < len(all_svcs):
                edges.append(SystemEdge(source_id=all_svcs[i], target_id=all_svcs[i+1], relationship="calls", weight=0.5))
        
        return nodes, edges
    
    def _build_data_pipeline(self, params: dict) -> tuple[list, list]:
        """Generate a data pipeline architecture."""
        nodes = []
        edges = []
        
        # Data sources
        for i in range(params.get("num_sources", 3)):
            src_id = f"source_{i+1}"
            nodes.append(SystemNode(id=src_id, name=f"Data Source {i+1}", node_type="external", tier=2, business_value=0.6, resilience=0.4))
        
        # Ingestion layer
        nodes.append(SystemNode(id="ingestion", name="Data Ingestion", node_type="service", tier=1, business_value=0.8, resilience=0.75))
        for i in range(params.get("num_sources", 3)):
            edges.append(SystemEdge(source_id=f"source_{i+1}", target_id="ingestion", relationship="writes_to", weight=0.7))
        
        # Data lake
        nodes.append(SystemNode(id="data_lake", name="Data Lake / Warehouse", node_type="database", tier=1, business_value=0.9, resilience=0.85))
        edges.append(SystemEdge(source_id="ingestion", target_id="data_lake", relationship="writes_to", weight=0.9, is_critical=True))
        
        # Transform steps
        prev_id = "data_lake"
        for i in range(params.get("num_transforms", 3)):
            t_id = f"transform_{i+1}"
            nodes.append(SystemNode(id=t_id, name=f"Transform {i+1}", node_type="service", tier=2, business_value=0.7, resilience=0.7))
            edges.append(SystemEdge(source_id=prev_id, target_id=t_id, relationship="reads_from", weight=0.7))
            prev_id = t_id
        
        # ML serving
        if params.get("has_ml_serving"):
            nodes.append(SystemNode(id="ml_serving", name="ML Model Serving", node_type="service", tier=2, business_value=0.75, resilience=0.65))
            edges.append(SystemEdge(source_id=prev_id, target_id="ml_serving", relationship="writes_to", weight=0.7))
        
        # Scheduler
        if params.get("has_scheduler"):
            nodes.append(SystemNode(id="scheduler", name="Job Scheduler", node_type="service", tier=2, business_value=0.7, resilience=0.7))
            edges.append(SystemEdge(source_id="scheduler", target_id="ingestion", relationship="triggers", weight=0.8))
        
        # Monitoring
        if params.get("has_monitoring"):
            nodes.append(SystemNode(id="dq_monitor", name="Data Quality Monitor", node_type="monitoring", tier=3, business_value=0.5, resilience=0.6))
            edges.append(SystemEdge(source_id="dq_monitor", target_id="data_lake", relationship="monitors", weight=0.4))
        
        return nodes, edges
    
    # ========================================================================
    # Helpers
    # ========================================================================
    
    def _parse_node(self, data: dict) -> Optional[SystemNode]:
        """Parse a node from dict input with validation."""
        if not isinstance(data, dict):
            return None
        
        node_id = str(data.get("id", ""))[:50]
        name = str(data.get("name", ""))[:100]
        
        if not node_id or not name:
            return None
        
        node_type = str(data.get("type", data.get("node_type", "service")))[:30]
        tier = max(1, min(4, int(data.get("tier", 2))))
        business_value = max(0.0, min(1.0, float(data.get("business_value", 0.5))))
        resilience = max(0.0, min(1.0, float(data.get("resilience", 0.7))))
        
        return SystemNode(
            id=node_id,
            name=name,
            node_type=node_type,
            description=str(data.get("description", ""))[:200],
            tier=tier,
            business_value=business_value,
            resilience=resilience,
        )
    
    def _parse_edge(self, data: dict, valid_ids: set) -> Optional[SystemEdge]:
        """Parse an edge from dict input with validation."""
        if not isinstance(data, dict):
            return None
        
        source = str(data.get("source", data.get("source_id", "")))[:50]
        target = str(data.get("target", data.get("target_id", "")))[:50]
        
        if not source or not target:
            return None
        if source not in valid_ids or target not in valid_ids:
            return None
        
        return SystemEdge(
            source_id=source,
            target_id=target,
            relationship=str(data.get("relationship", "depends_on"))[:30],
            weight=max(0.0, min(1.0, float(data.get("weight", 0.5)))),
            is_critical=bool(data.get("is_critical", False)),
        )
    
    def _resolve_params(self, template_params: dict, user_params: dict) -> dict:
        """Resolve template parameters with user overrides."""
        resolved = {}
        for key, spec in template_params.items():
            if key in user_params:
                value = user_params[key]
                # Type coercion and validation
                if spec["type"] == "int":
                    value = max(spec.get("min", 0), min(spec.get("max", 100), int(value)))
                elif spec["type"] == "bool":
                    value = bool(value)
                resolved[key] = value
            else:
                resolved[key] = spec["default"]
        return resolved
    
    @staticmethod
    def _infer_complexity(nodes: list, edges: list) -> str:
        """Infer complexity level from graph size."""
        n = len(nodes)
        if n > 20:
            return "high"
        elif n > 10:
            return "medium"
        else:
            return "low"
    
    @staticmethod
    def get_available_templates() -> dict:
        """Get all available templates with their parameters."""
        return TEMPLATES
    
    @staticmethod
    def get_node_types() -> list[str]:
        """Get all valid node types."""
        return list(NODE_TYPES.keys())
    
    @staticmethod
    def get_relationship_types() -> list[str]:
        """Get all valid relationship types."""
        return [
            "depends_on", "calls", "reads_from", "writes_to",
            "authenticates_via", "routes_through", "monitors",
            "triggers", "fallback_to",
        ]