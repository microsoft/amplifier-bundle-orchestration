"""Conversation Observer Orchestrator - Bottom-up feedback from conversation watching.

This orchestrator implements the observer pattern where:
- A main session handles user messages and does actual work
- Observer sessions run continuously in background, watching the main conversation
- When observers spot issues in the conversation, they create feedback issues
- The main session can address feedback between user interactions

Key difference from file-watching observer:
- File-watching: Observers monitor output files for changes
- Conversation-watching: Observers read the main session's conversation history

This gives observers direct visibility into the agent's thinking, tool usage,
and responses - not just the final artifacts.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from amplifier_core import AmplifierSession, ModuleLoader

from .config import ObserverConfig

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ConversationObserverOrchestrator:
    """Orchestrates a main session with observers watching the conversation.

    Observers run in infinite loops, periodically reading the main session's
    conversation history and creating feedback issues when they spot problems.

    Usage:
        async with ConversationObserverOrchestrator(
            loader=loader,
            main_config=main_config,
            observer_configs=[
                ObserverConfig(
                    name="Logic Checker",
                    config=observer_config,
                    role="Identifies logical fallacies and reasoning errors",
                    focus="Look for circular reasoning, false premises..."
                ),
            ],
            workspace_root=workspace,
        ) as orchestrator:
            # Observers start automatically in background
            response = await orchestrator.execute_user_message("Analyze this problem...")
            # Observers are watching the conversation and creating issues
            await asyncio.sleep(30)
            final = await orchestrator.execute_user_message("Address any feedback")
    """

    def __init__(
        self,
        loader: ModuleLoader,
        main_config: dict,
        observer_configs: list[ObserverConfig],
        workspace_root: Path,
        approval_system: Any = None,
        display_system: Any = None,
        observer_interval: float = 15.0,  # Seconds between observer checks
    ):
        """Initialize the conversation observer orchestrator.

        Args:
            loader: Amplifier module loader
            main_config: Mount plan configuration for the main session
            observer_configs: List of observer configurations
            workspace_root: Root workspace directory
            approval_system: Optional approval system for tool calls
            display_system: Optional display system for UI messages
            observer_interval: Seconds between observer review cycles
        """
        self.loader = loader
        self.main_config = main_config
        self.observer_configs = observer_configs
        self.workspace_root = workspace_root
        self.approval_system = approval_system
        self.display_system = display_system
        self.observer_interval = observer_interval

        # Runtime state (initialized lazily)
        self.main_session: AmplifierSession | None = None
        self.observer_tasks: list[asyncio.Task] = []
        self.observer_session_ids: dict[str, str] = {}
        self._initialized = False
        self._shutdown_event = asyncio.Event()

    async def __aenter__(self) -> "ConversationObserverOrchestrator":
        """Enter async context manager."""
        return self

    async def __aexit__(self, *_args: Any) -> None:
        """Exit async context manager, ensuring cleanup."""
        await self.shutdown()

    async def _initialize(self) -> None:
        """Initialize the main session and start observers (called on first message)."""
        if self._initialized:
            return

        logger.info("Initializing conversation observer orchestrator")

        # Create and enter main session
        self.main_session = AmplifierSession(
            config=self.main_config,
            loader=self.loader,
            approval_system=self.approval_system,
            display_system=self.display_system,
        )
        await self.main_session.__aenter__()

        # Inject system instructions for the main session
        main_instructions = self._build_main_instructions()
        context = self.main_session.coordinator.get("context")
        if not context:
            raise RuntimeError("Main session: No context manager mounted")
        await context.add_message({"role": "system", "content": main_instructions})

        # Start all observer background loops
        await self._start_observers()

        self._initialized = True
        logger.info("Conversation observer orchestrator initialized")

    def _build_main_instructions(self) -> str:
        """Build system instructions for the main session."""
        observer_list = "\n".join(
            f"- **{obs.name}**: {obs.role}" for obs in self.observer_configs
        )

        return f"""You are the main working session in an observer-feedback system.

## Your Role
You handle user requests and do actual work. Observer sessions run in the
background, watching your conversation and providing feedback through issues.

