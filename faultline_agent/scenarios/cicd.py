"""
CI/CD & Microservices Scenario
Simulates a software operations environment with microservices,
CI/CD pipelines, and infrastructure dependencies.

Based on real-world architectures: Netflix, Spotify, GitHub
Incident reference: GitHub Database 2022, Cloudflare BGP 2022, Fastly 2021
Data sources: CNCF surveys, Datadog reports, Kubernetes failure studies
"""

from core.models import SystemNode, SystemEdge, ScenarioConfig
from data.real_world_data import (
    REAL_LATENCIES, REAL_FAILURE_RATES, REAL_SLA_TARGETS,
    BUSINESS_IMPACT, RECOVERY_TIMES, KUBERNETES_DATA,
)


def build_cicd_scenario() -> ScenarioConfig:
    """Build a realistic CI/CD and microservices dependency graph."""
    
    nodes = [
        # Tier 1 - Production Services
        SystemNode(
            id="api_gateway",
            name="API Gateway (Kong)",
            node_type="gateway",
            description="Central API gateway routing all traffic",
            tier=1,
            business_value=0.95,
            resilience=0.8,
            load_capacity=1.0,
            current_load=0.6,
        ),
        SystemNode(
            id="user_service",
            name="User Service",
            node_type="service",
            description="User management microservice",
            tier=1,
            business_value=0.85,
            resilience=0.75,
            load_capacity=1.0,
            current_load=0.4,
        ),
        SystemNode(
            id="order_service",
            name="Order Service",
            node_type="service",
            description="Order processing microservice",
            tier=1,
            business_value=0.9,
            resilience=0.75,
            load_capacity=1.0,
            current_load=0.5,
        ),
        SystemNode(
            id="product_service",
            name="Product Service",
            node_type="service",
            description="Product catalog microservice",
            tier=2,
            business_value=0.8,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.4,
        ),
        SystemNode(
            id="notification_service",
            name="Notification Service",
            node_type="service",
            description="Email/SMS notification microservice",
            tier=3,
            business_value=0.5,
            resilience=0.6,
            load_capacity=1.0,
            current_load=0.3,
        ),
        
        # Tier 1 - Infrastructure
        SystemNode(
            id="kubernetes_cluster",
            name="Kubernetes Cluster",
            node_type="service",
            description="Container orchestration platform",
            tier=1,
            business_value=0.95,
            resilience=0.85,
            load_capacity=1.0,
            current_load=0.6,
        ),
        SystemNode(
            id="service_mesh",
            name="Service Mesh (Istio)",
            node_type="network",
            description="Service-to-service communication layer",
            tier=1,
            business_value=0.85,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.4,
        ),
        
        # Tier 2 - Data Layer
        SystemNode(
            id="postgres_primary",
            name="PostgreSQL Primary",
            node_type="database",
            description="Primary relational database",
            tier=1,
            business_value=0.9,
            resilience=0.85,
            load_capacity=1.0,
            current_load=0.5,
        ),
        SystemNode(
            id="postgres_replica",
            name="PostgreSQL Replica",
            node_type="database",
            description="Read replica for scaling",
            tier=2,
            business_value=0.6,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.4,
        ),
        SystemNode(
            id="redis_cluster",
            name="Redis Cluster",
            node_type="cache",
            description="Distributed caching layer",
            tier=2,
            business_value=0.7,
            resilience=0.65,
            load_capacity=1.0,
            current_load=0.6,
        ),
        SystemNode(
            id="kafka_cluster",
            name="Kafka Cluster",
            node_type="queue",
            description="Event streaming platform",
            tier=2,
            business_value=0.75,
            resilience=0.75,
            load_capacity=1.0,
            current_load=0.5,
        ),
        SystemNode(
            id="elasticsearch",
            name="Elasticsearch",
            node_type="database",
            description="Search and log aggregation",
            tier=3,
            business_value=0.5,
            resilience=0.6,
            load_capacity=1.0,
            current_load=0.5,
        ),
        
        # CI/CD Pipeline
        SystemNode(
            id="github_actions",
            name="GitHub Actions",
            node_type="external",
            description="CI/CD pipeline execution",
            tier=2,
            business_value=0.7,
            resilience=0.4,
            load_capacity=1.0,
            current_load=0.5,
        ),
        SystemNode(
            id="container_registry",
            name="Container Registry",
            node_type="service",
            description="Docker image storage and distribution",
            tier=2,
            business_value=0.7,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.3,
        ),
        SystemNode(
            id="argocd",
            name="ArgoCD",
            node_type="service",
            description="GitOps continuous deployment",
            tier=2,
            business_value=0.7,
            resilience=0.65,
            load_capacity=1.0,
            current_load=0.3,
        ),
        SystemNode(
            id="terraform_state",
            name="Terraform State",
            node_type="database",
            description="Infrastructure state management",
            tier=2,
            business_value=0.6,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.1,
        ),
        SystemNode(
            id="vault",
            name="HashiCorp Vault",
            node_type="auth",
            description="Secrets management",
            tier=2,
            business_value=0.85,
            resilience=0.8,
            load_capacity=1.0,
            current_load=0.2,
        ),
        
        # Monitoring & Observability
        SystemNode(
            id="prometheus",
            name="Prometheus",
            node_type="monitoring",
            description="Metrics collection and alerting",
            tier=2,
            business_value=0.6,
            resilience=0.6,
            load_capacity=1.0,
            current_load=0.5,
        ),
        SystemNode(
            id="grafana",
            name="Grafana",
            node_type="monitoring",
            description="Observability dashboards",
            tier=3,
            business_value=0.4,
            resilience=0.5,
            load_capacity=1.0,
            current_load=0.3,
        ),
        SystemNode(
            id="pagerduty",
            name="PagerDuty",
            node_type="external",
            description="Incident alerting and on-call management",
            tier=2,
            business_value=0.6,
            resilience=0.35,
            load_capacity=1.0,
            current_load=0.1,
        ),
        SystemNode(
            id="jaeger",
            name="Jaeger Tracing",
            node_type="monitoring",
            description="Distributed tracing",
            tier=3,
            business_value=0.4,
            resilience=0.5,
            load_capacity=1.0,
            current_load=0.4,
        ),
        
        # External & Cloud
        SystemNode(
            id="aws_services",
            name="AWS Cloud Services",
            node_type="external",
            description="Cloud infrastructure provider",
            tier=1,
            business_value=0.95,
            resilience=0.4,
            load_capacity=1.0,
            current_load=0.4,
        ),
        SystemNode(
            id="dns_service",
            name="DNS (Route53)",
            node_type="network",
            description="DNS resolution service",
            tier=1,
            business_value=0.9,
            resilience=0.5,
            load_capacity=1.0,
            current_load=0.2,
        ),
        SystemNode(
            id="cdn_cloudfront",
            name="CloudFront CDN",
            node_type="cdn",
            description="Content delivery and edge caching",
            tier=2,
            business_value=0.7,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.4,
        ),
    ]
    
    edges = [
        # Traffic flow
        SystemEdge(source_id="dns_service", target_id="cdn_cloudfront", relationship="routes_through", weight=0.8),
        SystemEdge(source_id="cdn_cloudfront", target_id="api_gateway", relationship="routes_through", weight=0.8),
        SystemEdge(source_id="api_gateway", target_id="service_mesh", relationship="routes_through", weight=0.9, is_critical=True),
        
        # Service mesh routing
        SystemEdge(source_id="service_mesh", target_id="user_service", relationship="routes_through", weight=0.8),
        SystemEdge(source_id="service_mesh", target_id="order_service", relationship="routes_through", weight=0.8),
        SystemEdge(source_id="service_mesh", target_id="product_service", relationship="routes_through", weight=0.7),
        
        # Service dependencies
        SystemEdge(source_id="user_service", target_id="postgres_primary", relationship="reads_from", weight=0.9, is_critical=True),
        SystemEdge(source_id="user_service", target_id="redis_cluster", relationship="reads_from", weight=0.6),
        SystemEdge(source_id="user_service", target_id="vault", relationship="authenticates_via", weight=0.7),
        
        SystemEdge(source_id="order_service", target_id="postgres_primary", relationship="writes_to", weight=0.9, is_critical=True),
        SystemEdge(source_id="order_service", target_id="kafka_cluster", relationship="writes_to", weight=0.7),
        SystemEdge(source_id="order_service", target_id="user_service", relationship="calls", weight=0.6),
        SystemEdge(source_id="order_service", target_id="product_service", relationship="calls", weight=0.6),
        
        SystemEdge(source_id="product_service", target_id="postgres_replica", relationship="reads_from", weight=0.7),
        SystemEdge(source_id="product_service", target_id="redis_cluster", relationship="reads_from", weight=0.6),
        SystemEdge(source_id="product_service", target_id="elasticsearch", relationship="reads_from", weight=0.5),
        
        # Database replication
        SystemEdge(source_id="postgres_primary", target_id="postgres_replica", relationship="writes_to", weight=0.7),
        
        # Event processing
        SystemEdge(source_id="kafka_cluster", target_id="notification_service", relationship="triggers", weight=0.5),
        SystemEdge(source_id="kafka_cluster", target_id="elasticsearch", relationship="writes_to", weight=0.4),
        
        # Kubernetes dependencies
        SystemEdge(source_id="kubernetes_cluster", target_id="aws_services", relationship="depends_on", weight=0.9, is_critical=True),
        SystemEdge(source_id="user_service", target_id="kubernetes_cluster", relationship="depends_on", weight=0.9),
        SystemEdge(source_id="order_service", target_id="kubernetes_cluster", relationship="depends_on", weight=0.9),
        SystemEdge(source_id="product_service", target_id="kubernetes_cluster", relationship="depends_on", weight=0.9),
        
        # CI/CD Pipeline
        SystemEdge(source_id="github_actions", target_id="container_registry", relationship="writes_to", weight=0.7),
        SystemEdge(source_id="argocd", target_id="container_registry", relationship="reads_from", weight=0.7),
        SystemEdge(source_id="argocd", target_id="kubernetes_cluster", relationship="writes_to", weight=0.8),
        SystemEdge(source_id="argocd", target_id="vault", relationship="authenticates_via", weight=0.6),
        SystemEdge(source_id="github_actions", target_id="terraform_state", relationship="reads_from", weight=0.5),
        
        # Monitoring
        SystemEdge(source_id="prometheus", target_id="kubernetes_cluster", relationship="monitors", weight=0.5),
        SystemEdge(source_id="prometheus", target_id="pagerduty", relationship="triggers", weight=0.5),
        SystemEdge(source_id="grafana", target_id="prometheus", relationship="reads_from", weight=0.5),
        SystemEdge(source_id="jaeger", target_id="elasticsearch", relationship="writes_to", weight=0.4),
        SystemEdge(source_id="service_mesh", target_id="jaeger", relationship="writes_to", weight=0.3),
        
        # Secrets
        SystemEdge(source_id="vault", target_id="kubernetes_cluster", relationship="depends_on", weight=0.6),
    ]
    
    return ScenarioConfig(
        name="Software Ops / CI-CD",
        description=(
            "Microservices architecture with Kubernetes, service mesh, "
            "CI/CD pipelines, and observability stack. "
            "Simulates a bad deployment cascading through the service mesh."
        ),
        nodes=nodes,
        edges=edges,
        initial_failures=[
            {
                "node_id": "container_registry",
                "stress_type": "latency",
                "intensity": 0.8,
                "description": "Container registry experiencing high pull latency",
            },
            {
                "node_id": "service_mesh",
                "stress_type": "network_partition",
                "intensity": 0.6,
                "description": "Service mesh sidecar injection causing network issues after update",
            },
        ],
        external_factors=[
            {"type": "bad_deployment", "description": "Faulty config pushed via ArgoCD"},
            {"type": "cloud_degradation", "description": "AWS us-east-1 experiencing elevated error rates"},
        ],
        business_context={
            "deployments_per_day": 50,
            "mttr_target_minutes": BUSINESS_IMPACT["mttr_industry_average_minutes"],
            "services_count": 25,
            "developer_count": 80,
            "developer_cost_per_hour": BUSINESS_IMPACT["developer_cost_per_hour"],
            "incident_team_size": BUSINESS_IMPACT["incident_response_team_size"],
            "sla_target": REAL_SLA_TARGETS["aws_ec2"],
            "pod_startup_seconds": KUBERNETES_DATA["pod_startup_time_seconds"],
            "hpa_scale_time_seconds": KUBERNETES_DATA["hpa_scale_up_time_seconds"],
            "downtime_cost_per_minute": BUSINESS_IMPACT["downtime_cost_per_minute_tier1"],
            "incident_reference": "GitHub Database 2022 + Cloudflare BGP 2022",
        },
        simulation_duration_seconds=300.0,
        complexity_level="high",
    )