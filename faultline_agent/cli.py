"""
Faultline CLI
Command-line interface for running fragility analysis without the UI.
Demonstrates agent skills via direct CLI interaction.

Usage:
    python cli.py analyze ecommerce
    python cli.py analyze banking --mode worst_case
    python cli.py inject ecommerce payment_gateway load_spike --intensity 0.9
    python cli.py status
    python cli.py list-nodes ecommerce
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import json
from datetime import datetime

from agents.orchestrator import AgentOrchestrator
from scenarios.ecommerce import build_ecommerce_scenario
from scenarios.banking import build_banking_scenario
from scenarios.cicd import build_cicd_scenario
from core.models import StressType


# ANSI colors for terminal output
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def get_scenario(name: str):
    """Get scenario builder by name."""
    builders = {
        "ecommerce": build_ecommerce_scenario,
        "banking": build_banking_scenario,
        "cicd": build_cicd_scenario,
    }
    builder = builders.get(name)
    if not builder:
        print(f"{Colors.RED}Unknown scenario: {name}{Colors.RESET}")
        print(f"Available: {', '.join(builders.keys())}")
        sys.exit(1)
    return builder()


def cmd_analyze(args):
    """Run full fragility analysis on a scenario."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  FAULTLINE - Fragility Analysis{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    scenario = get_scenario(args.scenario)
    print(f"  Scenario: {Colors.BOLD}{scenario.name}{Colors.RESET}")
    print(f"  Mode: {args.mode}")
    print(f"  Nodes: {len(scenario.nodes)}, Edges: {len(scenario.edges)}")
    print(f"\n  Running multi-agent pipeline...")
    
    orchestrator = AgentOrchestrator()
    result = orchestrator.run_full_pipeline(scenario=scenario, stress_mode=args.mode)
    
    if "error" in result:
        print(f"\n  {Colors.RED}ERROR: {result['error']}{Colors.RESET}")
        return
    
    print(f"  {Colors.GREEN}Complete in {result.get('pipeline_time_ms', 0):.0f}ms{Colors.RESET}\n")
    
    # Summary
    summary = result.get("summary", {})
    if summary:
        risk_score = summary.get("risk_score", 0)
        risk_level = summary.get("risk_level", "N/A")
        
        color = Colors.GREEN if risk_score < 0.4 else Colors.YELLOW if risk_score < 0.7 else Colors.RED
        print(f"  {Colors.BOLD}Risk Score: {color}{risk_score:.0%}{Colors.RESET} ({risk_level})")
        print(f"  {Colors.DIM}{summary.get('summary', '')}{Colors.RESET}\n")
        
        # Insights
        insights = summary.get("insights", [])
        if insights:
            print(f"  {Colors.BOLD}Fragility Insights ({len(insights)}):{Colors.RESET}")
            for i, insight in enumerate(insights[:5], 1):
                sev = insight.get("severity", "medium")
                sev_color = Colors.RED if sev in ("critical", "catastrophic") else Colors.YELLOW
                print(f"    {sev_color}[{sev.upper()}]{Colors.RESET} {insight.get('title', '')}")
            print()
        
        # Recommendations
        recs = summary.get("recommendations", [])
        if recs:
            print(f"  {Colors.BOLD}Recommendations ({len(recs)}):{Colors.RESET}")
            for i, rec in enumerate(recs[:5], 1):
                print(f"    {Colors.CYAN}#{i}{Colors.RESET} {rec.get('recommendation', '')}")
    
    # Fragility report
    fragility = orchestrator.get_fragility_report()
    if "error" not in fragility:
        spofs = fragility.get("single_points_of_failure", [])
        if spofs:
            print(f"\n  {Colors.BOLD}{Colors.RED}Single Points of Failure ({len(spofs)}):{Colors.RESET}")
            for spof in spofs:
                print(f"    {Colors.RED}!{Colors.RESET} {spof.get('name', spof.get('node_id', '?'))}")
    
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}\n")


