"""Configuration types for observer orchestrator."""

from dataclasses import dataclass


@dataclass
class ObserverConfig:
    """Configuration for an observer type.

    Args:
        name: Observer name (e.g., "skeptic", "clarity-editor")
        config: Mount plan configuration dictionary
        role: Brief role description (e.g., "Questions unsupported claims")
        focus: Detailed instructions for what to look for
    """

    name: str
    config: dict
    role: str
    focus: str
