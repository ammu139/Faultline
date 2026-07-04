"""
Insight Explanation Agent
Generates human-readable insights, risk assessments, and actionable
recommendations from propagation results.
"""

from __future__ import annotations
from typing import Any
from datetime import datetime
from agents.base_agent import BaseAgent, AgentResult
from core.models import FragilityInsight, ImpactSeverity


class InsightAgent(BaseAgent):
    """
    Analyzes propagation results and generates structured insights
    about system fragility, risk patterns, and recommendations.
    """
    
    def __init__(self):
        super().__init__(
            name="InsightAgent",
            description="Generates fragility insights and actionable recommendations"
        )
    
    def execute(self, context: dict[str, Any]) -> AgentResult:
        """
        Generate insights from propagation results and graph analysis.
        
        Expected context:
            - propagation_results: Results from PropagationAgent
            - analysis: Graph structural analysis
            - scenario_name: Current scenario name
        """
        start_time = datetime.now()
        
        try:
            prop_results = context.get("propagation_results", [])
            analysis = context.get("analysis", {})
            scenario_name = context.get("scenario_name", "Unknown")
            
            self.reason(f"Generating insights for scenario: {scenario_name}")
            
            insights = []
            
            # Generate structural insights
            structural_insights = self._analyze_structure(analysis)
            insights.extend(structural_insights)
            
            # Generate propagation insights
            propagation_insights = self._analyze_propagation(prop_results)
            insights.extend(propagation_insights)
            
            # Generate business impact insights
            business_insights = self._analyze_business_impact(prop_results, analysis)
            insights.extend(business_insights)
            
            # Generate resilience recommendations
            recommendations = self._generate_recommendations(insights, prop_results)
            
            # Risk score calculation
            risk_score = self._calculate_risk_score(insights)
            
            self.reason(f"Generated {len(insights)} insights, risk score: {risk_score:.2f}")
            
            result_data = {
                "insights": [i.model_dump() for i in insights],
                "recommendations": recommendations,
                "risk_score": risk_score,
                "risk_level": self._risk_level(risk_score),
                "scenario_name": scenario_name,
                "summary": self._generate_executive_summary(insights, risk_score),
            }
            
            return self._build_result(
                success=True,
                data=result_data,
                start_time=start_time,
            )
        
        except Exception as e:
            return self._build_result(
                success=False,
                error=str(e),
                start_time=start_time,
            )
    
    def _analyze_structure(self, analysis: dict) -> list[FragilityInsight]:
        """Generate insights from structural analysis."""
        insights = []
        
        # Single points of failure
        spofs = analysis.get("single_points_of_failure", [])
        if spofs:
            affected = [s["node_id"] for s in spofs]
            insights.append(FragilityInsight(
                title=f"{len(spofs)} Single Points of Failure Detected",
                description=(
                    f"The system has {len(spofs)} nodes whose failure would disconnect "
                    f"parts of the dependency graph. These represent critical architectural risks."
                ),
                category="single_point_of_failure",
                severity=ImpactSeverity.CRITICAL if len(spofs) > 2 else ImpactSeverity.HIGH,
                affected_nodes=affected,
                recommendation="Add redundancy or failover paths for these critical nodes",
                confidence=0.95,
                evidence=[f"Node '{s.get('name', s['node_id'])}' is an articulation point" for s in spofs[:3]],
            ))
        
        # High fan-in nodes
        high_fan_in = analysis.get("high_fan_in_nodes", [])
        if high_fan_in:
            worst = high_fan_in[0]
            insights.append(FragilityInsight(
                title=f"High-Dependency Hub: {worst.get('name', worst['node_id'])}",
                description=(
                    f"{worst.get('name', 'Node')} has {worst['dependent_count']} dependent services. "
                    f"A failure here would cascade to multiple downstream systems."
                ),
                category="dependency_hub",
                severity=ImpactSeverity.HIGH,
                affected_nodes=[h["node_id"] for h in high_fan_in],
                recommendation="Implement circuit breakers and load shedding for hub nodes",
                confidence=0.9,
                evidence=[f"{h.get('name', h['node_id'])}: {h['dependent_count']} dependents" for h in high_fan_in[:3]],
            ))
        
        # Graph connectivity
        if not analysis.get("is_connected", True):
            insights.append(FragilityInsight(
                title="Disconnected System Components",
                description=(
                    f"The system graph has {analysis.get('component_count', 0)} disconnected components. "
                    f"This may indicate missing dependencies or isolated subsystems."
                ),
                category="architecture_gap",
                severity=ImpactSeverity.MEDIUM,
                affected_nodes=[],
                recommendation="Review system architecture for missing dependency links",
                confidence=0.85,
            ))
        
        # Risk clusters
        clusters = analysis.get("risk_clusters", [])
        if clusters:
            worst_cluster = clusters[0]
            insights.append(FragilityInsight(
                title=f"High-Risk Cluster ({worst_cluster['size']} nodes)",
                description=(
                    f"A cluster of {worst_cluster['size']} interconnected high-criticality nodes "
                    f"creates a concentrated risk zone. Failure in this cluster could be catastrophic."
                ),
                category="risk_cluster",
                severity=ImpactSeverity.CRITICAL,
                affected_nodes=worst_cluster["nodes"],
                recommendation="Isolate risk clusters with bulkhead patterns",
                confidence=0.88,
            ))
        
        return insights
    
    def _analyze_propagation(self, results: list[dict]) -> list[FragilityInsight]:
        """Generate insights from propagation results."""
        insights = []
        
        if not results:
            return insights
        
        # Deep cascades
        deep_cascades = [r for r in results if r.get("max_cascade_depth", 0) > 3]
        if deep_cascades:
            worst = max(deep_cascades, key=lambda x: x.get("max_cascade_depth", 0))
            insights.append(FragilityInsight(
                title=f"Deep Cascade Chain (depth: {worst['max_cascade_depth']})",
                description=(
                    f"Scenario '{worst.get('scenario_name', 'unknown')}' produced a cascade "
                    f"{worst['max_cascade_depth']} levels deep, affecting {worst.get('total_affected', 0)} nodes. "
                    f"Deep cascades indicate insufficient isolation between system layers."
                ),
                category="cascade_risk",
                severity=ImpactSeverity.HIGH,
                affected_nodes=worst.get("affected_nodes", [])[:10],
                recommendation="Implement circuit breakers at cascade boundaries",
                confidence=0.92,
            ))
        
        # Wide-impact scenarios
        wide_impact = [r for r in results if r.get("total_affected", 0) > 5]
        if wide_impact:
            worst = max(wide_impact, key=lambda x: x.get("total_affected", 0))
            insights.append(FragilityInsight(
                title=f"Wide Blast Radius ({worst['total_affected']} nodes affected)",
                description=(
                    f"A single failure scenario affected {worst['total_affected']} nodes. "
                    f"This indicates tight coupling and insufficient failure isolation."
                ),
                category="blast_radius",
                severity=ImpactSeverity.CRITICAL,
                affected_nodes=worst.get("affected_nodes", [])[:10],
                recommendation="Introduce bulkhead isolation and graceful degradation",
                confidence=0.9,
            ))
        
        # Critical node hits
        critical_hits = set()
        for r in results:
            critical_hits.update(r.get("critical_nodes_hit", []))
        
        if critical_hits:
            insights.append(FragilityInsight(
                title=f"{len(critical_hits)} Critical Nodes Vulnerable to Cascade",
                description=(
                    f"Tier-1 critical nodes were reached by failure cascades. "
                    f"These nodes represent core business functionality."
                ),
                category="critical_exposure",
                severity=ImpactSeverity.CATASTROPHIC,
                affected_nodes=list(critical_hits),
                recommendation="Add protective layers around critical nodes (rate limiting, fallbacks)",
                confidence=0.95,
            ))
        
        return insights
    
    def _analyze_business_impact(self, results: list[dict], analysis: dict) -> list[FragilityInsight]:
        """Generate business-focused insights."""
        insights = []
        
        # Estimate total downtime risk
        total_downtime = sum(r.get("estimated_downtime_seconds", 0) for r in results)
        if total_downtime > 600:  # More than 10 minutes
            insights.append(FragilityInsight(
                title=f"Significant Downtime Risk ({total_downtime/60:.0f} min estimated)",
                description=(
                    f"Combined failure scenarios could result in {total_downtime/60:.0f} minutes "
                    f"of service disruption. This exceeds typical SLA thresholds."
                ),
                category="business_continuity",
                severity=ImpactSeverity.HIGH,
                recommendation="Implement automated failover and reduce MTTR targets",
                confidence=0.8,
            ))
        
        return insights
    
    def _generate_recommendations(
        self, insights: list[FragilityInsight], results: list[dict]
    ) -> list[dict[str, Any]]:
        """Generate prioritized recommendations."""
        rec_map = {}
        
        for insight in insights:
            if insight.recommendation:
                key = insight.recommendation
                if key not in rec_map:
                    rec_map[key] = {
                        "recommendation": key,
                        "priority": insight.severity.value,
                        "related_insights": [],
                        "affected_nodes": set(),
                    }
                rec_map[key]["related_insights"].append(insight.title)
                rec_map[key]["affected_nodes"].update(insight.affected_nodes)
        
        # Collect recommendations from propagation results
        for r in results:
            for rec in r.get("recommendations", []):
                if rec not in rec_map:
                    rec_map[rec] = {
                        "recommendation": rec,
                        "priority": "medium",
                        "related_insights": [],
                        "affected_nodes": set(),
                    }
        
        # Convert sets to lists and sort by priority
        priority_order = {"catastrophic": 6, "critical": 5, "high": 4, "medium": 3, "low": 2, "negligible": 1}
        recommendations = []
        for rec in rec_map.values():
            rec["affected_nodes"] = list(rec["affected_nodes"])[:5]
            recommendations.append(rec)
        
        recommendations.sort(
            key=lambda x: priority_order.get(x["priority"], 0),
            reverse=True,
        )
        
        return recommendations[:10]
    
    def _calculate_risk_score(self, insights: list[FragilityInsight]) -> float:
        """Calculate overall risk score (0-1) from insights."""
        if not insights:
            return 0.0
        
        severity_weights = {
            ImpactSeverity.NEGLIGIBLE: 0.05,
            ImpactSeverity.LOW: 0.15,
            ImpactSeverity.MEDIUM: 0.35,
            ImpactSeverity.HIGH: 0.6,
            ImpactSeverity.CRITICAL: 0.8,
            ImpactSeverity.CATASTROPHIC: 1.0,
        }
        
        weighted_sum = sum(
            severity_weights.get(i.severity, 0.3) * i.confidence
            for i in insights
        )
        
        # Normalize to 0-1 range
        max_possible = len(insights) * 1.0
        return min(1.0, weighted_sum / max(max_possible, 1))
    
    def _risk_level(self, score: float) -> str:
        """Convert risk score to human-readable level."""
        if score > 0.8:
            return "CRITICAL"
        elif score > 0.6:
            return "HIGH"
        elif score > 0.4:
            return "ELEVATED"
        elif score > 0.2:
            return "MODERATE"
        else:
            return "LOW"
    
    def _generate_executive_summary(self, insights: list[FragilityInsight], risk_score: float) -> str:
        """Generate a brief executive summary."""
        critical_count = sum(1 for i in insights if i.severity in (ImpactSeverity.CRITICAL, ImpactSeverity.CATASTROPHIC))
        
        summary = (
            f"System Risk Assessment: {self._risk_level(risk_score)} "
            f"(score: {risk_score:.0%}). "
            f"Identified {len(insights)} fragility points, "
            f"{critical_count} at critical/catastrophic severity. "
        )
        
        if critical_count > 0:
            summary += "Immediate attention required for critical vulnerabilities."
        else:
            summary += "No immediate critical risks, but monitoring recommended."
        
        return summary