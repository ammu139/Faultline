"""
Banking System Scenario
Simulates a banking transaction processing system with fraud detection,
core banking, and regulatory compliance components.

Based on real-world architectures: SWIFT, Visa/Mastercard networks, core banking
Incident reference: Major bank outages, SWIFT disruptions, fraud cascades
Data sources: BIS reports, PCI-DSS standards, banking industry benchmarks
"""

from core.models import SystemNode, SystemEdge, ScenarioConfig
from data.real_world_data import (
    REAL_LATENCIES, REAL_FAILURE_RATES, REAL_SLA_TARGETS,
    BUSINESS_IMPACT, TRAFFIC_PATTERNS, RECOVERY_TIMES,
)


def build_banking_scenario() -> ScenarioConfig:
    """Build a realistic banking system dependency graph."""
    
    nodes = [
        # Tier 1 - Core Banking
        SystemNode(
            id="core_banking",
            name="Core Banking Engine",
            node_type="service",
            description="Central transaction processing and account management",
            tier=1,
            business_value=0.99,
            resilience=0.9,
            load_capacity=1.0,
            current_load=0.5,
        ),
        SystemNode(
            id="transaction_processor",
            name="Transaction Processor",
            node_type="service",
            description="Real-time transaction authorization and settlement",
            tier=1,
            business_value=0.95,
            resilience=0.85,
            load_capacity=1.0,
            current_load=0.6,
        ),
        SystemNode(
            id="fraud_detection",
            name="Fraud Detection Engine",
            node_type="service",
            description="ML-based real-time fraud scoring and blocking",
            tier=1,
            business_value=0.9,
            resilience=0.8,
            load_capacity=1.0,
            current_load=0.4,
        ),
        SystemNode(
            id="account_db",
            name="Account Database",
            node_type="database",
            description="Primary account balances and ledger",
            tier=1,
            business_value=0.99,
            resilience=0.9,
            load_capacity=1.0,
            current_load=0.5,
        ),
        
        # Tier 1 - Customer Channels
        SystemNode(
            id="online_banking",
            name="Online Banking Portal",
            node_type="service",
            description="Web-based customer banking interface",
            tier=1,
            business_value=0.85,
            resilience=0.75,
            load_capacity=1.0,
            current_load=0.5,
        ),
        SystemNode(
            id="mobile_banking",
            name="Mobile Banking App",
            node_type="api",
            description="Mobile banking API and services",
            tier=1,
            business_value=0.85,
            resilience=0.75,
            load_capacity=1.0,
            current_load=0.6,
        ),
        
        # Tier 2 - Payment Infrastructure
        SystemNode(
            id="payment_switch",
            name="Payment Switch",
            node_type="gateway",
            description="Routes payments between networks (SWIFT, ACH, RTGS)",
            tier=1,
            business_value=0.9,
            resilience=0.85,
            load_capacity=1.0,
            current_load=0.4,
        ),
        SystemNode(
            id="card_processor",
            name="Card Processing",
            node_type="payment",
            description="Credit/debit card authorization",
            tier=2,
            business_value=0.85,
            resilience=0.8,
            load_capacity=1.0,
            current_load=0.5,
        ),
        SystemNode(
            id="atm_network",
            name="ATM Network Gateway",
            node_type="gateway",
            description="ATM transaction routing",
            tier=2,
            business_value=0.7,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.3,
        ),
        
        # Tier 2 - Security & Compliance
        SystemNode(
            id="auth_service",
            name="Authentication (MFA)",
            node_type="auth",
            description="Multi-factor authentication service",
            tier=2,
            business_value=0.85,
            resilience=0.8,
            load_capacity=1.0,
            current_load=0.3,
        ),
        SystemNode(
            id="aml_service",
            name="AML Screening",
            node_type="service",
            description="Anti-money laundering transaction screening",
            tier=2,
            business_value=0.8,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.4,
        ),
        SystemNode(
            id="kyc_service",
            name="KYC Verification",
            node_type="service",
            description="Know Your Customer identity verification",
            tier=3,
            business_value=0.6,
            resilience=0.6,
            load_capacity=1.0,
            current_load=0.2,
        ),
        
        # Tier 2 - Data & Analytics
        SystemNode(
            id="transaction_db",
            name="Transaction Database",
            node_type="database",
            description="Transaction history and audit trail",
            tier=2,
            business_value=0.8,
            resilience=0.85,
            load_capacity=1.0,
            current_load=0.6,
        ),
        SystemNode(
            id="fraud_ml_model",
            name="Fraud ML Model Service",
            node_type="service",
            description="Machine learning model serving for fraud scores",
            tier=2,
            business_value=0.75,
            resilience=0.6,
            load_capacity=1.0,
            current_load=0.5,
        ),
        SystemNode(
            id="risk_engine",
            name="Risk Assessment Engine",
            node_type="service",
            description="Real-time risk scoring for transactions",
            tier=2,
            business_value=0.8,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.4,
        ),
        
        # Tier 3 - Supporting
        SystemNode(
            id="notification_hub",
            name="Notification Hub",
            node_type="service",
            description="Customer alerts and notifications",
            tier=3,
            business_value=0.5,
            resilience=0.6,
            load_capacity=1.0,
            current_load=0.3,
        ),
        SystemNode(
            id="audit_logger",
            name="Audit Log Service",
            node_type="service",
            description="Regulatory audit trail logging",
            tier=2,
            business_value=0.7,
            resilience=0.7,
            load_capacity=1.0,
            current_load=0.4,
        ),
        SystemNode(
            id="reporting_service",
            name="Regulatory Reporting",
            node_type="service",
            description="Compliance and regulatory report generation",
            tier=3,
            business_value=0.6,
            resilience=0.5,
            load_capacity=1.0,
            current_load=0.2,
        ),
        SystemNode(
            id="message_broker",
            name="Message Broker",
            node_type="queue",
            description="Event-driven message processing",
            tier=2,
            business_value=0.7,
            resilience=0.75,
            load_capacity=1.0,
            current_load=0.5,
        ),
        
        # External
        SystemNode(
            id="swift_network",
            name="SWIFT Network",
            node_type="external",
            description="International payment messaging network",
            tier=2,
            business_value=0.8,
            resilience=0.4,
            load_capacity=1.0,
            current_load=0.3,
        ),
        SystemNode(
            id="credit_bureau",
            name="Credit Bureau API",
            node_type="external",
            description="External credit scoring service",
            tier=3,
            business_value=0.5,
            resilience=0.35,
            load_capacity=1.0,
            current_load=0.2,
        ),
        SystemNode(
            id="regulatory_api",
            name="Regulatory Authority API",
            node_type="external",
            description="Government regulatory reporting endpoint",
            tier=3,
            business_value=0.6,
            resilience=0.3,
            load_capacity=1.0,
            current_load=0.1,
        ),
    ]
    
    edges = [
        # Customer channels -> Core
        SystemEdge(source_id="online_banking", target_id="auth_service", relationship="authenticates_via", weight=0.9, is_critical=True),
        SystemEdge(source_id="online_banking", target_id="core_banking", relationship="calls", weight=0.9, is_critical=True),
        SystemEdge(source_id="mobile_banking", target_id="auth_service", relationship="authenticates_via", weight=0.9, is_critical=True),
        SystemEdge(source_id="mobile_banking", target_id="core_banking", relationship="calls", weight=0.9, is_critical=True),
        
        # Core banking flow
        SystemEdge(source_id="core_banking", target_id="account_db", relationship="reads_from", weight=0.95, is_critical=True),
        SystemEdge(source_id="core_banking", target_id="transaction_processor", relationship="calls", weight=0.9, is_critical=True),
        SystemEdge(source_id="core_banking", target_id="audit_logger", relationship="writes_to", weight=0.7),
        
        # Transaction processing
        SystemEdge(source_id="transaction_processor", target_id="fraud_detection", relationship="calls", weight=0.85, is_critical=True),
        SystemEdge(source_id="transaction_processor", target_id="payment_switch", relationship="calls", weight=0.9, is_critical=True),
        SystemEdge(source_id="transaction_processor", target_id="transaction_db", relationship="writes_to", weight=0.8),
        SystemEdge(source_id="transaction_processor", target_id="aml_service", relationship="calls", weight=0.7),
        SystemEdge(source_id="transaction_processor", target_id="risk_engine", relationship="calls", weight=0.7),
        
        # Fraud detection
        SystemEdge(source_id="fraud_detection", target_id="fraud_ml_model", relationship="calls", weight=0.8),
        SystemEdge(source_id="fraud_detection", target_id="transaction_db", relationship="reads_from", weight=0.7),
        SystemEdge(source_id="fraud_detection", target_id="message_broker", relationship="writes_to", weight=0.5),
        
        # Payment routing
        SystemEdge(source_id="payment_switch", target_id="swift_network", relationship="depends_on", weight=0.8),
        SystemEdge(source_id="payment_switch", target_id="card_processor", relationship="routes_through", weight=0.8),
        SystemEdge(source_id="card_processor", target_id="account_db", relationship="reads_from", weight=0.8),
        
        # ATM
        SystemEdge(source_id="atm_network", target_id="core_banking", relationship="calls", weight=0.8),
        SystemEdge(source_id="atm_network", target_id="auth_service", relationship="authenticates_via", weight=0.8),
        
        # Risk and compliance
        SystemEdge(source_id="risk_engine", target_id="credit_bureau", relationship="calls", weight=0.5),
        SystemEdge(source_id="risk_engine", target_id="transaction_db", relationship="reads_from", weight=0.6),
        SystemEdge(source_id="aml_service", target_id="transaction_db", relationship="reads_from", weight=0.7),
        SystemEdge(source_id="aml_service", target_id="regulatory_api", relationship="calls", weight=0.4),
        
        # Auth
        SystemEdge(source_id="auth_service", target_id="account_db", relationship="reads_from", weight=0.8),
        
        # Async processing
        SystemEdge(source_id="message_broker", target_id="notification_hub", relationship="triggers", weight=0.5),
        SystemEdge(source_id="message_broker", target_id="reporting_service", relationship="triggers", weight=0.4),
        SystemEdge(source_id="message_broker", target_id="audit_logger", relationship="triggers", weight=0.6),
        
        # Reporting
        SystemEdge(source_id="reporting_service", target_id="transaction_db", relationship="reads_from", weight=0.5),
        SystemEdge(source_id="reporting_service", target_id="regulatory_api", relationship="calls", weight=0.4),
        
        # KYC
        SystemEdge(source_id="kyc_service", target_id="credit_bureau", relationship="calls", weight=0.5),
        SystemEdge(source_id="kyc_service", target_id="account_db", relationship="reads_from", weight=0.4),
    ]
    
    return ScenarioConfig(
        name="Banking System",
        description=(
            "Core banking system with transaction processing, fraud detection, "
            "payment switching, and regulatory compliance. "
            "Simulates a fraud detection cascade causing transaction processing delays."
        ),
        nodes=nodes,
        edges=edges,
        initial_failures=[
            {
                "node_id": "fraud_ml_model",
                "stress_type": "latency",
                "intensity": 0.85,
                "description": "Fraud ML model experiencing high latency due to model drift",
            },
            {
                "node_id": "swift_network",
                "stress_type": "external_outage",
                "intensity": 0.7,
                "description": "SWIFT network experiencing intermittent connectivity issues",
            },
        ],
        external_factors=[
            {"type": "fraud_wave", "magnitude": 5.0, "description": "Coordinated fraud attack detected"},
            {"type": "regulatory_deadline", "description": "End-of-day settlement deadline approaching"},
        ],
        business_context={
            "transactions_per_second": TRAFFIC_PATTERNS["banking_normal_tps"],
            "peak_tps": TRAFFIC_PATTERNS["banking_peak_tps"],
            "average_transaction_value": BUSINESS_IMPACT["banking_transaction_value_avg"],
            "fraud_loss_per_minute": BUSINESS_IMPACT["banking_fraud_loss_per_minute"],
            "regulatory_fine_risk": BUSINESS_IMPACT["banking_regulatory_fine_base"],
            "sla_target": REAL_SLA_TARGETS["core_banking"],
            "payment_auth_latency_ms": REAL_LATENCIES["payment_authorization"],
            "swift_latency_ms": REAL_LATENCIES["swift_message"],
            "downtime_cost_per_minute": BUSINESS_IMPACT["downtime_cost_per_minute_tier1"],
            "incident_reference": "SWIFT network disruptions + ML model drift incidents",
        },
        simulation_duration_seconds=300.0,
        complexity_level="critical",
    )