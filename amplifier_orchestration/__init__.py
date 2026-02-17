"""
Amplifier Orchestration Bundle.

Event-driven orchestration primitives for multi-session coordination.

This bundle provides:
- spawn_bundle: Unified session spawning with inheritance controls
- EventRouter: Cross-session pub/sub communication
- Triggers: Timer, session event, and manual trigger sources
- BackgroundSessionManager: Long-running sessions that respond to triggers
"""

from amplifier_orchestration.background import (
    BackgroundSessionConfig,
    BackgroundSessionManager,
    BackgroundSessionState,
)
from amplifier_orchestration.events import (
    EventRouter,
    SessionEmitter,
    SessionEvent,
)
from amplifier_orchestration.spawn import (
    SessionStorage,
    SpawnResult,
    spawn_bundle,
)
from amplifier_orchestration.triggers import (
    ManualTrigger,
    SessionEventTrigger,
    TimerTrigger,
    TriggerEvent,
    TriggerSource,
    TriggerType,
)

__all__ = [
    # Spawn
    "spawn_bundle",
    "SpawnResult",
    "SessionStorage",
    # Events
    "EventRouter",
    "SessionEmitter",
    "SessionEvent",
    # Triggers
    "TriggerType",
    "TriggerEvent",
    "TriggerSource",
    "SessionEventTrigger",
    "TimerTrigger",
    "ManualTrigger",
    # Background sessions
    "BackgroundSessionConfig",
    "BackgroundSessionManager",
    "BackgroundSessionState",
]
