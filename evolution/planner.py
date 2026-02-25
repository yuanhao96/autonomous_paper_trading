"""Evolution planner: assembles context for strategy generation.

Gathers knowledge summaries, past winners, past feedback, and preferences
to build the ``GenerationContext`` that drives the LLM strategy generator.
"""

from __future__ import annotations

import logging

from core.preferences import load_preferences
from evolution.store import EvolutionStore
from knowledge.store import MarkdownMemory
from strategies.generator import GenerationContext, StrategyGenerator
from strategies.spec import StrategySpec

logger = logging.getLogger(__name__)


class EvolutionPlanner:
    """Plan strategy generation by assembling context from memory + store."""

    def __init__(
        self,
        memory: MarkdownMemory,
        generator: StrategyGenerator,
        store: EvolutionStore,
    ) -> None:
        self._memory = memory
        self._generator = generator
        self._store = store

    def plan_generation(self) -> GenerationContext:
        """Build the context for the next generation batch."""
        # Knowledge summary from memory.
        knowledge_summary = ""
        try:
            docs = self._memory.search("trading strategy indicators technical analysis", limit=5)
            if docs:
                knowledge_summary = "\n".join(
                    f"- {doc.title}: {doc.content[:200]}" for doc in docs[:5]
                )
        except Exception:
            logger.exception("Failed to search knowledge memory")

        # Past winners.
        past_winners = self._store.get_recent_winners(limit=10)

        # Past feedback.
        past_feedback = self._store.get_recent_feedback(limit=20)

        # Preferences summary.
        preferences_summary = ""
        try:
            prefs = load_preferences()
            preferences_summary = (
                f"Risk tolerance: {prefs.risk_tolerance}, "
                f"Max drawdown: {prefs.max_drawdown_pct}%, "
                f"Horizon: {prefs.trading_horizon}, "
                f"Target return: {prefs.target_annual_return_pct}%, "
                f"Max position: {prefs.max_position_pct}%"
            )
        except Exception:
            logger.exception("Failed to load preferences")

        # Exhaustion notes.
        exhaustion_notes = ""
        if self._store.check_exhaustion():
            exhaustion_notes = (
                "WARNING: Recent cycles show score plateau. "
                "Try radically different approaches."
            )

        return GenerationContext(
            knowledge_summary=knowledge_summary,
            past_winners=past_winners,
            past_feedback=past_feedback,
            preferences_summary=preferences_summary,
            exhaustion_notes=exhaustion_notes,
        )

    def generate(self, context: GenerationContext) -> list[StrategySpec]:
        """Generate a batch of strategy specs."""
        result = self._generator.generate_batch(context)
        logger.info(
            "Planner generated %d specs (%d failures)",
            len(result.specs),
            result.parse_failures,
        )
        return result.specs
