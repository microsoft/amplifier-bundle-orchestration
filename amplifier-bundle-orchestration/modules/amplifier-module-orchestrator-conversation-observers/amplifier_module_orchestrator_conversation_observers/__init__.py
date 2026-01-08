"""Conversation Observer orchestrator module for Amplifier.

Implements the observer pattern where observers watch the main conversation
and provide feedback:
- Main session handles user messages and does actual work
- After each response, observers analyze the conversation
- Observers provide feedback via system messages
- Main session addresses feedback in subsequent iterations

This gives observers visibility into the agent's thinking and responses,
not just the final artifacts.

Exports:
    mount - Module mount function (Amplifier protocol)
    ConversationObserverOrchestrator - CLI-compatible orchestrator class
    ObserverConfig - Observer configuration dataclass
"""

# Amplifier module metadata
__amplifier_module_type__ = "orchestrator"

import logging
from typing import Any

from amplifier_core import ModuleCoordinator

from .config import ObserverConfig
from .cli_orchestrator import ConversationObserverOrchestrator

logger = logging.getLogger(__name__)


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None):
    """Mount the conversation observer orchestrator module.
    
    Config options:
        observer_interval: int - Not used in CLI mode (observers run inline)
        max_iterations: int - Max main loop iterations, -1 for unlimited (default: 50)
        convergence_threshold: int - Iterations without feedback to converge (default: 2)
        observers: list[dict] - Observer configurations with name, role, focus
    """
    config = config or {}
    
    # Declare observable lifecycle events
    coordinator.register_contributor(
        "observability.events",
        "orchestrator-conversation-observers",
        lambda: [
            "observer:cycle:start",
            "observer:cycle:end",
            "observer:feedback:created",
            "main:iteration:start",
            "main:iteration:end",
        ],
    )
    
    orchestrator = ConversationObserverOrchestrator(config)
    await coordinator.mount("orchestrator", orchestrator)
    logger.info("Mounted ConversationObserverOrchestrator")
    return


__all__ = ["mount", "ConversationObserverOrchestrator", "ObserverConfig"]
