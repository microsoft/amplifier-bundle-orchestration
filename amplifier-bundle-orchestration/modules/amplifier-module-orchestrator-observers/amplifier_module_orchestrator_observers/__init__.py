"""Observer orchestrator module for Amplifier.

Implements the observer pattern for bottom-up feedback loops where:
- A main session does actual work (research, coding, writing)
- Observer checks run after each main loop iteration
- Observers analyze output and create feedback issues
- The main session addresses feedback in subsequent iterations
- Process converges when observers have no more feedback

This is the inverse of the foreman-worker pattern:
- Foreman-Worker: Top-down delegation
- Observer: Bottom-up feedback

Exports:
    mount - Module mount function (Amplifier protocol)
    ObserverOrchestrator - Main orchestrator class
    ObserverConfig - Observer configuration dataclass
"""

# Amplifier module metadata
__amplifier_module_type__ = "orchestrator"

import logging
from typing import Any

from amplifier_core import ModuleCoordinator

from .config import ObserverConfig
from .orchestrator import ObserverOrchestrator

logger = logging.getLogger(__name__)


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None):
    """Mount the observer orchestrator module.
    
    Config options:
        observer_interval: float - Seconds between observer checks (default: 15.0)
        watch_paths: list[str] - File paths observers should watch (default: ["work/"])
        max_iterations: int - Max main loop iterations, -1 for unlimited (default: 50)
        observers: list[dict] - Observer configurations with name, role, focus
    """
    config = config or {}
    
    # Declare observable lifecycle events
    coordinator.register_contributor(
        "observability.events",
        "orchestrator-observers",
        lambda: [
            "observer:cycle:start",
            "observer:cycle:end",
            "observer:feedback:created",
            "main:iteration:start",
            "main:iteration:end",
        ],
    )
    
    orchestrator = ObserverOrchestrator(config)
    await coordinator.mount("orchestrator", orchestrator)
    logger.info("Mounted ObserverOrchestrator")
    return


__all__ = ["mount", "ObserverOrchestrator", "ObserverConfig"]
