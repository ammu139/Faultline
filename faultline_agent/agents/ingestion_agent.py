"""
Ingestion Agent
Responsible for parsing system descriptions and converting them into
structured node/edge data for the dependency graph.
"""

from __future__ import annotations
from typing import Any
from datetime import datetime
from agents.base_agent import BaseAgent, AgentResult
from core.models import SystemNode, SystemEdge, ScenarioConfig


class IngestionAgent(BaseAgent):
    """
    Parses raw system descriptions (JSON, text, or scenario configs)
    and produces structured graph data.
    """
    
    def __init__(self):
        super().__init__(
            name="IngestionAgent",
            description="Parses system descriptions into structured graph components"
        )
    
    def execute(self, context: dict[str, Any]) -> AgentResult:
        """
        Process system input and produce structured nodes and edges.
        
        Expected context:
            - scenario_config: ScenarioConfig or dict with system description
            - raw_input: Optional raw text/JSON input
        """
        start_time = datetime.now()
        
        try:
            scenario_config = context.get("scenario_config")
            
            if scenario_config is None:
                return self._build_result(
                    success=False,
                    error="No scenario_config provided in context",
                    start_time=start_time,
                )
            
            self.reason("Received scenario configuration for ingestion")
            
            # If it's already a ScenarioConfig, validate it
            if isinstance(scenario_config, ScenarioConfig):
                self.reason(f"Processing ScenarioConfig: {scenario_config.name}")
                validated = self._validate_scenario(scenario_config)
                
                if not validated["valid"]:
                    return self._build_result(
                        success=False,
                        error=f"Validation failed: {validated['errors']}",
                        start_time=start_time,
                    )
                
                self.reason(f"Validated {len(scenario_config.nodes)} nodes and {len(scenario_config.edges)} edges")
                
                # Enrich nodes with computed properties
                enriched_nodes = self._enrich_nodes(scenario_config.nodes)
                enriched_edges = self._validate_edges(scenario_config.edges, enriched_nodes)
                
                result_data = {
                    "scenario": scenario_config,
                    "nodes": enriched_nodes,
                    "edges": enriched_edges,
                    "metadata": {
                        "total_nodes": len(enriched_nodes),
                        "total_edges": len(enriched_edges),
                        "node_types": list(set(n.node_type for n in enriched_nodes)),
                        "complexity": scenario_config.complexity_level,
                    }
                }
                
                self.send_message(
                    "DependencyAgent",
                    result_data,
                    msg_type="ingestion_complete"
                )
                
                return self._build_result(
                    success=True,
                    data=result_data,
                    start_time=start_time,
                )
            
            # Handle dict input
            elif isinstance(scenario_config, dict):
                self.reason("Converting dict input to ScenarioConfig")
                config = self._parse_dict_input(scenario_config)
                context["scenario_config"] = config
                return self.execute(context)
            
            else:
                return self._build_result(
                    success=False,
                    error=f"Unsupported input type: {type(scenario_config)}",
                    start_time=start_time,
                )
        
        except Exception as e:
            return self._build_result(
                success=False,
                error=str(e),
                start_time=start_time,
            )
    
    def _validate_scenario(self, config: ScenarioConfig) -> dict[str, Any]:
        """Validate a scenario configuration."""
        errors = []
        
        if not config.nodes:
            errors.append("No nodes defined in scenario")
        
        if not config.edges:
            errors.append("No edges defined in scenario")
        
        # Check for duplicate node IDs
        node_ids = [n.id for n in config.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("Duplicate node IDs found")
        
        # Check edge references
        node_id_set = set(node_ids)
        for edge in config.edges:
            if edge.source_id not in node_id_set:
                errors.append(f"Edge references unknown source: {edge.source_id}")
            if edge.target_id not in node_id_set:
                errors.append(f"Edge references unknown target: {edge.target_id}")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def _enrich_nodes(self, nodes: list[SystemNode]) -> list[SystemNode]:
        """Enrich nodes with computed default properties."""
        for node in nodes:
            # Ensure reasonable defaults
            if node.health_score <= 0:
                node.health_score = 1.0
            if node.load_capacity <= 0:
                node.load_capacity = 1.0
            if node.current_load < 0:
                node.current_load = 0.3
        
        return nodes
    
    def _validate_edges(
        self, edges: list[SystemEdge], nodes: list[SystemNode]
    ) -> list[SystemEdge]:
        """Validate and filter edges to only reference existing nodes."""
        node_ids = {n.id for n in nodes}
        valid_edges = [
            e for e in edges
            if e.source_id in node_ids and e.target_id in node_ids
        ]
        return valid_edges
    
    def _parse_dict_input(self, data: dict) -> ScenarioConfig:
        """Parse a dictionary into a ScenarioConfig."""
        nodes = []
        for node_data in data.get("nodes", []):
            nodes.append(SystemNode(**node_data))
        
        edges = []
        for edge_data in data.get("edges", []):
            edges.append(SystemEdge(**edge_data))
        
        return ScenarioConfig(
            name=data.get("name", "Custom Scenario"),
            description=data.get("description", ""),
            nodes=nodes,
            edges=edges,
            initial_failures=data.get("initial_failures", []),
            external_factors=data.get("external_factors", []),
            business_context=data.get("business_context", {}),
            simulation_duration_seconds=data.get("duration", 300.0),
            complexity_level=data.get("complexity", "medium"),
        )