"""
E-Commerce Platform Scenario
Simulates a full e-commerce checkout system with payment processing,
inventory management, and customer-facing services.

Based on real-world architectures: Amazon, Shopify, Stripe
Incident reference: Stripe API degradation 2023, AWS US-East-1 2021
Data sources: AWS Architecture Blog, Stripe Status, industry benchmarks
"""

from core.models import SystemNode, SystemEdge, ScenarioConfig
from data.real_world_data import (
    REAL_LATENCIES, REAL_FAILURE_RATES, REAL_SLA_TARGETS,
    BUSINESS_IMPACT, TRAFFIC_PATTERNS, RECOVERY_TIMES,
    get_realistic_node_params,
)


def build_ecommerce_scenario() -> ScenarioConfig:
    """Build a realistic e-commerce platform dependency graph."""
    
    nodes = [
        # Tier 1 - Critical Customer-Facing
        SystemNode(
            id="web_frontend",
            name="Web Frontend",
            node_type="service",
            description="Customer-facing web application",
            tier=1,
            business_value=0.9,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.6,
        ),
        SystemNode(
            id="mobile_app",
            name="Mobile App Backend",
            node_type="api",
            description="Mobile application API layer",
            tier=1,
            business_value=0.85,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.5,
        ),
        SystemNode(
            id="checkout_service",
            name="Checkout Service",
            node_type="service",
            description="Core checkout and order processing",
            tier=1,
            business_value=0.95,
            resilience=0.8,
            load_capacity=1.0,
            current_load=0.4,
        ),
        
        # Tier 1 - Critical Infrastructure
        SystemNode(
            id="payment_gateway",
            name="Payment Gateway",
            node_type="payment",
            description="Payment processing and authorization",
            tier=1,
            business_value=0.95,
            resilience=0.85,
            load_capacity=1.0,
            current_load=0.3,
        ),
        SystemNode(
            id="order_db",
            name="Order Database",
            node_type="database",
            description="Primary order and transaction database",
            tier=1,
            business_value=0.9,
            resilience=0.85,
            load_capacity=1.0,
            current_load=0.5,
        ),
        
        # Tier 2 - Important Services
        SystemNode(
            id="inventory_service",
            name="Inventory Service",
            node_type="service",
            description="Real-time inventory management",
            tier=2,
            business_value=0.8,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.4,
        ),
        SystemNode(
            id="pricing_engine",
            name="Pricing Engine",
            node_type="service",
            description="Dynamic pricing and discount calculation",
            tier=2,
            business_value=0.7,
            resilience=0.65,
            load_capacity=1.0,
            current_load=0.3,
        ),
        SystemNode(
            id="user_auth",
            name="Authentication Service",
            node_type="auth",
            description="User authentication and session management",
            tier=2,
            business_value=0.85,
            resilience=0.8,
            load_capacity=1.0,
            current_load=0.3,
        ),
        SystemNode(
            id="search_service",
            name="Search Service",
            node_type="service",
            description="Product search and recommendations",
            tier=2,
            business_value=0.7,
            resilience=0.6,
            load_capacity=1.0,
            current_load=0.5,
        ),
        SystemNode(
            id="cart_service",
            name="Shopping Cart",
            node_type="service",
            description="Cart management and persistence",
            tier=2,
            business_value=0.8,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.4,
        ),
        
        # Tier 2 - Data Layer
        SystemNode(
            id="product_db",
            name="Product Database",
            node_type="database",
            description="Product catalog database",
            tier=2,
            business_value=0.75,
            resilience=0.8,
            load_capacity=1.0,
            current_load=0.4,
        ),
        SystemNode(
            id="user_db",
            name="User Database",
            node_type="database",
            description="Customer accounts and profiles",
            tier=2,
            business_value=0.8,
            resilience=0.8,
            load_capacity=1.0,
            current_load=0.3,
        ),
        SystemNode(
            id="redis_cache",
            name="Redis Cache",
            node_type="cache",
            description="Session and data caching layer",
            tier=2,
            business_value=0.6,
            resilience=0.65,
            load_capacity=1.0,
            current_load=0.7,
        ),
        
        # Tier 3 - Supporting Services
        SystemNode(
            id="notification_service",
            name="Notification Service",
            node_type="service",
            description="Email, SMS, push notifications",
            tier=3,
            business_value=0.5,
            resilience=0.6,
            load_capacity=1.0,
            current_load=0.3,
        ),
        SystemNode(
            id="analytics_service",
            name="Analytics Pipeline",
            node_type="service",
            description="Real-time analytics and tracking",
            tier=3,
            business_value=0.4,
            resilience=0.5,
            load_capacity=1.0,
            current_load=0.6,
        ),
        SystemNode(
            id="recommendation_engine",
            name="Recommendation Engine",
            node_type="service",
            description="ML-based product recommendations",
            tier=3,
            business_value=0.5,
            resilience=0.5,
            load_capacity=1.0,
            current_load=0.4,
        ),
        SystemNode(
            id="message_queue",
            name="Message Queue (Kafka)",
            node_type="queue",
            description="Async event processing",
            tier=2,
            business_value=0.7,
            resilience=0.75,
            load_capacity=1.0,
            current_load=0.5,
        ),
        
        # Tier 3 - Infrastructure
        SystemNode(
            id="cdn",
            name="CDN (CloudFront)",
            node_type="cdn",
            description="Content delivery network",
            tier=3,
            business_value=0.6,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.4,
        ),
        SystemNode(
            id="load_balancer",
            name="Load Balancer",
            node_type="load_balancer",
            description="Traffic distribution and health checks",
            tier=2,
            business_value=0.8,
            resilience=0.75,
            load_capacity=1.0,
            current_load=0.5,
        ),
        
        # External Dependencies
        SystemNode(
            id="stripe_api",
            name="Stripe API",
            node_type="external",
            description="External payment processor",
            tier=2,
            business_value=0.9,
            resilience=0.4,
            load_capacity=1.0,
            current_load=0.3,
        ),
        SystemNode(
            id="shipping_api",
            name="Shipping Provider API",
            node_type="external",
            description="Third-party shipping rates and tracking",
            tier=3,
            business_value=0.6,
            resilience=0.35,
            load_capacity=1.0,
            current_load=0.2,
        ),
        SystemNode(
            id="tax_service",
            name="Tax Calculation Service",
            node_type="external",
            description="External tax computation",
            tier=3,
            business_value=0.5,
            resilience=0.4,
            load_capacity=1.0,
            current_load=0.2,
        ),
    ]
    
    edges = [
        # Frontend dependencies
        SystemEdge(source_id="web_frontend", target_id="load_balancer", relationship="routes_through", weight=0.9, is_critical=True),
        SystemEdge(source_id="web_frontend", target_id="cdn", relationship="depends_on", weight=0.6),
        SystemEdge(source_id="web_frontend", target_id="user_auth", relationship="authenticates_via", weight=0.8, is_critical=True),
        SystemEdge(source_id="mobile_app", target_id="load_balancer", relationship="routes_through", weight=0.9, is_critical=True),
        SystemEdge(source_id="mobile_app", target_id="user_auth", relationship="authenticates_via", weight=0.8, is_critical=True),
        
        # Load balancer routes
        SystemEdge(source_id="load_balancer", target_id="checkout_service", relationship="routes_through", weight=0.9, is_critical=True),
        SystemEdge(source_id="load_balancer", target_id="search_service", relationship="routes_through", weight=0.6),
        SystemEdge(source_id="load_balancer", target_id="cart_service", relationship="routes_through", weight=0.7),
        
        # Checkout flow (critical path)
        SystemEdge(source_id="checkout_service", target_id="payment_gateway", relationship="depends_on", weight=0.95, is_critical=True),
        SystemEdge(source_id="checkout_service", target_id="inventory_service", relationship="calls", weight=0.8, is_critical=True),
        SystemEdge(source_id="checkout_service", target_id="order_db", relationship="writes_to", weight=0.9, is_critical=True),
        SystemEdge(source_id="checkout_service", target_id="cart_service", relationship="reads_from", weight=0.7),
        SystemEdge(source_id="checkout_service", target_id="pricing_engine", relationship="calls", weight=0.7),
        SystemEdge(source_id="checkout_service", target_id="tax_service", relationship="calls", weight=0.5),
        SystemEdge(source_id="checkout_service", target_id="shipping_api", relationship="calls", weight=0.5),
        
        # Payment flow
        SystemEdge(source_id="payment_gateway", target_id="stripe_api", relationship="depends_on", weight=0.95, is_critical=True),
        SystemEdge(source_id="payment_gateway", target_id="order_db", relationship="writes_to", weight=0.8),
        
        # Cart and inventory
        SystemEdge(source_id="cart_service", target_id="redis_cache", relationship="reads_from", weight=0.8),
        SystemEdge(source_id="cart_service", target_id="product_db", relationship="reads_from", weight=0.6),
        SystemEdge(source_id="inventory_service", target_id="product_db", relationship="reads_from", weight=0.8),
        SystemEdge(source_id="inventory_service", target_id="message_queue", relationship="writes_to", weight=0.6),
        
        # Search and recommendations
        SystemEdge(source_id="search_service", target_id="product_db", relationship="reads_from", weight=0.7),
        SystemEdge(source_id="search_service", target_id="redis_cache", relationship="reads_from", weight=0.5),
        SystemEdge(source_id="recommendation_engine", target_id="product_db", relationship="reads_from", weight=0.5),
        SystemEdge(source_id="recommendation_engine", target_id="analytics_service", relationship="reads_from", weight=0.4),
        
        # Auth
        SystemEdge(source_id="user_auth", target_id="user_db", relationship="reads_from", weight=0.9, is_critical=True),
        SystemEdge(source_id="user_auth", target_id="redis_cache", relationship="reads_from", weight=0.7),
        
        # Pricing
        SystemEdge(source_id="pricing_engine", target_id="product_db", relationship="reads_from", weight=0.6),
        SystemEdge(source_id="pricing_engine", target_id="redis_cache", relationship="reads_from", weight=0.5),
        
        # Async processing
        SystemEdge(source_id="message_queue", target_id="notification_service", relationship="triggers", weight=0.5),
        SystemEdge(source_id="message_queue", target_id="analytics_service", relationship="triggers", weight=0.4),
        
        # Notifications
        SystemEdge(source_id="notification_service", target_id="user_db", relationship="reads_from", weight=0.4),
    ]
    
    return ScenarioConfig(
        name="E-Commerce Platform",
        description=(
            "Full e-commerce platform with checkout, payment processing, "
            "inventory management, and customer-facing services. "
            "Simulates Black Friday traffic spike causing checkout collapse."
        ),
        nodes=nodes,
        edges=edges,
        initial_failures=[
            {
                "node_id": "stripe_api",
                "stress_type": "external_outage",
                "intensity": 0.9,
                "description": "Stripe API experiencing degraded performance during peak traffic",
            },
            {
                "node_id": "redis_cache",
                "stress_type": "memory_pressure",
                "intensity": 0.75,
                "description": "Redis cache under memory pressure from Black Friday traffic",
            },
        ],
        external_factors=[
            {"type": "traffic_spike", "magnitude": 3.0, "description": "Black Friday 3x traffic surge"},
            {"type": "seasonal", "description": "Holiday shopping peak"},
        ],
        business_context={
            "revenue_per_minute": BUSINESS_IMPACT["ecommerce_revenue_per_minute"],
            "peak_transactions_per_second": TRAFFIC_PATTERNS["ecommerce_peak_tps"],
            "normal_tps": TRAFFIC_PATTERNS["ecommerce_normal_tps"],
            "peak_multiplier": TRAFFIC_PATTERNS["ecommerce_peak_multiplier"],
            "sla_target": REAL_SLA_TARGETS["customer_portal"],
            "cart_abandonment_baseline": BUSINESS_IMPACT["ecommerce_cart_abandonment_rate"],
            "cart_abandonment_during_outage": BUSINESS_IMPACT["ecommerce_outage_abandonment"],
            "downtime_cost_per_minute": BUSINESS_IMPACT["downtime_cost_per_minute_tier1"],
            "incident_reference": "Stripe API Degradation 2023 + AWS US-East-1 2021",
        },
        simulation_duration_seconds=300.0,
        complexity_level="high",
    )