"""
Scenario Controller Agent
Manages scenario selection, configuration, and orchestrates
the flow between different simulation views.
"""

from __future__ import annotations
from typing import Any
from datetime import datetime
from agents.base_agent import BaseAgent, AgentResult
from core.models import ScenarioConfig
from config import AVAILABLE_SCENARIOS


class ScenarioAgent(BaseAgent):
    """
    Controls scenario lifecycle - selection, initialization,
    parameter tuning, and view switching.
    """
    
    def __init__(self):
        super().__init__(
            name="ScenarioAgent",
            description="Manages scenario selection and simulation flow control"
        )
        self._active_scenario: str = ""
        self._scenario_history: list[str] = []
    
    def execute(self, context: dict[str, Any]) -> AgentResult:
        """
        Handle scenario operations.
        
        Expected context:
            - action: "select" | "configure" | "switch" | "list"
            - scenario_id: ID of scenario to operate on
            - parameters: Optional configuration overrides
        """
        start_time = datetime.now()
        
        try:
            action = context.get("action", "list")
            scenario_id = context.get("scenario_id", "")
            parameters = context.get("parameters", {})
            
            self.reason(f"Scenario action: {action}")
            
            if action == "list":
                result_data = self._list_scenarios()
            elif action == "select":
                result_data = self._select_scenario(scenario_id, parameters)
            elif action == "configure":
                result_data = self._configure_scenario(scenario_id, parameters)
            elif action == "switch":
                result_data = self._switch_scenario(scenario_id)
            else:
                return self._build_result(
                    success=False,
                    error=f"Unknown action: {action}",
                    start_time=start_time,
                )
            
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
    
    def _list_scenarios(self) -> dict[str, Any]:
        """List all available scenarios."""
        return {
            "scenarios": AVAILABLE_SCENARIOS,
            "active_scenario": self._active_scenario,
            "history": self._scenario_history,
        }
    
    def _select_scenario(self, scenario_id: str, parameters: dict) -> dict[str, Any]:
        """Select and activate a scenario."""
        if scenario_id not in AVAILABLE_SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_id}")
        
        self._active_scenario = scenario_id
        self._scenario_history.append(scenario_id)
        
        scenario_info = AVAILABLE_SCENARIOS[scenario_id]
        
        self.reason(f"Selected scenario: {scenario_info['name']}")
        
        return {
            "selected": scenario_id,
            "info": scenario_info,
            "parameters": parameters,
            "status": "ready",
        }
    
    def _configure_scenario(self, scenario_id: str, parameters: dict) -> dict[str, Any]:
        """Configure scenario parameters."""
        return {
            "scenario_id": scenario_id or self._active_scenario,
            "applied_parameters": parameters,
            "status": "configured",
        }
    
    def _switch_scenario(self, scenario_id: str) -> dict[str, Any]:
        """Switch to a different scenario."""
        previous = self._active_scenario
        result = self._select_scenario(scenario_id, {})
        result["previous_scenario"] = previous
        return result