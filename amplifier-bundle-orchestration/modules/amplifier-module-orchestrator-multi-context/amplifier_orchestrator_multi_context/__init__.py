"""
Amplifier Multi-Context Workflow Orchestrator

A modular orchestration system for executing workflows across multiple
isolated execution contexts using Amplifier Core.

Public API:
    - MultiContextOrchestrator: Main orchestrator class
    - ExecutionContext: Individual context manager
    - Workflow, Phase, Task: Workflow data models
    - load_workflow: Load workflow from YAML file
"""

from .config import load_workflow
from .context import ExecutionContext
from .orchestrator import MultiContextOrchestrator
from .workflow import Phase, Task, Workflow

__all__ = [
    "MultiContextOrchestrator",
    "ExecutionContext",
    "Workflow",
    "Phase",
    "Task",
    "load_workflow",
]
