"""Observer Orchestrator - Bottom-up feedback pattern with observer checks.

This orchestrator extends the standard agent loop with observer checks:
- Main loop processes user messages and executes tools
- After tool execution phases, observers analyze the work
- Observers create feedback via system messages injected into context
- Main session addresses feedback in subsequent iterations
- Process converges when no more feedback or max iterations reached

The observer pattern is ideal for:
- Code review workflows
- Quality assurance
- Iterative refinement tasks
- Multi-perspective analysis
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from amplifier_core import HookRegistry
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
from amplifier_core import ToolResult

from .config import ObserverConfig

if TYPE_CHECKING:
    from amplifier_core import ModuleCoordinator

logger = logging.getLogger(__name__)


class ObserverOrchestrator:
    """Orchestrator that runs observer checks between main loop iterations.

    The observer pattern provides bottom-up feedback:
    1. Main session executes user request and uses tools
    2. After tool execution, observers analyze the work output
    3. Observer feedback is injected as system messages
    4. Main session continues, addressing the feedback
    5. Process repeats until observers have no feedback or max iterations
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize the observer orchestrator.

        Args:
            config: Configuration dict with:
                - observer_interval: Seconds between observer checks (default: 15.0)
                - watch_paths: File paths to watch (default: ["work/"])
                - max_iterations: Max iterations, -1 for unlimited (default: 50)
                - observers: List of observer configs [{name, role, focus}]
                - convergence_threshold: Iterations without feedback to converge (default: 2)
        """
        self.config = config
        self.max_iterations = config.get("max_iterations", 50)
        self.watch_paths = config.get("watch_paths", ["work/"])
        self.convergence_threshold = config.get("convergence_threshold", 2)
        
        # Parse observer configs
        self.observers: list[ObserverConfig] = []
        for obs_dict in config.get("observers", []):
            self.observers.append(ObserverConfig(
                name=obs_dict.get("name", "Observer"),
                role=obs_dict.get("role", "Reviews work output"),
                focus=obs_dict.get("focus", "Look for issues and improvements"),
                config=obs_dict.get("config", {}),
            ))
        
        # Default observers if none configured
        if not self.observers:
            self.observers = [
                ObserverConfig(
                    name="Quality Reviewer",
                    role="Reviews work for quality issues",
                    focus="Look for errors, inconsistencies, unclear sections, and areas for improvement",
                    config={},
                ),
            ]
        
        # Track state for convergence detection
        self._last_work_state: str | None = None
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
        """Execute the observer-enhanced agent loop.

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
            result = await coordinator.process_hook_result(result, "prompt:submit", "orchestrator")
            if result.action == "deny":
                return f"Operation denied: {result.reason}"

        # Add user message
        await context.add_message({"role": "user", "content": prompt})

        # Inject observer awareness into context
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
            result = await hooks.emit(PROVIDER_REQUEST, {"provider": provider_name, "iteration": iteration})
            if coordinator:
                result = await coordinator.process_hook_result(result, "provider:request", "orchestrator")
                if result.action == "deny":
                    return f"Operation denied: {result.reason}"

            # Get messages for LLM
            message_dicts = list(await context.get_messages_for_request(provider=provider))
            
            # Handle ephemeral injections from hooks
            if result.action == "inject_context" and result.ephemeral and result.context_injection:
                message_dicts.append({"role": result.context_injection_role, "content": result.context_injection})

            # Build chat request
            messages = [Message(**msg) for msg in message_dicts]
            tools_list = [
                ToolSpec(name=t.name, description=t.description, parameters=t.input_schema)
                for t in tools.values()
            ] if tools else None
            
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
                    await hooks.emit("main:iteration:end", {"iteration": iteration, "has_tools": False})
                    
                    # Run observer checks after work is done
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
                            logger.info(f"Converged after {iteration} iterations (no feedback for {self.convergence_threshold} cycles)")
                            break
                        continue
                else:
                    # Has tool calls - process them
                    response_text = self._extract_text(response)
                    
                    # Store assistant message with tool calls
                    await self._store_assistant_message_with_tools(context, response, response_text, tool_calls)
                    
                    # Execute tools
                    await self._execute_tools(tool_calls, tools, context, hooks, coordinator)
                    
                    # Emit iteration end
                    await hooks.emit("main:iteration:end", {"iteration": iteration, "has_tools": True})
                    
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
                "orchestrator": "orchestrator-observers",
                "turn_count": iteration,
                "status": "success" if full_response else "incomplete",
                "observers_used": [o.name for o in self.observers],
            },
        )

        return full_response

    async def _inject_observer_instructions(self, context) -> None:
        """Inject system instructions about the observer workflow."""
        observer_list = "\n".join(f"- **{obs.name}**: {obs.role}" for obs in self.observers)
        
        instructions = f"""## Observer-Enhanced Workflow

You are working in an observer-enhanced session. After you complete work, observers will review it and may provide feedback.

### Active Observers
{observer_list}

### Workflow
1. Complete the user's request to the best of your ability
2. Observers will automatically review your work output
3. If feedback is provided, address it in your next response
4. Process continues until observers have no more feedback

### Guidelines
- Focus on producing high-quality work in your first attempt
- When feedback is provided, address it directly and thoroughly
- Explain what changes you made in response to feedback
"""
        await context.add_message({"role": "system", "content": instructions})

    async def _run_observer_checks(
        self,
        context,
        provider,
        hooks: HookRegistry,
    ) -> str | None:
        """Run observer checks and return feedback if any.

        Returns:
            Feedback string to inject, or None if no feedback
        """
        # Check if work has changed
        current_state = self._get_work_state()
        if current_state == self._last_work_state:
            logger.debug("Work state unchanged, skipping observer checks")
            return None
        
        self._last_work_state = current_state
        
        if not current_state:
            logger.debug("No work files found, skipping observer checks")
            return None

        await hooks.emit("observer:cycle:start", {"observers": [o.name for o in self.observers]})

        all_feedback = []
        
        for observer in self.observers:
            feedback = await self._run_single_observer(observer, provider, hooks)
            if feedback:
                all_feedback.append(f"**{observer.name}**:\n{feedback}")

        await hooks.emit("observer:cycle:end", {"feedback_count": len(all_feedback)})

        if all_feedback:
            combined = "\n\n".join(all_feedback)
            feedback_msg = f"""<observer-feedback>
The following feedback has been provided by observers reviewing your work:

{combined}

Please address this feedback in your next response. Explain what changes you're making.
</observer-feedback>"""
            
            await hooks.emit("observer:feedback:created", {"feedback": combined})
            return feedback_msg
        
        return None

    async def _run_single_observer(
        self,
        observer: ObserverConfig,
        provider,
        hooks: HookRegistry,
    ) -> str | None:
        """Run a single observer check.

        Args:
            observer: Observer configuration
            provider: LLM provider for analysis
            hooks: Hook registry

        Returns:
            Feedback string or None
        """
        # Read work files
        work_content = self._read_work_files()
        if not work_content:
            return None

        # Create observer prompt
        prompt = f"""You are **{observer.name}**, a specialized reviewer.

## Your Role
{observer.role}

## Your Focus
{observer.focus}

## Work to Review
{work_content}

## Instructions
1. Analyze the work from your specialized perspective
2. If you find issues that need addressing, describe them clearly
3. If the work looks good, respond with exactly: NO_FEEDBACK
4. Be specific and actionable in your feedback
5. Prioritize the most important issues (max 3)

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

    def _get_work_state(self) -> str | None:
        """Get a hash of the current work state for change detection."""
        state_parts = []

        for watch_path in self.watch_paths:
            path = Path(watch_path)
            if not path.is_absolute():
                path = Path.cwd() / path

            if path.exists():
                if path.is_file():
                    stat = path.stat()
                    state_parts.append(f"{path}:{stat.st_mtime}:{stat.st_size}")
                elif path.is_dir():
                    for file in path.rglob("*"):
                        if file.is_file() and not file.name.startswith("."):
                            stat = file.stat()
                            state_parts.append(f"{file}:{stat.st_mtime}:{stat.st_size}")

        if not state_parts:
            return None

        state_parts.sort()
        return hashlib.md5("|".join(state_parts).encode()).hexdigest()

    def _read_work_files(self) -> str:
        """Read content from work files for observer review."""
        content_parts = []

        for watch_path in self.watch_paths:
            path = Path(watch_path)
            if not path.is_absolute():
                path = Path.cwd() / path

            if path.exists():
                if path.is_file():
                    try:
                        text = path.read_text()
                        content_parts.append(f"### File: {path}\n```\n{text}\n```")
                    except Exception as e:
                        logger.warning(f"Failed to read {path}: {e}")
                elif path.is_dir():
                    for file in path.rglob("*"):
                        if file.is_file() and not file.name.startswith("."):
                            try:
                                text = file.read_text()
                                rel_path = file.relative_to(path)
                                content_parts.append(f"### File: {rel_path}\n```\n{text}\n```")
                            except Exception as e:
                                logger.warning(f"Failed to read {file}: {e}")

        return "\n\n".join(content_parts)

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
                    pre_result = await coordinator.process_hook_result(pre_result, "tool:pre", tc.name)
                    if pre_result.action == "deny":
                        await context.add_message({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": f"Denied: {pre_result.reason}",
                        })
                        continue

                # Get and execute tool
                tool = tools.get(tc.name)
                if not tool:
                    await context.add_message({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": f"Error: Tool '{tc.name}' not found",
                    })
                    continue

                try:
                    result = await tool.execute(tc.arguments)
                except Exception as e:
                    result = ToolResult(success=False, error={"message": str(e)})

                # Post-tool hook
                result_data = result.model_dump() if hasattr(result, "model_dump") else str(result)
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
                await context.add_message({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result.get_serialized_output(),
                })

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
                await context.add_message({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": f"Error: {str(e)}",
                })

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

    async def _store_assistant_message_with_tools(self, context, response, text: str, tool_calls) -> None:
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
                "tool_calls": [{"id": tc.id, "tool": tc.name, "arguments": tc.arguments} for tc in tool_calls],
            }
        else:
            msg = {
                "role": "assistant",
                "content": text,
                "tool_calls": [{"id": tc.id, "tool": tc.name, "arguments": tc.arguments} for tc in tool_calls],
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
