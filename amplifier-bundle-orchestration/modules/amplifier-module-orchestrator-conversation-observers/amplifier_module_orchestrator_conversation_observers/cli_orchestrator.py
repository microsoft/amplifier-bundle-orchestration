"""CLI-compatible Conversation Observer Orchestrator.

This orchestrator runs observers inline after each main response, analyzing
the conversation and providing feedback. Unlike the demo version which spawns
separate background sessions, this version works with `amplifier run`.

The flow:
1. User sends message
2. Main agent responds
3. Observers analyze the conversation (inline, using same provider)
4. If feedback, inject it and continue
5. Converge when no more feedback
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, Any

from amplifier_core import HookRegistry, ToolResult
from amplifier_core.events import (
    CONTENT_BLOCK_END,
    CONTENT_BLOCK_START,
    ORCHESTRATOR_COMPLETE,
    PROMPT_SUBMIT,
    PROVIDER_REQUEST,
    TOOL_ERROR,
    TOOL_POST,
    TOOL_PRE,
)
from amplifier_core.message_models import ChatRequest, Message, ToolSpec

from .config import ObserverConfig

if TYPE_CHECKING:
    from amplifier_core import ModuleCoordinator

logger = logging.getLogger(__name__)


class ConversationObserverOrchestrator:
    """CLI-compatible orchestrator with conversation observers.

    Observers run inline after each main agent response, analyzing the
    conversation and providing feedback via injected messages.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize the conversation observer orchestrator.

        Args:
            config: Configuration dict with:
                - max_iterations: Max iterations, -1 for unlimited (default: 50)
                - convergence_threshold: Iterations without feedback to converge (default: 2)
                - observers: List of observer configs [{name, role, focus}]
        """
        self.config = config
        self.max_iterations = config.get("max_iterations", 50)
        self.convergence_threshold = config.get("convergence_threshold", 2)

        # Parse observer configs
        self.observers: list[ObserverConfig] = []
        for obs_dict in config.get("observers", []):
            self.observers.append(
                ObserverConfig(
                    name=obs_dict.get("name", "Observer"),
                    role=obs_dict.get("role", "Reviews conversation"),
                    focus=obs_dict.get("focus", "Look for issues and improvements"),
                    config=obs_dict.get("config", {}),
                )
            )

        # Default observers if none configured
        if not self.observers:
            self.observers = [
                ObserverConfig(
                    name="Quality Reviewer",
                    role="Reviews conversation for quality issues",
                    focus="Look for errors, inconsistencies, unclear explanations, and areas for improvement",
                    config={},
                ),
            ]

        # Track state for convergence detection
        self._last_conversation_hash: str | None = None
        self._iterations_without_feedback = 0

    async def execute(
        self,
        prompt: str,
        context,
        providers: dict[str, Any],
        tools: dict[str, Any],
        hooks: HookRegistry,
        coordinator: "ModuleCoordinator | None" = None,
    ) -> str:
        """Execute the conversation-observer-enhanced agent loop.

        Args:
            prompt: User input prompt
            context: Context manager for conversation state
            providers: Available LLM providers
            tools: Available tools
            hooks: Hook registry for lifecycle events
            coordinator: Optional module coordinator

        Returns:
            Final response string
        """
        full_response = ""
        iteration = 0

        # Emit prompt submit hook
        result = await hooks.emit(PROMPT_SUBMIT, {"prompt": prompt})
        if coordinator:
            result = await coordinator.process_hook_result(
                result, "prompt:submit", "orchestrator"
            )
            if result.action == "deny":
                return f"Operation denied: {result.reason}"

        # Add user message
        await context.add_message({"role": "user", "content": prompt})

        # Inject observer awareness into context (first turn only)
        if iteration == 0:
            await self._inject_observer_instructions(context)

        # Select provider
        provider = self._select_provider(providers)
        if not provider:
            return "Error: No providers available"

        provider_name = self._get_provider_name(provider, providers)

        while self.max_iterations == -1 or iteration < self.max_iterations:
            iteration += 1

            # Emit iteration start
            await hooks.emit("main:iteration:start", {"iteration": iteration})

            # Emit provider request
            result = await hooks.emit(
                PROVIDER_REQUEST, {"provider": provider_name, "iteration": iteration}
            )
            if coordinator:
                result = await coordinator.process_hook_result(
                    result, "provider:request", "orchestrator"
                )
                if result.action == "deny":
                    return f"Operation denied: {result.reason}"

            # Get messages for LLM
            message_dicts = list(
                await context.get_messages_for_request(provider=provider)
            )

            # Handle ephemeral injections from hooks
            if (
                result.action == "inject_context"
                and result.ephemeral
                and result.context_injection
            ):
                message_dicts.append(
                    {"role": result.context_injection_role, "content": result.context_injection}
                )

            # Build chat request
            messages = [Message(**msg) for msg in message_dicts]
            tools_list = (
                [
                    ToolSpec(
                        name=t.name, description=t.description, parameters=t.input_schema
                    )
                    for t in tools.values()
                ]
                if tools
                else None
            )

            chat_request = ChatRequest(messages=messages, tools=tools_list)

            try:
                response = await provider.complete(chat_request)

                # Emit content block events
                await self._emit_content_events(response, hooks)

                # Parse tool calls
                tool_calls = provider.parse_tool_calls(response)

                if not tool_calls:
                    # No tools - extract response and check observers
                    response_text = self._extract_text(response)
                    full_response = response_text

                    # Store assistant message
                    await self._store_assistant_message(context, response, response_text)

                    # Emit iteration end
                    await hooks.emit(
                        "main:iteration:end", {"iteration": iteration, "has_tools": False}
                    )

                    # Run observer checks on the conversation
                    feedback = await self._run_observer_checks(context, provider, hooks)

                    if feedback:
                        # Inject feedback into context and continue
                        await context.add_message({"role": "user", "content": feedback})
                        self._iterations_without_feedback = 0
                        continue
                    else:
                        # No feedback - check convergence
                        self._iterations_without_feedback += 1
                        if self._iterations_without_feedback >= self.convergence_threshold:
                            logger.info(
                                f"Converged after {iteration} iterations "
                                f"(no feedback for {self.convergence_threshold} cycles)"
                            )
                            break
                        # If we haven't converged but no feedback, we're done with this turn
                        break
                else:
                    # Has tool calls - process them
                    response_text = self._extract_text(response)

                    # Store assistant message with tool calls
                    await self._store_assistant_message_with_tools(
                        context, response, response_text, tool_calls
                    )

                    # Execute tools
                    await self._execute_tools(
                        tool_calls, tools, context, hooks, coordinator
                    )

                    # Emit iteration end
                    await hooks.emit(
                        "main:iteration:end", {"iteration": iteration, "has_tools": True}
                    )

                    # Continue to process tool results
                    continue

            except Exception as e:
                error_msg = str(e) or f"{type(e).__name__}: (no message)"
                logger.error(f"Provider error: {error_msg}")
                full_response = f"\nError: {error_msg}"
                break

        # Emit completion
        await hooks.emit(
            ORCHESTRATOR_COMPLETE,
            {
                "orchestrator": "orchestrator-conversation-observers",
                "turn_count": iteration,
                "status": "success" if full_response else "incomplete",
                "observers_used": [o.name for o in self.observers],
            },
        )

        return full_response

    async def _inject_observer_instructions(self, context) -> None:
        """Inject system instructions about the observer workflow."""
        observer_list = "\n".join(
            f"- **{obs.name}**: {obs.role}" for obs in self.observers
        )

        instructions = f"""## Conversation Observer Workflow

