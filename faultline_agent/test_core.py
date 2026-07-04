"""
Quick verification test for Faultline core logic.
Run: python test_core.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from scenarios.ecommerce import build_ecommerce_scenario
from scenarios.banking import build_banking_scenario
from scenarios.cicd import build_cicd_scenario
from agents.orchestrator import AgentOrchestrator


def test_scenario(name, builder_func):
    """Test a single scenario through the full pipeline."""
    print(f"\n{'='*60}")
    print(f"  Testing: {name}")
    print(f"{'='*60}")
    
    orchestrator = AgentOrchestrator()
    scenario = builder_func()
    
    print(f"  Nodes: {len(scenario.nodes)}, Edges: {len(scenario.edges)}")
    
    # Run full pipeline
    result = orchestrator.run_full_pipeline(scenario=scenario, stress_mode="auto")
    
    if "error" in result:
        print(f"  [FAIL] ERROR: {result['error']}")
        return False
    
    print(f"  [OK] Pipeline Status: {result['status']}")
    print(f"  Time: {result.get('pipeline_time_ms', 0):.0f}ms")
    
    # Check summary
    summary = result.get("summary")
    if summary:
        print(f"  Risk Score: {summary.get('risk_score', 0):.0%}")
        print(f"  Risk Level: {summary.get('risk_level', 'N/A')}")
        insights = summary.get("insights", [])
        print(f"  Insights Generated: {len(insights)}")
        recs = summary.get("recommendations", [])
        print(f"  Recommendations: {len(recs)}")
    
    # Check graph
    graph_data = result.get("graph_data", {})
    metrics = graph_data.get("metrics", {})
    print(f"  Graph Density: {metrics.get('density', 0):.3f}")
    print(f"  Connected: {metrics.get('is_connected', False)}")
    
    # Test interactive failure
    if orchestrator.graph.nodes:
        first_node = list(orchestrator.graph.nodes.keys())[0]
        interactive = orchestrator.run_interactive_failure(
            node_id=first_node,
            stress_type="load_spike",
            intensity=0.8,
        )
        if "error" not in interactive:
            prop = interactive.get("propagation", {})
            print(f"  Interactive Test: {prop.get('total_affected', 0)} nodes affected")
        else:
            print(f"  [FAIL] Interactive Error: {interactive['error']}")
    
    # Test fragility report
    fragility = orchestrator.get_fragility_report()
    if "error" not in fragility:
        spofs = fragility.get("single_points_of_failure", [])
        top_fragile = fragility.get("top_fragile_nodes", [])
        print(f"  SPOFs: {len(spofs)}")
        print(f"  Top Fragile Nodes: {len(top_fragile)}")
    
    return True


def main():
    print("\n" + "="*60)
    print("  FAULTLINE - Core Logic Verification Test")
    print("="*60)
    
    tests = [
        ("E-Commerce Platform", build_ecommerce_scenario),
        ("Banking System", build_banking_scenario),
        ("CI/CD & Microservices", build_cicd_scenario),
    ]
    
    results = []
    for name, builder in tests:
        try:
            success = test_scenario(name, builder)
            results.append((name, success))
        except Exception as e:
            print(f"  [EXCEPTION] {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "="*60)
    print("  TEST RESULTS")
    print("="*60)
    
    all_passed = True
    for name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"  {status} - {name}")
        if not success:
            all_passed = False
    
    print(f"\n  Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())