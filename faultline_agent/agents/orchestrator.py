"""
Agent Orchestrator
Coordinates the multi-agent pipeline, managing execution order,
data flow between agents, and the overall simulation lifecycle.
"""

from __future__ import annotations
from typing import Any, Optional
from datetime import datetime
from agents.base_agent import BaseAgent, AgentResult, AgentMessage
from agents.ingestion_agent import IngestionAgent
from agents.dependency_agent import DependencyAgent
from agents.stress_agent import StressAgent
from agents.propagation_agent import PropagationAgent
from agents.insight_agent import InsightAgent
from agents.scenario_agent import ScenarioAgent
from core.graph_builder import SystemGraph
from core.failure_engine import FailureEngine
from core.simulator import FaultlineSimulator
from core.models import ScenarioConfig


class AgentOrchestrator:
    """
    Central orchestrator for the multi-agent system.
    Manages agent lifecycle, message routing, and pipeline execution.
    """
    
    def __init__(self):
        # Core components
        self.graph = SystemGraph()
        self.engine: Optional[FailureEngine] = None
        self.simulator = FaultlineSimulator()
        
        # Initialize agents
        self.ingestion_agent = IngestionAgent()
        self.dependency_agent = DependencyAgent(self.graph)
        self.stress_agent = StressAgent(self.graph)
        self.propagation_agent: Optional[PropagationAgent] = None
        self.insight_agent = InsightAgent()
        self.scenario_agent = ScenarioAgent()
        
        # Agent registry
        self.agents: dict[str, BaseAgent] = {
            "IngestionAgent": self.ingestion_agent,
            "DependencyAgent": self.dependency_agent,
            "StressAgent": self.stress_agent,
            "InsightAgent": self.insight_agent,
            "ScenarioAgent": self.scenario_agent,
        }
        
        # Pipeline state
        self._pipeline_results: dict[str, AgentResult] = {}
        self._is_initialized = False
        self._current_scenario: Optional[str] = None
    
    def initialize_scenario(self, scenario: ScenarioConfig) -> dict[str, Any]:
        """
        Initialize the full pipeline with a scenario.
        Runs ingestion -> dependency analysis -> ready for stress testing.
        """
        # Initialize simulator
        self.simulator.initialize(scenario)
        self.graph = self.simulator.graph
        self.engine = self.simulator.engine
        
        # Re-initialize agents with new graph
        self.dependency_agent = DependencyAgent(self.graph)
        self.stress_agent = StressAgent(self.graph)
        self.propagation_agent = PropagationAgent(self.graph, self.engine)
        
        self.agents["DependencyAgent"] = self.dependency_agent
        self.agents["StressAgent"] = self.stress_agent
        self.agents["PropagationAgent"] = self.propagation_agent
        
        self._is_initialized = True
        self._current_scenario = scenario.name
        
        return {
            "status": "initialized",
            "scenario": scenario.name,
            "nodes": len(self.graph.nodes),
            "edges": len(self.graph.edges),
        }
    
    def run_full_pipeline(
        self,
        scenario: ScenarioConfig,
        stress_mode: str = "auto",
    ) -> dict[str, Any]:
        """
        Execute the complete agent pipeline:
        1. Ingestion -> 2. Dependency Analysis -> 3. Stress Design ->
        4. Propagation -> 5. Insight Generation
        """
        pipeline_start = datetime.now()
        results = {}
        
        # Step 1: Ingestion
        ingestion_result = self.ingestion_agent.execute({
            "scenario_config": scenario,
        })
        results["ingestion"] = ingestion_result
        
        if not ingestion_result.success:
            return {"error": f"Ingestion failed: {ingestion_result.error}", "results": results}
        
        # Initialize the graph and engine
        self.initialize_scenario(scenario)
        
        # Step 2: Dependency Analysis
        dep_result = self.dependency_agent.execute({
            "scenario": scenario,
        })
        results["dependency"] = dep_result
        
        if not dep_result.success:
            return {"error": f"Dependency analysis failed: {dep_result.error}", "results": results}
        
        analysis = dep_result.data.get("analysis", {})
        
        # Step 3: Stress Design
        stress_result = self.stress_agent.execute({
            "analysis": analysis,
            "stress_mode": stress_mode,
        })
        results["stress"] = stress_result
        
        if not stress_result.success:
            return {"error": f"Stress design failed: {stress_result.error}", "results": results}
        
        stress_scenarios = stress_result.data.get("scenarios", [])
        
        # Step 4: Propagation
        prop_result = self.propagation_agent.execute({
            "scenarios": stress_scenarios,
            "propagation_depth": 5,
            "decay_factor": 0.7,
        })
        results["propagation"] = prop_result
        
        if not prop_result.success:
            return {"error": f"Propagation failed: {prop_result.error}", "results": results}
        
        prop_data = prop_result.data
        
        # Step 5: Insight Generation
        insight_result = self.insight_agent.execute({
            "propagation_results": prop_data.get("propagation_results", []),
            "analysis": analysis,
            "scenario_name": scenario.name,
        })
        results["insight"] = insight_result
        
        # Calculate pipeline execution time
        pipeline_time = (datetime.now() - pipeline_start).total_seconds() * 1000
        
        return {
            "status": "complete",
            "scenario": scenario.name,
            "pipeline_time_ms": pipeline_time,
            "results": results,
            "summary": insight_result.data if insight_result.success else None,
            "graph_data": self.graph.to_serializable(),
        }
    
    def run_interactive_failure(
        self,
        node_id: str,
        stress_type: str,
        intensity: float = 0.8,
    ) -> dict[str, Any]:
        """Run a single interactive failure injection."""
        if not self._is_initialized or not self.propagation_agent:
            return {"error": "System not initialized. Load a scenario first."}
        
        # Execute propagation
        result = self.propagation_agent.execute_single(
            node_id=node_id,
            stress_type=stress_type,
            intensity=intensity,
        )
        
        # Generate insights for this specific failure
        insight_result = self.insight_agent.execute({
            "propagation_results": [result.get("propagation", {})],
            "analysis": {},
            "scenario_name": self._current_scenario or "Interactive",
        })
        
        result["insights"] = insight_result.data if insight_result.success else None
        return result
    
    def get_fragility_report(self) -> dict[str, Any]:
        """Get a comprehensive fragility report for the current system."""
        if not self._is_initialized:
            return {"error": "System not initialized"}
        
        return self.simulator.get_fragility_analysis()
    
    def get_system_status(self) -> dict[str, Any]:
        """Get current system status."""
        if not self._is_initialized:
            return {"status": "not_initialized"}
        
        return self.simulator.get_system_status()
    
    def reset(self) -> None:
        """Reset the orchestrator and all agents."""
        self.simulator.reset()
        self._pipeline_results.clear()
        self._is_initialized = False
        self._current_scenario = None
        
        for agent in self.agents.values():
            agent.clear_messages()
            agent.reasoning_log.clear()
    
    def _route_messages(self) -> None:
        """Route messages between agents."""
        for agent in self.agents.values():
            for msg in agent.message_outbox:
                target = self.agents.get(msg.receiver)
                if target:
                    target.receive_message(msg)
            agent.message_outbox.clear()