You are working in an observer-enhanced session. After you respond, observers will analyze the conversation and may provide feedback.

### Active Observers
{observer_list}

### Workflow
1. Respond to the user's request to the best of your ability
2. Observers will automatically review your conversation
3. If feedback is provided, address it in your next response
4. Process continues until observers have no more feedback

### Guidelines
- Focus on producing high-quality responses
- When feedback is provided, address it directly and thoroughly
- Explain what you're changing in response to feedback
"""
        await context.add_message({"role": "system", "content": instructions})

    async def _run_observer_checks(
        self,
        context,
        provider,
        hooks: HookRegistry,
    ) -> str | None:
        """Run observer checks on the conversation and return feedback if any.

        Returns:
            Feedback string to inject, or None if no feedback
        """
        # Get current conversation for analysis
        conversation = await self._get_conversation_snapshot(context)
        if not conversation:
            return None

        # Check if conversation has changed
        conversation_hash = hashlib.md5(conversation.encode()).hexdigest()
        if conversation_hash == self._last_conversation_hash:
            logger.debug("Conversation unchanged, skipping observer checks")
            return None

        self._last_conversation_hash = conversation_hash

        await hooks.emit(
            "observer:cycle:start", {"observers": [o.name for o in self.observers]}
        )

        all_feedback = []

        for observer in self.observers:
            feedback = await self._run_single_observer(
                observer, conversation, provider, hooks
            )
            if feedback:
                all_feedback.append(f"**{observer.name}**:\n{feedback}")

        await hooks.emit("observer:cycle:end", {"feedback_count": len(all_feedback)})

        if all_feedback:
            combined = "\n\n".join(all_feedback)
            feedback_msg = f"""<observer-feedback>
