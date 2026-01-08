#!/usr/bin/env python3
"""
Essay Writing with Critics Demo

Write an essay on any topic while critics (observers) watch your conversation
and provide feedback through the issue system.

Usage:
    python essay-with-critics.py "The impact of AI on software development"
    python essay-with-critics.py  # Uses default topic

The critics will:
1. Watch the conversation as you write
2. Create issues when they spot problems
3. You can then ask the writer to address the feedback
"""

import asyncio
import json
import sys
from pathlib import Path

# Add module paths
modules_dir = Path(__file__).parent.parent / "modules"
for module_dir in modules_dir.iterdir():
    if module_dir.is_dir() and module_dir.name.startswith("amplifier-module-"):
        sys.path.insert(0, str(module_dir))

# Add issues bundle modules (if local)
issues_modules = Path(__file__).parent.parent.parent / "amplifier-bundle-issues" / "modules"
if issues_modules.exists():
    for module_dir in issues_modules.iterdir():
        if module_dir.is_dir():
            sys.path.insert(0, str(module_dir))

from amplifier_core import ModuleLoader
from amplifier_module_orchestrator_conversation_observers import (
    ConversationObserverOrchestrator,
    ObserverConfig,
)


def get_writer_config() -> dict:
    """Configuration for the main essay writer session."""
    return {
        "session": {
            "orchestrator": {"module": "loop-streaming", "config": {}},
            "context": {"module": "context-simple", "config": {}},
        },
        "providers": [
            {
                "module": "provider-anthropic",
                "config": {"default_model": "claude-sonnet-4-20250514"},
            }
        ],
        "tools": [
            {
                "module": "tool-issue",
                "source": f"git+https://github.com/microsoft/amplifier-bundle-issues@main#subdirectory=modules/tool-issue",
                "config": {
                    "data_dir": ".essay-workspace/issues",
                    "auto_create_dir": True,
                    "actor": "writer",
                },
            },
            {
                "module": "tool-filesystem",
                "config": {"allowed_write_paths": [".essay-workspace/"]},
            },
        ],
    }


def get_critic_config() -> dict:
    """Configuration for critic/observer sessions."""
    return {
        "session": {
            "orchestrator": {"module": "loop-streaming", "config": {}},
            "context": {"module": "context-simple", "config": {}},
        },
        "providers": [
            {
                "module": "provider-anthropic",
                "config": {"default_model": "claude-sonnet-4-20250514"},
            }
        ],
        "tools": [
            {
                "module": "tool-issue",
                "source": f"git+https://github.com/microsoft/amplifier-bundle-issues@main#subdirectory=modules/tool-issue",
                "config": {
                    "data_dir": ".essay-workspace/issues",
                    "auto_create_dir": True,
                    "actor": "critic",  # Will be overridden per-critic
                },
            },
        ],
    }


def define_critics() -> list[ObserverConfig]:
    """Define the critics who will observe the essay writing."""
    critic_config = get_critic_config()

    return [
        ObserverConfig(
            name="Argument Critic",
            config=critic_config,
            role="Evaluates the strength and structure of arguments",
            focus=(
                "Look for: weak arguments, logical fallacies, unsupported claims, "
                "missing evidence, circular reasoning, strawman arguments. "
                "Suggest how to strengthen the argumentation."
            ),
        ),
        ObserverConfig(
            name="Clarity Editor",
            config=critic_config,
            role="Ensures the writing is clear and accessible",
            focus=(
                "Look for: confusing sentences, jargon without explanation, "
                "unclear transitions, ambiguous pronouns, overly complex structure. "
                "Suggest specific rewrites for clarity."
            ),
        ),
        ObserverConfig(
            name="Devil's Advocate",
            config=critic_config,
            role="Challenges assumptions and presents counterarguments",
            focus=(
                "Look for: unstated assumptions, one-sided arguments, ignored counterpoints, "
                "oversimplifications of complex issues. "
                "Suggest counterarguments that should be addressed."
            ),
        ),
    ]


