"""
ExecutionContext - Manages isolated context for workflow tasks.

Each context maintains its own conversation history with automatic trimming.
"""

from typing import Any


class ExecutionContext:
    """
    Manages an isolated execution context for workflow tasks.

    Each context maintains its own conversation history that is automatically
    trimmed based on configured limits. This ensures that long-running workflows
    don't accumulate unbounded history while preserving recent context.

    Attributes:
        name: Unique identifier for this context
        history: List of conversation messages
        max_history: Maximum number of messages to retain (auto-trim when exceeded)
    """

    def __init__(self, name: str, max_history: int = 50):
        """
        Initialize a new execution context.

        Args:
            name: Unique identifier for this context
            max_history: Maximum number of messages to retain (default: 50)
        """
        self.name = name
        self.history: list[dict[str, Any]] = []
        self.max_history = max_history

    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the context history with automatic trimming.

        If the history exceeds max_history, the oldest messages are removed
        to maintain the configured limit.

        Args:
            role: Message role (e.g., "user", "assistant")
            content: Message content
        """
        self.history.append({"role": role, "content": content})

        # Auto-trim if history exceeds limit
        if len(self.history) > self.max_history:
            # Keep the most recent messages
            self.history = self.history[-self.max_history :]

    def get_history(self) -> list[dict[str, Any]]:
        """
        Get the full conversation history for this context.

        Returns:
            List of message dictionaries with "role" and "content" keys
        """
        return self.history.copy()

    def clear_history(self) -> None:
        """
        Clear all conversation history for this context.

        Useful for resetting context between workflow runs or phases.
        """
        self.history.clear()

    def __repr__(self) -> str:
        return f"ExecutionContext(name={self.name!r}, messages={len(self.history)})"
