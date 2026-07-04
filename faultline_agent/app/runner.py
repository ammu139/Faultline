"""
Faultline ADK Runner
Programmatic runner for the Faultline ADK agent.
Supports both interactive chat and pipeline workflow execution.

Usage:
    python -m app.runner "analyze the ecommerce system"
    python -m app.runner --workflow "banking worst_case"
    python -m app.runner --interactive
"""

from __future__ import annotations
import sys
import os
import asyncio
import argparse

# Ensure faultline root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from google.adk.runners import Runner, InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.adk.apps import App
from google.genai import types


async def run_chat(prompt: str, session_id: str = "default") -> str:
    """Run a single chat turn with the Faultline agent.
    
    Args:
        prompt: User message to send to the agent.
        session_id: Session ID for conversation continuity.
    
    Returns:
        The agent's response text.
    """
    from app.agent import root_agent

    app = App(name="app", root_agent=root_agent)
    runner = InMemoryRunner(app=app)

    session = await runner.session_service.create_session(
        app_name="app", user_id="user", session_id=session_id
    )

    response_text = ""
    async for event in runner.run_async(
        user_id="user",
        session_id=session.id,
        new_message=types.Content(
            role="user", parts=[types.Part.from_text(text=prompt)]
        ),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text or ""

    return response_text


async def run_workflow(prompt: str) -> dict:
    """Run the full pipeline workflow.
    
    Args:
        prompt: Input describing scenario and mode (e.g., "ecommerce auto")
    
    Returns:
        The workflow output as a dict.
    """
    from app.workflow import pipeline_workflow

    app = App(name="app", root_agent=pipeline_workflow)
    runner = InMemoryRunner(app=app)

    session = await runner.session_service.create_session(
        app_name="app", user_id="user"
    )

    result = None
    async for event in runner.run_async(
        user_id="user",
        session_id=session.id,
        new_message=types.Content(
            role="user", parts=[types.Part.from_text(text=prompt)]
        ),
    ):
        if hasattr(event, 'output') and event.output is not None:
            result = event.output

    return result or {}


async def interactive_session():
    """Run an interactive chat session with the Faultline agent."""
    from app.agent import root_agent

    print("\n⚡ FAULTLINE — System Fragility Intelligence Agent (ADK 2.0)")
    print("=" * 60)
    print("Type your questions about system fragility. Type 'quit' to exit.\n")
    print("Examples:")
    print("  • 'Analyze the ecommerce system'")
    print("  • 'What are the single points of failure?'")
    print("  • 'Inject a load_spike failure into payment_gateway at 0.9 intensity'")
    print("  • 'Show me the fragility report'")
    print("=" * 60 + "\n")

    app = App(name="app", root_agent=root_agent)
    runner = InMemoryRunner(app=app)

    session = await runner.session_service.create_session(
        app_name="app", user_id="user", session_id="interactive"
    )

    while True:
        try:
            prompt = input("\n🧑 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break

        if not prompt:
            continue
        if prompt.lower() in ("quit", "exit", "q"):
            print("\nGoodbye!")
            break

        print("\n🤖 Faultline: ", end="", flush=True)

        response_text = ""
        async for event in runner.run_async(
            user_id="user",
            session_id=session.id,
            new_message=types.Content(
                role="user", parts=[types.Part.from_text(text=prompt)]
            ),
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[0].text or ""

        if response_text:
            print(response_text)
        else:
            print("(No response generated)")


def main():
    """CLI entry point for the ADK runner."""
    parser = argparse.ArgumentParser(
        prog="faultline-adk",
        description="Faultline ADK 2.0 Agent Runner",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Prompt to send to the agent (single-turn mode)",
    )
    parser.add_argument(
        "--workflow",
        action="store_true",
        help="Run the full pipeline workflow instead of chat agent",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start an interactive chat session",
    )
    parser.add_argument(
        "--session-id",
        default="default",
        help="Session ID for conversation continuity",
    )

    args = parser.parse_args()

    if args.interactive:
        asyncio.run(interactive_session())
    elif args.prompt:
        if args.workflow:
            result = asyncio.run(run_workflow(args.prompt))
            import json
            print(json.dumps(result, indent=2, default=str))
        else:
            response = asyncio.run(run_chat(args.prompt, session_id=args.session_id))
            print(response)
    else:
        # Default to interactive mode
        asyncio.run(interactive_session())


if __name__ == "__main__":
    main()