async def run_essay_session(topic: str):
    """Run an interactive essay writing session with critics."""
    print("\n" + "=" * 70)
    print("  Essay Writing with Critics")
    print("=" * 70)
    print(f"\nTopic: {topic}")
    print("\nCritics watching your conversation:")
    for critic in define_critics():
        print(f"  - {critic.name}: {critic.role}")
    print("\n" + "=" * 70)

    # Setup workspace
    workspace = Path.cwd() / ".essay-workspace"
    workspace.mkdir(exist_ok=True)
    (workspace / "issues").mkdir(exist_ok=True)

    # Setup module loader
    loader = ModuleLoader(search_paths=[modules_dir])

    # Create orchestrator with critics
    async with ConversationObserverOrchestrator(
        loader=loader,
        main_config=get_writer_config(),
        observer_configs=define_critics(),
        workspace_root=workspace,
        observer_interval=20.0,  # Critics check every 20 seconds
    ) as orchestrator:
        print("\nOrchestrator ready. Critics will watch your conversation.\n")

        # Phase 1: Write the essay
        print("-" * 70)
        print("PHASE 1: Writing the essay")
        print("-" * 70)

        write_prompt = f"""Write an essay on: {topic}

Instructions:
1. Write a well-structured essay (500-800 words)
2. Include an introduction, body paragraphs, and conclusion
3. Make specific claims that can be evaluated
4. Save the essay to .essay-workspace/essay.md

Write the essay now."""

        response = await orchestrator.execute_user_message(write_prompt)
        print(f"\nWriter: {response[:500]}..." if len(response) > 500 else f"\nWriter: {response}")

        # Wait for critics to review
        print("\n" + "-" * 70)
        print("Waiting 30 seconds for critics to review...")
        print("-" * 70)
        await asyncio.sleep(30)

        # Phase 2: Address feedback
        print("\n" + "-" * 70)
        print("PHASE 2: Addressing critic feedback")
        print("-" * 70)

        feedback_prompt = """Check for any open issues from the critics.
For each issue:
1. Read the feedback carefully
2. Either revise the essay to address it, or explain why your approach is valid
3. Close the issue with a note about what you did

Then show me a summary of what feedback you received and how you addressed it."""

        response = await orchestrator.execute_user_message(feedback_prompt)
        print(f"\nWriter: {response}")

        # Optional: Another round
        print("\n" + "-" * 70)
        print("Waiting 20 seconds for critics to review changes...")
        print("-" * 70)
        await asyncio.sleep(20)

        # Final status
        print("\n" + "-" * 70)
        print("PHASE 3: Final status")
        print("-" * 70)

        final_prompt = "Give me a final summary: What was the essay about, what feedback did you receive, and what's the current state of all issues?"
        response = await orchestrator.execute_user_message(final_prompt)
        print(f"\nWriter: {response}")

    print("\n" + "=" * 70)
    print("Session complete!")
    print(f"Essay saved to: {workspace / 'essay.md'}")
    print(f"Issues stored in: {workspace / 'issues'}")
    print("=" * 70)


async def interactive_session(topic: str):
    """Run a fully interactive session where you control the flow."""
    print("\n" + "=" * 70)
    print("  Interactive Essay Writing with Critics")
    print("=" * 70)
    print(f"\nTopic: {topic}")
    print("\nCommands:")
    print("  Type your message to send to the writer")
    print("  'quit' or 'exit' to end session")
    print("  'wait <seconds>' to let critics review")
    print("\n" + "=" * 70)

    workspace = Path.cwd() / ".essay-workspace"
    workspace.mkdir(exist_ok=True)
    (workspace / "issues").mkdir(exist_ok=True)

    loader = ModuleLoader(search_paths=[modules_dir])

    async with ConversationObserverOrchestrator(
        loader=loader,
        main_config=get_writer_config(),
        observer_configs=define_critics(),
        workspace_root=workspace,
        observer_interval=15.0,
    ) as orchestrator:
        print("\nReady! Critics are watching in the background.\n")

        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                break

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit"):
                break

            if user_input.lower().startswith("wait"):
                parts = user_input.split()
                seconds = int(parts[1]) if len(parts) > 1 else 30
                print(f"Waiting {seconds} seconds for critics to review...")
                await asyncio.sleep(seconds)
                print("Done waiting.")
                continue

            response = await orchestrator.execute_user_message(user_input)
            print(f"\nWriter: {response}")

    print("\nSession ended.")


if __name__ == "__main__":
    # Get topic from command line or use default
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = "The benefits and risks of artificial intelligence in education"

    # Choose mode
    print("\nSelect mode:")
    print("  1. Automated demo (writes essay, waits for feedback, addresses it)")
    print("  2. Interactive (you control the conversation)")

    try:
        choice = input("\nChoice [1]: ").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        choice = "1"

    if choice == "2":
        asyncio.run(interactive_session(topic))
    else:
        asyncio.run(run_essay_session(topic))