def cmd_inject(args):
    """Inject a failure into a specific node."""
    print(f"\n{Colors.BOLD}{Colors.RED}  FAULTLINE - Failure Injection{Colors.RESET}\n")
    
    scenario = get_scenario(args.scenario)
    orchestrator = AgentOrchestrator()
    orchestrator.run_full_pipeline(scenario=scenario, stress_mode="auto")
    
    # Validate node
    if args.node_id not in orchestrator.graph.nodes:
        print(f"  {Colors.RED}Node '{args.node_id}' not found.{Colors.RESET}")
        print(f"  Available nodes:")
        for nid, node in orchestrator.graph.nodes.items():
            print(f"    {nid}: {node.name} ({node.node_type})")
        return
    
    # Validate stress type
    valid_types = [s.value for s in StressType]
    if args.stress_type not in valid_types:
        print(f"  {Colors.RED}Invalid stress type: {args.stress_type}{Colors.RESET}")
        print(f"  Available: {', '.join(valid_types)}")
        return
    
    node = orchestrator.graph.nodes[args.node_id]
    print(f"  Target: {Colors.BOLD}{node.name}{Colors.RESET} ({node.node_type})")
    print(f"  Stress: {args.stress_type}")
    print(f"  Intensity: {args.intensity}")
    print(f"\n  Injecting failure...")
    
    result = orchestrator.run_interactive_failure(
        node_id=args.node_id,
        stress_type=args.stress_type,
        intensity=args.intensity,
    )
    
    if "error" in result:
        print(f"  {Colors.RED}ERROR: {result['error']}{Colors.RESET}")
        return
    
    prop = result.get("propagation", {})
    event = result.get("event", {})
    
    print(f"\n  {Colors.BOLD}Result:{Colors.RESET}")
    print(f"    Description: {event.get('description', 'N/A')}")
    print(f"    Severity: {Colors.RED}{prop.get('severity', 'N/A')}{Colors.RESET}")
    print(f"    Nodes Affected: {prop.get('total_affected', 0)}")
    print(f"    Cascade Depth: {prop.get('max_depth', 0)}")
    
    # Show affected nodes
    node_states = result.get("node_states", {})
    affected = [(nid, d) for nid, d in node_states.items() if d.get("status") != "healthy"]
    if affected:
        print(f"\n  {Colors.BOLD}Affected Nodes:{Colors.RESET}")
        for nid, data in sorted(affected, key=lambda x: x[1].get("health", 1)):
            status = data.get("status", "?")
            health = data.get("health", 0)
            name = data.get("name", nid)
            color = Colors.RED if status in ("dead", "failing") else Colors.YELLOW
            print(f"    {color}{status:10s}{Colors.RESET} {name} ({health:.0%})")
    
    # Recommendations
    recs = prop.get("recommendations", [])
    if recs:
        print(f"\n  {Colors.BOLD}Recommendations:{Colors.RESET}")
        for rec in recs:
            print(f"    - {rec}")
    
    print()


def cmd_list_nodes(args):
    """List all nodes in a scenario."""
    scenario = get_scenario(args.scenario)
    
    print(f"\n{Colors.BOLD}  Nodes in {scenario.name}:{Colors.RESET}\n")
    print(f"  {'ID':<20} {'Name':<30} {'Type':<15} {'Tier'}")
    print(f"  {'-'*20} {'-'*30} {'-'*15} {'-'*4}")
    
    for node in sorted(scenario.nodes, key=lambda n: n.tier):
        tier_color = Colors.RED if node.tier == 1 else Colors.YELLOW if node.tier == 2 else Colors.DIM
        print(f"  {node.id:<20} {node.name:<30} {node.node_type:<15} {tier_color}T{node.tier}{Colors.RESET}")
    
    print(f"\n  Total: {len(scenario.nodes)} nodes, {len(scenario.edges)} edges\n")


def cmd_mcp(args):
    """Start the MCP server."""
    print(f"Starting Faultline MCP Server...", file=sys.stderr)
    from mcp_server import main as mcp_main
    mcp_main()


def cmd_adk(args):
    """Run the ADK 2.0 agent (chat or workflow mode)."""
    import asyncio
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    if args.adk_mode == "chat":
        if args.prompt:
            from app.runner import run_chat
            response = asyncio.run(run_chat(args.prompt))
            print(response)
        else:
            from app.runner import interactive_session
            asyncio.run(interactive_session())
    elif args.adk_mode == "workflow":
        from app.runner import run_workflow
        import json
        prompt = args.prompt or "ecommerce auto"
        result = asyncio.run(run_workflow(prompt))
        print(json.dumps(result, indent=2, default=str))
    elif args.adk_mode == "interactive":
        from app.runner import interactive_session
        asyncio.run(interactive_session())
    else:
        from app.runner import interactive_session
        asyncio.run(interactive_session())


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="faultline",
        description="Faultline: System Fragility Intelligence Agent CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Run fragility analysis")
    analyze_parser.add_argument("scenario", choices=["ecommerce", "banking", "cicd"])
    analyze_parser.add_argument("--mode", default="auto", choices=["auto", "targeted", "random", "worst_case"])
    
    # inject command
    inject_parser = subparsers.add_parser("inject", help="Inject a failure")
    inject_parser.add_argument("scenario", choices=["ecommerce", "banking", "cicd"])
    inject_parser.add_argument("node_id", help="Node ID to target")
    inject_parser.add_argument("stress_type", help="Type of stress to apply")
    inject_parser.add_argument("--intensity", type=float, default=0.8)
    
    # list-nodes command
    list_parser = subparsers.add_parser("list-nodes", help="List scenario nodes")
    list_parser.add_argument("scenario", choices=["ecommerce", "banking", "cicd"])
    
    # mcp command
    subparsers.add_parser("mcp", help="Start MCP server")
    
    # adk command (ADK 2.0 agent)
    adk_parser = subparsers.add_parser("adk", help="Run ADK 2.0 agent")
    adk_parser.add_argument(
        "adk_mode",
        nargs="?",
        default="interactive",
        choices=["chat", "workflow", "interactive"],
        help="Agent mode: chat (single-turn), workflow (pipeline), interactive (REPL)",
    )
    adk_parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Prompt for chat/workflow mode",
    )
    
    args = parser.parse_args()
    
    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "inject":
        cmd_inject(args)
    elif args.command == "list-nodes":
        cmd_list_nodes(args)
    elif args.command == "mcp":
        cmd_mcp(args)
    elif args.command == "adk":
        cmd_adk(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()