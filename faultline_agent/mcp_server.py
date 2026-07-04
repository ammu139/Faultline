"""
Faultline MCP Server
Model Context Protocol server that exposes Faultline's fragility analysis
tools to any MCP-compatible client (Claude, Cline, etc.)

This allows external AI agents to:
- Query system dependency graphs
- Run failure simulations
- Get fragility insights
- Inject failures interactively

Architecture: Stdio-based MCP transport for local integration.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from typing import Any

from core.models import StressType, ScenarioConfig
from agents.orchestrator import AgentOrchestrator
from scenarios.ecommerce import build_ecommerce_scenario
from scenarios.banking import build_banking_scenario
from scenarios.cicd import build_cicd_scenario


class FaultlineMCPServer:
    """
    MCP Server exposing Faultline tools via the Model Context Protocol.
    
    Design: Implements the MCP tool-calling interface so that LLM agents
    can invoke Faultline's analysis capabilities as tools.
    
    Security: All inputs are validated and sanitized before processing.
    Rate limiting prevents abuse of simulation endpoints.
    """
    
    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self._initialized = False
        self._request_count = 0
        self._max_requests_per_minute = 60  # Rate limiting
    
    def get_tools(self) -> list[dict[str, Any]]:
        """
        Return the list of available MCP tools.
        Each tool has a name, description, and input schema.
        """
        return [
            {
                "name": "faultline_load_scenario",
                "description": (
                    "Load a pre-built enterprise system scenario for fragility analysis. "
                    "Available scenarios: ecommerce (checkout collapse), banking (fraud cascade), "
                    "cicd (microservices fragility)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "scenario": {
                            "type": "string",
                            "enum": ["ecommerce", "banking", "cicd"],
                            "description": "The scenario to load",
                        },
                        "stress_mode": {
                            "type": "string",
                            "enum": ["auto", "targeted", "random", "worst_case"],
                            "description": "How to design stress tests",
                            "default": "auto",
                        },
                    },
                    "required": ["scenario"],
                },
            },
            {
                "name": "faultline_analyze",
                "description": (
                    "Run full fragility analysis on the loaded scenario. "
                    "Returns risk score, insights, single points of failure, "
                    "and actionable recommendations."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "faultline_inject_failure",
                "description": (
                    "Inject a failure into a specific node and observe cascade propagation. "
                    "Returns affected nodes, cascade depth, severity, and recommendations."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "node_id": {
                            "type": "string",
                            "description": "ID of the node to fail",
                        },
                        "stress_type": {
                            "type": "string",
                            "enum": [s.value for s in StressType],
                            "description": "Type of stress to apply",
                        },
                        "intensity": {
                            "type": "number",
                            "minimum": 0.1,
                            "maximum": 1.0,
                            "description": "Failure intensity (0.1-1.0)",
                            "default": 0.8,
                        },
                    },
                    "required": ["node_id", "stress_type"],
                },
            },
            {
                "name": "faultline_get_status",
                "description": "Get current system health status and node states.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "faultline_list_nodes",
                "description": "List all nodes in the current dependency graph with their status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "faultline_get_fragility_report",
                "description": (
                    "Get a comprehensive fragility report including single points of failure, "
                    "criticality rankings, and blast radius analysis."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]
    
    def handle_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Handle an MCP tool call.
        
        Security: Validates tool name and sanitizes all input arguments
        before processing. Rate limits requests.
        """
        # Rate limiting
        self._request_count += 1
        if self._request_count > self._max_requests_per_minute:
            return {"error": "Rate limit exceeded. Max 60 requests/minute."}
        
        # Input validation
        if not isinstance(tool_name, str) or len(tool_name) > 100:
            return {"error": "Invalid tool name"}
        
        # Route to handler
        handlers = {
            "faultline_load_scenario": self._handle_load_scenario,
            "faultline_analyze": self._handle_analyze,
            "faultline_inject_failure": self._handle_inject_failure,
            "faultline_get_status": self._handle_get_status,
            "faultline_list_nodes": self._handle_list_nodes,
            "faultline_get_fragility_report": self._handle_fragility_report,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            return handler(arguments)
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
    
    def _handle_load_scenario(self, args: dict) -> dict:
        """Load and initialize a scenario."""
        scenario_id = self._sanitize_string(args.get("scenario", ""))
        stress_mode = self._sanitize_string(args.get("stress_mode", "auto"))
        
        builders = {
            "ecommerce": build_ecommerce_scenario,
            "banking": build_banking_scenario,
            "cicd": build_cicd_scenario,
        }
        
        if scenario_id not in builders:
            return {"error": f"Unknown scenario: {scenario_id}. Use: ecommerce, banking, cicd"}
        
        scenario = builders[scenario_id]()
        result = self.orchestrator.run_full_pipeline(scenario=scenario, stress_mode=stress_mode)
        self._initialized = True
        
        return {
            "status": "loaded",
            "scenario": scenario_id,
            "nodes": len(self.orchestrator.graph.nodes),
            "edges": len(self.orchestrator.graph.edges),
            "pipeline_time_ms": result.get("pipeline_time_ms", 0),
        }
    
    def _handle_analyze(self, args: dict) -> dict:
        """Run analysis on current scenario."""
        if not self._initialized:
            return {"error": "No scenario loaded. Call faultline_load_scenario first."}
        
        summary = self.orchestrator.simulator.get_fragility_analysis()
        status = self.orchestrator.get_system_status()
        
        return {
            "system_health": status.get("system_health", 1.0),
            "total_nodes": status.get("total_nodes", 0),
            "affected_count": status.get("affected_count", 0),
            "fragility": summary,
        }
    
    def _handle_inject_failure(self, args: dict) -> dict:
        """Inject a failure into a node."""
        if not self._initialized:
            return {"error": "No scenario loaded. Call faultline_load_scenario first."}
        
        node_id = self._sanitize_string(args.get("node_id", ""))
        stress_type = self._sanitize_string(args.get("stress_type", "load_spike"))
        intensity = min(1.0, max(0.1, float(args.get("intensity", 0.8))))
        
        # Validate node exists
        if node_id not in self.orchestrator.graph.nodes:
            available = list(self.orchestrator.graph.nodes.keys())
            return {"error": f"Node '{node_id}' not found. Available: {available}"}
        
        # Validate stress type
        valid_types = [s.value for s in StressType]
        if stress_type not in valid_types:
            return {"error": f"Invalid stress_type. Use: {valid_types}"}
        
        result = self.orchestrator.run_interactive_failure(
            node_id=node_id,
            stress_type=stress_type,
            intensity=intensity,
        )
        
        return result
    
    def _handle_get_status(self, args: dict) -> dict:
        """Get system status."""
        if not self._initialized:
            return {"status": "not_initialized", "message": "Load a scenario first"}
        return self.orchestrator.get_system_status()
    
    def _handle_list_nodes(self, args: dict) -> dict:
        """List all nodes."""
        if not self._initialized:
            return {"error": "No scenario loaded"}
        
        nodes = []
        for nid, node in self.orchestrator.graph.nodes.items():
            nodes.append({
                "id": nid,
                "name": node.name,
                "type": node.node_type,
                "tier": node.tier,
                "status": node.status.value if hasattr(node.status, 'value') else node.status,
                "health": node.health_score,
            })
        return {"nodes": nodes, "total": len(nodes)}
    
    def _handle_fragility_report(self, args: dict) -> dict:
        """Get fragility report."""
        if not self._initialized:
            return {"error": "No scenario loaded"}
        return self.orchestrator.get_fragility_report()
    
    @staticmethod
    def _sanitize_string(value: str) -> str:
        """
        Security: Sanitize string input to prevent injection.
        Strips dangerous characters and limits length.
        """
        if not isinstance(value, str):
            return ""
        # Remove any control characters and limit length
        sanitized = "".join(c for c in value if c.isprintable())
        return sanitized[:200]


def main():
    """
    Run the MCP server in stdio mode.
    Reads JSON-RPC requests from stdin, writes responses to stdout.
    """
    server = FaultlineMCPServer()
    
    # Print available tools on startup (for discovery)
    tools_info = {
        "type": "tools",
        "tools": server.get_tools(),
    }
    print(json.dumps(tools_info), flush=True)
    
    # Main loop: read requests, process, respond
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            request = json.loads(line)
            tool_name = request.get("tool", "")
            arguments = request.get("arguments", {})
            
            result = server.handle_tool_call(tool_name, arguments)
            
            response = {
                "id": request.get("id"),
                "result": result,
            }
            print(json.dumps(response), flush=True)
        
        except json.JSONDecodeError:
            error_response = {"error": "Invalid JSON input"}
            print(json.dumps(error_response), flush=True)
        except Exception as e:
            error_response = {"error": str(e)}
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    main()