## Observers Watching Your Conversation
{observer_list}

## How This Works
1. You receive tasks from the user and execute them
2. Observers read your conversation history and create issues for improvements
3. When asked to "address feedback" or "check for issues", use the issue tool
4. Address feedback issues by explaining your reasoning or correcting mistakes

## Issue Workflow
- Use `list_issues` with status=open to see feedback from observers
- Read each issue's description for specific feedback
- Respond to the feedback (explain, correct, or acknowledge)
- Close the issue with a note about how you addressed it

## Focus
- Do your primary work when given tasks
- When asked to address feedback, check for and resolve open issues
- Work iteratively - observers provide ongoing feedback on your conversation
"""

    async def _start_observers(self) -> None:
        """Start all observer background loops."""
        logger.info("Starting observer background loops")

        for observer in self.observer_configs:
            task = asyncio.create_task(
                self._observer_loop(observer),
                name=f"observer-{observer.name}",
            )
            self.observer_tasks.append(task)
            logger.info(f"Started observer: {observer.name}")

        logger.info(f"Started {len(self.observer_tasks)} observers")

    async def _observer_loop(self, observer: ObserverConfig) -> None:
        """Continuous observer loop - watches conversation and creates feedback.

        Runs until shutdown, periodically reading the main conversation
        and creating issues when problems are spotted.
        """
        logger.info(f"Observer {observer.name} starting continuous loop")

        # Track what we've reviewed to avoid duplicate feedback
        last_conversation_hash: str | None = None

        # Deep copy config to modify actor
        config = json.loads(json.dumps(observer.config))
        for tool in config.get("tools", []):
            if tool.get("module") == "tool-issue":
                tool["config"]["actor"] = observer.name.lower().replace(" ", "-")

        # Get main session ID for parent linking
        main_session_id = getattr(self.main_session, "session_id", None) if self.main_session else None

        while not self._shutdown_event.is_set():
            try:
                # Get the current conversation from main session
                conversation_snapshot = await self._get_conversation_snapshot()

                if conversation_snapshot:
                    # Hash the conversation to detect changes
                    conversation_hash = hashlib.md5(
                        conversation_snapshot.encode()
                    ).hexdigest()

                    if conversation_hash != last_conversation_hash:
                        logger.info(f"Observer {observer.name}: Detected conversation changes, reviewing...")

                        # Create a session for this review cycle
                        async with AmplifierSession(
                            config,
                            loader=self.loader,
                            parent_id=main_session_id,
                            approval_system=self.approval_system,
                            display_system=self.display_system,
                        ) as session:
                            # Track session ID
                            self.observer_session_ids[observer.name] = getattr(session, "session_id", "unknown")

                            # Inject observer instructions with the conversation snapshot
                            instructions = self._build_observer_instructions(observer)
                            context = session.coordinator.get("context")
                            if context:
                                await context.add_message({"role": "system", "content": instructions})

                            # Execute review with the conversation included
                            prompt = self._build_review_prompt(observer, conversation_snapshot)
                            await session.execute(prompt)

                        last_conversation_hash = conversation_hash
                        logger.info(f"Observer {observer.name}: Review complete")

            except asyncio.CancelledError:
                logger.info(f"Observer {observer.name}: Cancelled")
                break
            except Exception as e:
                logger.error(f"Observer {observer.name} error: {e}")
                # Continue running despite errors

            # Wait before next check
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.observer_interval,
                )
                # If we get here, shutdown was signaled
                break
            except asyncio.TimeoutError:
                # Normal timeout, continue loop
                pass

        logger.info(f"Observer {observer.name}: Loop ended")

    async def _get_conversation_snapshot(self) -> str | None:
        """Get the current conversation from the main session as formatted text.

        Returns a string representing the conversation, or None if no
        conversation exists yet.
        """
        if not self.main_session:
            return None

        context = self.main_session.coordinator.get("context")
        if not context:
            return None

        messages = await context.get_messages()
        if not messages:
            return None

        # Format messages for observer review
        # Skip system messages (instructions) - observers just see the conversation flow
        formatted_parts = []
        for msg in messages:
            role = msg.get("role", "unknown")

            # Skip system messages
            if role == "system":
                continue

            content = msg.get("content", "")

            # Handle tool calls
            if role == "assistant" and msg.get("tool_calls"):
                tool_calls = msg.get("tool_calls", [])
                tool_summary = ", ".join(
                    f"{tc.get('function', {}).get('name', 'unknown')}"
                    for tc in tool_calls
                )
                formatted_parts.append(f"ASSISTANT [tool calls: {tool_summary}]:\n{content}")

            # Handle tool results
            elif role == "tool":
                tool_name = msg.get("name", "unknown")
                # Truncate long tool results
                if len(content) > 500:
                    content = content[:500] + "... [truncated]"
                formatted_parts.append(f"TOOL RESULT ({tool_name}):\n{content}")

            # Regular messages
            elif role == "user":
                formatted_parts.append(f"USER:\n{content}")
            elif role == "assistant":
                formatted_parts.append(f"ASSISTANT:\n{content}")

        if not formatted_parts:
            return None

        return "\n\n---\n\n".join(formatted_parts)

    def _build_observer_instructions(self, observer: ObserverConfig) -> str:
        """Build system instructions for an observer session."""
        return f"""You are **{observer.name}**, a specialized observer reviewing the main agent's conversation.

