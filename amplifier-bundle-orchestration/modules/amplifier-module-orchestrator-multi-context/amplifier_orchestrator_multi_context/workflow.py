"""
Workflow data models for multi-context orchestration.

Defines the structure of workflows, phases, and tasks using Pydantic models
for validation and easy YAML serialization.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class Task(BaseModel):
    """
    A single task to be executed in a context.

    Attributes:
        context_name: Name of the execution context to use
        prompt: Task instructions/prompt for the agent
        profile: Optional profile name to use for this task
    """

    context_name: str = Field(description="Name of the execution context to use")
    prompt: str = Field(description="Task instructions/prompt for the agent")
    profile: str | None = Field(
        default=None, description="Optional profile name to use for this task"
    )


class Phase(BaseModel):
    """
    A phase containing one or more tasks to execute.

    Phases can execute tasks either sequentially (one after another) or
    in parallel (all at once using asyncio.gather).

    Attributes:
        name: Human-readable phase name
        execution_mode: "sequential" or "parallel"
        tasks: List of tasks to execute in this phase
    """

    name: str = Field(description="Human-readable phase name")
    execution_mode: Literal["sequential", "parallel"] = Field(
        default="sequential", description="How to execute tasks: sequential or parallel"
    )
    tasks: list[Task] = Field(description="List of tasks to execute in this phase")


class Workflow(BaseModel):
    """
    Complete workflow definition with multiple phases.

    A workflow consists of one or more phases that are always executed
    sequentially. Within each phase, tasks can be executed either
    sequentially or in parallel.

    Attributes:
        name: Human-readable workflow name
        description: Optional workflow description
        default_profile: Default profile to use if task doesn't specify one
        phases: List of phases to execute sequentially
        config: Optional workflow-wide configuration
    """

    name: str = Field(description="Human-readable workflow name")
    description: str | None = Field(
        default=None, description="Optional workflow description"
    )
    default_profile: str | None = Field(
        default=None, description="Default profile to use if task doesn't specify one"
    )
    phases: list[Phase] = Field(
        description="List of phases to execute sequentially"
    )
    config: dict[str, Any] = Field(
        default_factory=dict, description="Optional workflow-wide configuration"
    )