The following feedback has been provided by observers reviewing your conversation:

{combined}

Please address this feedback in your next response. Explain what changes you're making.
</observer-feedback>"""

            await hooks.emit("observer:feedback:created", {"feedback": combined})
            return feedback_msg

        return None

    async def _get_conversation_snapshot(self, context) -> str | None:
        """Get the current conversation as formatted text for observer review."""
        messages = await context.get_messages()
        if not messages:
            return None

        # Format messages for observer review
        formatted_parts = []
        for msg in messages:
            role = msg.get("role", "unknown")

            # Skip system messages
            if role == "system":
                continue

            content = msg.get("content", "")
            if isinstance(content, list):
                # Handle structured content
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = "\n".join(text_parts)

            # Handle tool calls
            if role == "assistant" and msg.get("tool_calls"):
                tool_calls = msg.get("tool_calls", [])
                tool_summary = ", ".join(
                    tc.get("tool", tc.get("function", {}).get("name", "unknown"))
                    for tc in tool_calls
                )
                formatted_parts.append(
                    f"ASSISTANT [tool calls: {tool_summary}]:\n{content}"
                )

            # Handle tool results
            elif role == "tool":
                tool_name = msg.get("name", "unknown")
                # Truncate long tool results
                if len(str(content)) > 500:
                    content = str(content)[:500] + "... [truncated]"
                formatted_parts.append(f"TOOL RESULT ({tool_name}):\n{content}")

            # Regular messages
            elif role == "user":
                formatted_parts.append(f"USER:\n{content}")
            elif role == "assistant":
                formatted_parts.append(f"ASSISTANT:\n{content}")

        if not formatted_parts:
            return None

        return "\n\n---\n\n".join(formatted_parts)

    async def _run_single_observer(
        self,
        observer: ObserverConfig,
        conversation: str,
        provider,
        hooks: HookRegistry,
    ) -> str | None:
        """Run a single observer check on the conversation.

        Args:
            observer: Observer configuration
            conversation: Formatted conversation text
            provider: LLM provider for analysis
            hooks: Hook registry

        Returns:
            Feedback string or None
        """
        # Create observer prompt
        prompt = f"""You are **{observer.name}**, a specialized reviewer analyzing a conversation.

## Your Role
{observer.role}

## Your Focus
{observer.focus}

## Conversation to Review
{conversation}

## Instructions
1. Analyze the conversation from your specialized perspective
2. If you find issues that need addressing, describe them clearly
3. If the conversation looks good, respond with exactly: NO_FEEDBACK
4. Be specific and actionable in your feedback
5. Prioritize the most important issues (max 2)
6. Reference specific parts of the conversation