## Your Role
{observer.role}

## Your Focus
{observer.focus}

## Review Guidelines
1. Read the conversation transcript carefully
2. Analyze strictly from your specialized perspective
3. Create issues ONLY for problems in your domain
4. Each issue should have:
   - Clear, specific title
   - Detailed description explaining the problem and suggestion
   - Reference to which part of the conversation has the issue
   - Metadata: {{"observer": "{observer.name}"}}
5. Create at most 2 issues per review (prioritize the most important)
6. Check existing open issues first - don't create duplicates
7. If the conversation looks good from your perspective, don't create any issues

## Issue Creation
Use type="task", priority=2 for feedback issues.
Be specific about what's problematic and how to improve.
"""

    def _build_review_prompt(self, observer: ObserverConfig, conversation: str) -> str:
        """Build the review prompt for an observer including the conversation."""
        return f"""Review this conversation between a user and the main agent:

<conversation>
{conversation}
</conversation>

Your task:
1. First, list any existing open issues to avoid duplicates
2. Analyze the conversation from your specialized perspective: {observer.role}
3. Look for: {observer.focus}
4. If you find NEW issues (not already reported), create them
5. Reference specific parts of the conversation in your issue descriptions

Create at most 2 issues for the most important problems you find.
If everything looks good, just say "No new issues found."
"""

    async def execute_user_message(self, message: str) -> str:
        """Execute a user message through the main session.

        This handles user requests. Observers run automatically in background.

        Args:
            message: The user's message

        Returns:
            The main session's response
        """
        await self._initialize()

        if self.main_session is None:
            raise RuntimeError("Main session not initialized")

        logger.info("Executing user message through main session")

        # Use hybrid async approach to ensure fair scheduling with observers
        task = asyncio.create_task(self.main_session.execute(message))

        while not task.done():
            await asyncio.sleep(0.1)

        return await task

    @property
    def main_session_id(self) -> str | None:
        """Get the main session ID."""
        if self.main_session is None:
            return None
        return getattr(self.main_session, "session_id", None)

    async def shutdown(self) -> None:
        """Shutdown the orchestrator and cleanup resources."""
        logger.info("Shutting down conversation observer orchestrator")
        self._shutdown_event.set()

        # Wait for all observer tasks to complete
        if self.observer_tasks:
            logger.info(f"Waiting for {len(self.observer_tasks)} observers to stop...")
            await asyncio.gather(*self.observer_tasks, return_exceptions=True)
            self.observer_tasks.clear()

        # Close main session
        if self.main_session is not None:
            await self.main_session.__aexit__(None, None, None)
            self.main_session = None

        self._initialized = False
        logger.info("Conversation observer orchestrator shutdown complete")
