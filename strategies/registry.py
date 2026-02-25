"""Strategy registry.

Provides a central place to register, look up, and enumerate all
available ``Strategy`` instances.  A module-level singleton
(``registry``) is provided for convenience.
"""

from __future__ import annotations

import logging

from strategies.base import Strategy

logger = logging.getLogger(__name__)


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

    def load_survivors_from_store(self, store: "evolution.store.EvolutionStore") -> int:  # noqa: F821
        """Load recent tournament survivors from the evolution store.

        Compiles each survivor's spec into a ``TemplateStrategy`` and
        registers it.  Returns the number of strategies loaded.
        """
        from strategies.spec import StrategySpec
        from strategies.template_engine import compile_spec

        winners = store.get_recent_winners(limit=10)
        loaded = 0

        for spec_dict in winners:
            try:
                spec = StrategySpec.from_dict(spec_dict)
                strategy = compile_spec(spec)
                self.register(strategy)
                loaded += 1
            except Exception:
                logger.exception("Failed to load survivor spec: %s", spec_dict.get("name", "?"))

        if loaded:
            logger.info("Loaded %d evolved strategies from store", loaded)
        return loaded


# Module-level singleton used across the application.
registry: StrategyRegistry = StrategyRegistry()
