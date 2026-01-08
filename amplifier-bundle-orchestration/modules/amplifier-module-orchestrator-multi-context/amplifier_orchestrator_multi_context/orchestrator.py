"""
MultiContextOrchestrator - Executes workflows across multiple isolated contexts.

The orchestrator manages execution contexts, runs tasks through Amplifier Core,
and handles sequential and parallel execution of workflow phases.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from amplifier_core import AmplifierSession

from .context import ExecutionContext
from .workflow import Workflow

logger = logging.getLogger(__name__)


class MultiContextOrchestrator:
    """
    Orchestrates workflow execution across multiple isolated contexts.

    The orchestrator maintains a registry of execution contexts and a pool of
    AmplifierSession instances (one per profile). Each session manages its own
    history internally. Contexts track metadata about task execution.

    Usage:
        loader = ModuleLoader(search_paths=[modules_dir])
        mount_plans_dir = Path("mount_plans")
        orchestrator = MultiContextOrchestrator(loader, mount_plans_dir)

        workflow = load_workflow("workflow.yaml")
        results = await orchestrator.execute_workflow(workflow)

        await orchestrator.cleanup()
    """

    def __init__(
        self,
        loader: Any,
        mount_plans_dir: Path,
        max_context_history: int = 50,
    ):
        """
        Initialize the orchestrator with module loader and mount plans directory.

        Args:
            loader: ModuleLoader for Amplifier Core modules
            mount_plans_dir: Directory containing mount plan JSON files
            max_context_history: Max messages per context (for tracking only)
        """
        self.loader = loader
        self.mount_plans_dir = Path(mount_plans_dir)
        self.max_context_history = max_context_history
        self.contexts: dict[str, ExecutionContext] = {}
        self.sessions: dict[str, AmplifierSession] = {}  # Session pool

    def _load_mount_plan(self, profile: str) -> dict:
        """Load mount plan JSON for a profile."""
        mount_plan_path = self.mount_plans_dir / f"{profile}.json"
        if not mount_plan_path.exists():
            raise FileNotFoundError(f"Mount plan not found: {mount_plan_path}")

        with open(mount_plan_path) as f:
            return json.load(f)

    async def _get_or_create_session(self, profile: str) -> AmplifierSession:
        """Get existing session or create new one for profile."""
        if profile not in self.sessions:
            logger.info(f"Creating new session for profile: {profile}")
            logger.info(f"[TRACE] Loading mount plan for profile: {profile}")
            config = self._load_mount_plan(profile)
            logger.info(f"[TRACE] Mount plan loaded, creating AmplifierSession")
            session = AmplifierSession(config, loader=self.loader)
            logger.info(f"[TRACE] Calling session.__aenter__() to initialize")
            await session.__aenter__()  # Initialize
            logger.info(f"[TRACE] Session initialized for profile: {profile}")
            self.sessions[profile] = session
        else:
            logger.info(f"[TRACE] Reusing existing session for profile: {profile}")

        return self.sessions[profile]

    def get_or_create_context(self, context_name: str) -> ExecutionContext:
        """
        Get an existing context or create a new one.

        Args:
            context_name: Name of the context to retrieve or create

        Returns:
            ExecutionContext for the given name
        """
        if context_name not in self.contexts:
            self.contexts[context_name] = ExecutionContext(
                name=context_name, max_history=self.max_context_history
            )
            logger.info(f"Created new context: {context_name}")

        return self.contexts[context_name]

    async def execute_task(
        self, task_dict: dict[str, Any], default_profile: str | None = None
    ) -> dict[str, Any]:
        """
        Execute a single task in its designated context.

        Args:
            task_dict: Task configuration with context_name, prompt, and optional profile
            default_profile: Default profile to use if task doesn't specify one

        Returns:
            Dictionary with task result:
                - success: bool
                - context_name: str
                - response: str (if successful)
                - error: str (if failed)
        """
        context_name = task_dict["context_name"]
        prompt = task_dict["prompt"]
        profile = task_dict.get("profile") or default_profile

        logger.info(f"[TRACE] execute_task START: context={context_name}, profile={profile}")

        if not profile:
            logger.error(f"[TRACE] execute_task FAIL: No profile for context={context_name}")
            return {
                "success": False,
                "context_name": context_name,
                "error": "No profile specified for task",
            }

        logger.info(f"Executing task in context '{context_name}' with profile '{profile}'")
        print(f"  🔄 [{context_name}] Starting task with profile '{profile}'...")

        # Get or create context for tracking
        logger.info(f"[TRACE] Getting context for '{context_name}'")
        context = self.get_or_create_context(context_name)
        context.add_message("user", prompt)
        logger.info(f"[TRACE] Context retrieved, adding user message")

        try:
            # Get session for this profile
            logger.info(f"[TRACE] Getting session for profile '{profile}'")
            session = await self._get_or_create_session(profile)
            logger.info(f"[TRACE] Session obtained, calling session.execute()")

            # Execute via Amplifier Core
            # Note: session.execute() maintains its own history internally
            response = await session.execute(prompt)
            logger.info(f"[TRACE] session.execute() returned: {len(response)} chars")

            # Track in context for metadata
            context.add_message("assistant", response)

            logger.info(f"Task completed in context '{context_name}'")
            logger.info(f"[TRACE] execute_task SUCCESS: context={context_name}")
            print(f"  ✅ [{context_name}] Task completed ({len(response)} chars)")

            return {
                "success": True,
                "context_name": context_name,
                "response": response,
            }

        except Exception as e:
            logger.error(f"[TRACE] execute_task EXCEPTION: {e}")
            logger.error(f"Task failed in context '{context_name}': {e}")
            print(f"  ❌ [{context_name}] Task failed: {str(e)[:100]}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "context_name": context_name,
                "error": str(e),
            }

    async def execute_phase(
        self, phase_dict: dict[str, Any], default_profile: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Execute a phase (collection of tasks) sequentially or in parallel.

        Args:
            phase_dict: Phase configuration with name, execution_mode, and tasks
            default_profile: Default profile to use for tasks without one

        Returns:
            List of task results
        """
        import time
        phase_start = time.time()

        phase_name = phase_dict["name"]
        execution_mode = phase_dict.get("execution_mode", "sequential")
        tasks = phase_dict["tasks"]

        logger.info(
            f"Starting phase '{phase_name}' with {len(tasks)} tasks ({execution_mode})"
        )
        print(f"\n{'='*70}")
        print(f"📋 PHASE: {phase_name}")
        print(f"   Mode: {execution_mode.upper()}")
        print(f"   Tasks: {len(tasks)}")
        print(f"{'='*70}\n")
        logger.info(f"[TRACE] execute_phase START: phase={phase_name}, mode={execution_mode}, tasks={len(tasks)}")

        if execution_mode == "parallel":
            logger.info(f"[TRACE] Creating {len(tasks)} parallel task coroutines")
            # Execute all tasks concurrently
            task_coroutines = [
                self.execute_task(task, default_profile) for task in tasks
            ]
            logger.info(f"[TRACE] Calling asyncio.gather() with {len(task_coroutines)} coroutines")
            results = await asyncio.gather(*task_coroutines, return_exceptions=True)
            logger.info(f"[TRACE] asyncio.gather() returned {len(results)} results")

            # Convert exceptions to error results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"[TRACE] Task {i} raised exception: {result}")
                    processed_results.append(
                        {
                            "success": False,
                            "context_name": tasks[i].get("context_name", "unknown"),
                            "error": str(result),
                        }
                    )
                else:
                    logger.info(f"[TRACE] Task {i} completed successfully")
                    processed_results.append(result)

            phase_elapsed = time.time() - phase_start
            logger.info(f"[TRACE] execute_phase COMPLETE: phase={phase_name}")
            print(f"\n  ⏱️  Phase '{phase_name}' completed in {phase_elapsed:.1f}s")
            return processed_results

        else:  # sequential
            logger.info(f"[TRACE] Sequential execution of {len(tasks)} tasks")
            results = []
            for i, task in enumerate(tasks):
                logger.info(f"[TRACE] Starting sequential task {i+1}/{len(tasks)}")
                result = await self.execute_task(task, default_profile)
                results.append(result)
                logger.info(f"[TRACE] Sequential task {i+1}/{len(tasks)} completed")

                # Stop on failure if configured (future enhancement)
                # For MVP, we continue even on failure
                if not result["success"]:
                    logger.warning(
                        f"Task failed in context '{result['context_name']}', continuing..."
                    )

            phase_elapsed = time.time() - phase_start
            logger.info(f"[TRACE] execute_phase COMPLETE: phase={phase_name}")
            print(f"\n  ⏱️  Phase '{phase_name}' completed in {phase_elapsed:.1f}s")
            return results

    async def execute_workflow(self, workflow: Workflow) -> dict[str, Any]:
        """
        Execute a complete workflow with all its phases.

        Phases are always executed sequentially, but tasks within a phase
        can be sequential or parallel based on the phase configuration.

        Args:
            workflow: Workflow object loaded from YAML

        Returns:
            Dictionary with workflow execution results:
                - workflow_name: str
                - success: bool
                - phases: list of phase results
                - total_tasks: int
                - successful_tasks: int
                - failed_tasks: int
        """
        logger.info(f"Starting workflow: {workflow.name}")
        logger.info(f"[TRACE] execute_workflow START: {workflow.name}, phases={len(workflow.phases)}")

        if workflow.description:
            logger.info(f"Description: {workflow.description}")

        all_phase_results = []
        total_tasks = 0
        successful_tasks = 0
        failed_tasks = 0

        # Execute phases sequentially
        for i, phase in enumerate(workflow.phases):
            logger.info(f"[TRACE] Starting phase {i+1}/{len(workflow.phases)}: {phase.name}")
            phase_dict = phase.model_dump()
            logger.info(f"[TRACE] Calling execute_phase for '{phase.name}'")
            phase_results = await self.execute_phase(
                phase_dict, workflow.default_profile
            )
            logger.info(f"[TRACE] Phase {i+1}/{len(workflow.phases)} returned {len(phase_results)} results")

            all_phase_results.append(
                {"phase_name": phase.name, "results": phase_results}
            )

            # Track statistics
            total_tasks += len(phase_results)
            successful_tasks += sum(1 for r in phase_results if r.get("success"))
            failed_tasks += sum(1 for r in phase_results if not r.get("success"))

        logger.info(
            f"Workflow '{workflow.name}' completed: {successful_tasks}/{total_tasks} tasks successful"
        )
        logger.info(f"[TRACE] execute_workflow COMPLETE: {workflow.name}")

        return {
            "workflow_name": workflow.name,
            "success": failed_tasks == 0,
            "phases": all_phase_results,
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
        }

    async def cleanup(self):
        """Clean up all sessions."""
        logger.info(f"Cleaning up {len(self.sessions)} sessions")

        for profile, session in self.sessions.items():
            try:
                await session.__aexit__(None, None, None)
                logger.info(f"Closed session for profile: {profile}")
            except Exception as e:
                logger.error(f"Failed to close session for {profile}: {e}")

        self.sessions.clear()

    def clear_context(self, context_name: str) -> None:
        """
        Clear the history for a specific context.

        Args:
            context_name: Name of the context to clear
        """
        if context_name in self.contexts:
            self.contexts[context_name].clear_history()
            logger.info(f"Cleared context: {context_name}")

    def clear_all_contexts(self) -> None:
        """
        Clear history for all contexts.
        """
        for context in self.contexts.values():
            context.clear_history()
        logger.info("Cleared all contexts")