Provide your feedback now:"""

        try:
            # Make a simple completion request for the observer
            messages = [Message(role="user", content=prompt)]
            chat_request = ChatRequest(messages=messages, tools=None)

            response = await provider.complete(chat_request)
            feedback_text = self._extract_text(response).strip()

            if "NO_FEEDBACK" in feedback_text.upper():
                return None

            return feedback_text

        except Exception as e:
            logger.warning(f"Observer {observer.name} failed: {e}")
            return None

    async def _execute_tools(
        self,
        tool_calls,
        tools: dict[str, Any],
        context,
        hooks: HookRegistry,
        coordinator,
    ) -> None:
        """Execute tool calls and add results to context."""
        import uuid

        parallel_group_id = str(uuid.uuid4())

        for tc in tool_calls:
            try:
                # Pre-tool hook
                pre_result = await hooks.emit(
                    TOOL_PRE,
                    {
                        "tool_name": tc.name,
                        "tool_call_id": tc.id,
                        "tool_input": tc.arguments,
                        "parallel_group_id": parallel_group_id,
                    },
                )
                if coordinator:
                    pre_result = await coordinator.process_hook_result(
                        pre_result, "tool:pre", tc.name
                    )
                    if pre_result.action == "deny":
                        await context.add_message(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": f"Denied: {pre_result.reason}",
                            }
                        )
                        continue

                # Get and execute tool
                tool = tools.get(tc.name)
                if not tool:
                    await context.add_message(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": f"Error: Tool '{tc.name}' not found",
                        }
                    )
                    continue

                try:
                    result = await tool.execute(tc.arguments)
                except Exception as e:
                    result = ToolResult(success=False, error={"message": str(e)})

                # Post-tool hook
                result_data = (
                    result.model_dump() if hasattr(result, "model_dump") else str(result)
                )
                await hooks.emit(
                    TOOL_POST,
                    {
                        "tool_name": tc.name,
                        "tool_call_id": tc.id,
                        "tool_input": tc.arguments,
                        "result": result_data,
                        "parallel_group_id": parallel_group_id,
                    },
                )

                # Add result to context
                await context.add_message(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result.get_serialized_output(),
                    }
                )

            except Exception as e:
                logger.error(f"Tool {tc.name} failed: {e}")
                await hooks.emit(
                    TOOL_ERROR,
                    {
                        "tool_name": tc.name,
                        "tool_call_id": tc.id,
                        "error": {"type": type(e).__name__, "msg": str(e)},
                    },
                )
                await context.add_message(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": f"Error: {str(e)}",
                    }
                )

    async def _emit_content_events(self, response, hooks: HookRegistry) -> None:
        """Emit content block events for the response."""
        content_blocks = getattr(response, "content_blocks", None)
        if not content_blocks:
            return

        total_blocks = len(content_blocks)
        for idx, block in enumerate(content_blocks):
            await hooks.emit(
                CONTENT_BLOCK_START,
                {
                    "block_type": block.type.value,
                    "block_index": idx,
                    "total_blocks": total_blocks,
                },
            )
            event_data = {
                "block_index": idx,
                "total_blocks": total_blocks,
                "block": block.to_dict() if hasattr(block, "to_dict") else str(block),
            }
            if response.usage:
                event_data["usage"] = response.usage.model_dump()
            await hooks.emit(CONTENT_BLOCK_END, event_data)

    async def _store_assistant_message(self, context, response, text: str) -> None:
        """Store assistant message in context."""
        content = getattr(response, "content", None)
        if content and isinstance(content, list):
            content_dicts = [
                block.model_dump() if hasattr(block, "model_dump") else block
                for block in content
            ]
            msg = {"role": "assistant", "content": content_dicts}
        else:
            msg = {"role": "assistant", "content": text}

        if hasattr(response, "metadata") and response.metadata:
            msg["metadata"] = response.metadata

        await context.add_message(msg)

    async def _store_assistant_message_with_tools(
        self, context, response, text: str, tool_calls
    ) -> None:
        """Store assistant message with tool calls."""
        content = getattr(response, "content", None)
        if content and isinstance(content, list):
            content_dicts = [
                block.model_dump() if hasattr(block, "model_dump") else block
                for block in content
            ]
            msg = {
                "role": "assistant",
                "content": content_dicts,
                "tool_calls": [
                    {"id": tc.id, "tool": tc.name, "arguments": tc.arguments}
                    for tc in tool_calls
                ],
            }
        else:
            msg = {
                "role": "assistant",
                "content": text,
                "tool_calls": [
                    {"id": tc.id, "tool": tc.name, "arguments": tc.arguments}
                    for tc in tool_calls
                ],
            }

        if hasattr(response, "metadata") and response.metadata:
            msg["metadata"] = response.metadata

        await context.add_message(msg)

    def _extract_text(self, response) -> str:
        """Extract text content from response."""
        if hasattr(response, "text") and response.text:
            return response.text

        content = getattr(response, "content", None)
        if isinstance(content, str):
            return content

        if not content:
            return ""

        text_parts = []
        for block in content:
            if hasattr(block, "text"):
                text_parts.append(block.text)

        return "\n\n".join(text_parts)

    def _select_provider(self, providers: dict[str, Any]) -> Any:
        """Select provider based on priority."""
        if not providers:
            return None

        provider_list = []
        for name, provider in providers.items():
            priority = 100
            if hasattr(provider, "priority"):
                priority = provider.priority
            elif hasattr(provider, "config") and isinstance(provider.config, dict):
                priority = provider.config.get("priority", 100)
            provider_list.append((priority, name, provider))

        provider_list.sort(key=lambda x: x[0])
        return provider_list[0][2] if provider_list else None

    def _get_provider_name(self, provider, providers: dict[str, Any]) -> str | None:
        """Get the name of a provider."""
        for name, prov in providers.items():
            if prov is provider:
                return name
        return None
