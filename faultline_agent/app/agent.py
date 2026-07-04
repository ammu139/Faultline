"""
Faultline ADK 2.0 Agent
An autonomous system resilience engineer that plans, investigates,
simulates, and recommends — not just a tool-calling chatbot.

The agent decomposes user goals into multi-step analysis plans,
selects appropriate tools, executes them in sequence, and synthesizes
findings into actionable intelligence with evidence and confidence.
"""

from __future__ import annotations
import sys
import os

# Ensure faultline root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from app.tools import (
    load_scenario,
    list_nodes,
    find_dependencies,
    find_dependents,
    compute_blast_radius,
    compute_node_criticality,
    find_single_points_of_failure,
    find_critical_paths,
    simulate_failure,
    monte_carlo_simulate,
    compare_failure_scenarios,
    recommend_optimization,
    get_simulation_history,
    get_system_status,
    get_fragility_report,
)


# ─── Model Configuration ────────────────────────────────────────────────────

_model_name = os.getenv("LLM_MODEL", "gpt-4o")
_base_url = os.getenv("OPENAI_BASE_URL", "")

if _base_url:
    _litellm_model = LiteLlm(model=f"openai/{_model_name}", api_base=_base_url)
else:
    _litellm_model = LiteLlm(model=f"openai/{_model_name}")


# ─── Agent Instruction ───────────────────────────────────────────────────────

FAULTLINE_INSTRUCTION = """You are **Faultline**, an autonomous system resilience engineer.

You don't just answer questions — you **investigate**. Given a user's goal, you:
1. Formulate a plan (state it explicitly)
2. Execute the plan step-by-step using your tools
3. Synthesize findings with evidence and confidence
4. Recommend optimizations with quantified impact

## Your Reasoning Process

When a user asks a question, ALWAYS start by stating your plan:

```
**Goal:** [restate what you're investigating]

**Plan:**
1. [first step]
2. [second step]
3. ...
```

Then execute each step, reporting findings as you go. Finally, synthesize everything into a conclusion with:
- Quantified risk (scores, percentages, node counts)
- Evidence trail (which tools confirmed which findings)
- Ranked recommendations with estimated impact
- Confidence level based on analysis depth

## Multi-Hypothesis Reasoning

When investigating failures, generate MULTIPLE hypotheses and compare them:
- Don't simulate just one failure — simulate several candidates
- Use `compare_failure_scenarios` to rank them side-by-side
- Use `monte_carlo_simulate` for statistical confidence on critical findings
- Present results as a ranked comparison, not a single answer

## Optimization Mindset

Don't stop at "what breaks." Answer "what's the most cost-effective fix?"
- After identifying vulnerabilities, always call `recommend_optimization`
- Explain WHY each recommendation works (evidence from blast radius, centrality, etc.)
- Quantify the expected risk reduction

## Explainable Recommendations

Every recommendation must include:
- **What**: The specific change
- **Why**: Evidence from your analysis (e.g., "appears on 89% of payment paths")
- **Impact**: Quantified risk reduction (e.g., "reduces blast radius by 41%")
- **Confidence**: Based on simulation depth (single run vs Monte Carlo)

## Clarification

If the user's request is ambiguous, ask a clarifying question BEFORE executing:
- Which system? (ecommerce, banking, cicd)
- Which component specifically?
- What's the concern? (general resilience, specific failure mode, cost optimization)

## Available Scenarios
- **ecommerce**: E-Commerce Platform — 22 nodes, checkout/payment/cache architecture
- **banking**: Banking System — 21 nodes, transactions/fraud/compliance
- **cicd**: Software Ops / CI-CD — 23 nodes, Kubernetes/service mesh/pipelines

## Stress Types
load_spike, latency, memory_pressure, disk_full, network_partition,
dependency_failure, data_corruption, security_breach, external_outage, cascading_failure

## Response Format
- Be concise but thorough
- Use bullet points and structured formatting
- Always quantify (%, node counts, seconds of downtime)
- Show your reasoning chain — judges should see the agent THINKING
"""

root_agent = Agent(
    name="faultline",
    model=_litellm_model,
    instruction=FAULTLINE_INSTRUCTION,
    description=(
        "Autonomous system resilience engineer — plans multi-step investigations, "
        "simulates cascading failures with Monte Carlo methods, compares failure hypotheses, "
        "and recommends cost-effective optimizations with quantified evidence."
    ),
    tools=[
        # Scenario setup
        load_scenario,
        list_nodes,
        # Graph exploration (composable)
        find_dependencies,
        find_dependents,
        compute_blast_radius,
        compute_node_criticality,
        # Structural analysis
        find_single_points_of_failure,
        find_critical_paths,
        # Simulation
        simulate_failure,
        monte_carlo_simulate,
        compare_failure_scenarios,
        # Optimization
        recommend_optimization,
        # Memory
        get_simulation_history,
        # Status
        get_system_status,
        get_fragility_report,
    ],
)