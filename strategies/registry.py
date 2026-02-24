"""Strategy registry.

Provides a central place to register, look up, and enumerate all
available ``Strategy`` instances.  A module-level singleton
(``registry``) is provided for convenience.
"""

from __future__ import annotations

from strategies.base import Strategy


class StrategyRegistry:
    """In-memory registry of named strategies."""

    def __init__(self) -> None:
        self._strategies: dict[str, Strategy] = {}

    def register(self, strategy: Strategy) -> None:
        """Add *strategy* to the registry, keyed by its ``name``."""
        self._strategies[strategy.name] = strategy

    def get(self, name: str) -> Strategy | None:
        """Return the strategy registered under *name*, or ``None``."""
        return self._strategies.get(name)

    def list_strategies(self) -> list[str]:
        """Return the names of all registered strategies."""
        return list(self._strategies.keys())

    def get_all(self) -> list[Strategy]:
        """Return every registered strategy instance."""
        return list(self._strategies.values())


# Module-level singleton used across the application.
registry: StrategyRegistry = StrategyRegistry()
