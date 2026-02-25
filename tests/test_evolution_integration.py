"""Integration tests for evolution loop wiring into agent lifecycle.

Tests that:
1. TradingAgent loads evolved strategies at startup.
2. Learning session optionally triggers evolution.
3. Full pipeline: generate → compile → backtest → audit → persist → reload.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evolution.store import EvolutionStore
from strategies.spec import (
    CompositeCondition,
    ConditionSpec,
    IndicatorSpec,
    StrategySpec,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_spec(name: str = "evolved_strategy") -> StrategySpec:
    return StrategySpec(
        name=name,
        version="0.1.0",
        description="Evolved SMA crossover",
        indicators=[
            IndicatorSpec(name="sma", params={"period": 20}, output_key="sma_short"),
            IndicatorSpec(name="sma", params={"period": 50}, output_key="sma_long"),
        ],
        entry_conditions=CompositeCondition(
            logic="ALL_OF",
            conditions=[
                ConditionSpec(
                    operator="cross_above", left="sma_short", right="sma_long"
                ),
            ],
        ),
        exit_conditions=CompositeCondition(
            logic="ALL_OF",
            conditions=[
                ConditionSpec(
                    operator="cross_below", left="sma_short", right="sma_long"
                ),
            ],
        ),
    )


def _seed_store_with_survivor(store: EvolutionStore, name: str = "evolved_strategy") -> None:
    """Insert a completed cycle with one survivor into the store."""
    cycle_id = store.start_cycle("test")
    spec = _valid_spec(name)
    store.save_spec_result(
        cycle_id, json.dumps(spec.to_dict()), spec.name, 0.75, 1, True
    )
    store.complete_cycle(cycle_id, 0.75)


@pytest.fixture
def evo_db(tmp_path: Path) -> str:
    return str(tmp_path / "test_evolution.db")


@pytest.fixture
def store(evo_db: str) -> EvolutionStore:
    return EvolutionStore(db_path=evo_db)


# ---------------------------------------------------------------------------
# Tests: TradingAgent loads survivors at init
# ---------------------------------------------------------------------------


class TestAgentLoadsSurvivors:
    @patch("agents.trading.agent.PaperBroker")
    @patch("evolution.store.EvolutionStore")
    def test_init_loads_survivors_from_store(
        self, mock_store_cls, mock_broker
    ) -> None:
        """TradingAgent.__init__ calls load_survivors_from_store."""
        mock_store = MagicMock()
        mock_store.get_recent_winners.return_value = [_valid_spec().to_dict()]
        mock_store_cls.return_value = mock_store

        from agents.trading.agent import TradingAgent

        agent = TradingAgent(mock=True)

        # Should have defaults + evolved strategy.
        strategies = agent._registry.list_strategies()
        assert "sma_crossover" in strategies
        assert "rsi_mean_reversion" in strategies
        assert "evolved_strategy" in strategies

    @patch("agents.trading.agent.PaperBroker")
    @patch("evolution.store.EvolutionStore")
    def test_init_handles_missing_store_gracefully(
        self, mock_store_cls, mock_broker
    ) -> None:
        """Agent starts cleanly even if EvolutionStore() raises."""
        mock_store_cls.side_effect = RuntimeError("DB not available")

        from agents.trading.agent import TradingAgent

        agent = TradingAgent(mock=True)

        # Should still have the 2 default strategies.
        strategies = agent._registry.list_strategies()
        assert len(strategies) == 2
        assert "sma_crossover" in strategies

    @patch("agents.trading.agent.PaperBroker")
    @patch("evolution.store.EvolutionStore")
    def test_init_with_empty_store(self, mock_store_cls, mock_broker) -> None:
        """Agent starts with just defaults when no survivors exist."""
        mock_store = MagicMock()
        mock_store.get_recent_winners.return_value = []
        mock_store_cls.return_value = mock_store

        from agents.trading.agent import TradingAgent

        agent = TradingAgent(mock=True)

        strategies = agent._registry.list_strategies()
        assert len(strategies) == 2


# ---------------------------------------------------------------------------
# Tests: Learning session triggers evolution
# ---------------------------------------------------------------------------


class TestLearningTriggersEvolution:
    @patch("agents.trading.agent.PaperBroker")
    @patch("evolution.store.EvolutionStore")
    def test_learning_does_not_trigger_by_default(
        self, mock_store_cls, mock_broker
    ) -> None:
        """With auto_trigger_after_learning=false, no evolution runs."""
        mock_store = MagicMock()
        mock_store.get_recent_winners.return_value = []
        mock_store_cls.return_value = mock_store

        from agents.trading.agent import TradingAgent

        agent = TradingAgent(mock=True)

        with patch.object(agent, "_curriculum") as mock_curriculum, \
             patch.object(agent, "run_evolution_cycle") as mock_evolve, \
             patch.object(agent, "_load_evolution_settings", return_value={}):
            mock_curriculum.get_next_learning_tasks.return_value = []
            mock_curriculum.get_current_stage.return_value = 1
            mock_curriculum.get_ongoing_tasks.return_value = []

            agent.run_learning_session()

            mock_evolve.assert_not_called()

    @patch("agents.trading.agent.PaperBroker")
    @patch("evolution.store.EvolutionStore")
    def test_learning_triggers_when_enabled(
        self, mock_store_cls, mock_broker
    ) -> None:
        """With auto_trigger_after_learning=true and topics studied, evolution runs."""
        mock_store = MagicMock()
        mock_store.get_recent_winners.return_value = []
        mock_store_cls.return_value = mock_store

        from agents.trading.agent import TradingAgent

        agent = TradingAgent(mock=True)

        # Create a mock topic.
        mock_topic = MagicMock()
        mock_topic.id = "test_topic"
        mock_topic.name = "Test Topic"
        mock_topic.description = "A test"
        mock_topic.mastery_criteria = "Know it"

        with patch.object(agent, "_curriculum") as mock_curriculum, \
             patch.object(agent, "run_evolution_cycle", return_value="ok") as mock_evolve, \
             patch.object(
                 agent, "_load_evolution_settings",
                 return_value={"auto_trigger_after_learning": True},
             ), \
             patch.object(agent, "_state_manager"):
            mock_curriculum.get_next_learning_tasks.return_value = [mock_topic]
            mock_curriculum.get_current_stage.return_value = 1
            mock_curriculum.get_ongoing_tasks.return_value = []
            mock_curriculum.get_mastery.return_value = 0.3

            # Mock learning controller to return quickly.
            with patch("agents.trading.agent.LearningController") as mock_lc_cls:
                mock_controller = MagicMock()
                mock_knowledge = MagicMock()
                mock_knowledge.summary = "Learned about momentum"
                mock_knowledge.key_concepts = ["momentum", "trend"]
                mock_knowledge.trading_implications = []
                mock_knowledge.risk_factors = []
                mock_knowledge.claims = []

                mock_state_obj = MagicMock()
                mock_state_obj.evidence_pool = [MagicMock()]
                mock_state_obj.round_log = []
                mock_state_obj.gaps = []
                mock_state_obj.conflicts = []
                mock_state_obj.round_idx = 1
                mock_state_obj.source_diversity.return_value = 1
                mock_state_obj.confidence = 0.8

                mock_controller.learn_topic.return_value = (mock_knowledge, mock_state_obj)
                mock_lc_cls.return_value = mock_controller

                result = agent.run_learning_session()

            mock_evolve.assert_called_once_with(trigger="knowledge_acquired")
            assert "Evolution:" in result


# ---------------------------------------------------------------------------
# Tests: Full pipeline round-trip (generate → persist → reload)
# ---------------------------------------------------------------------------


class TestFullPipelineRoundTrip:
    def test_persist_and_reload(self, store: EvolutionStore) -> None:
        """Survivors persisted by evolution cycle can be loaded into a fresh registry."""
        from strategies.registry import StrategyRegistry

        # Seed the store with a survivor.
        _seed_store_with_survivor(store, "pipeline_test_strategy")

        # Load into a fresh registry.
        reg = StrategyRegistry()
        loaded = reg.load_survivors_from_store(store)

        assert loaded == 1
        assert "pipeline_test_strategy" in reg.list_strategies()

        # The loaded strategy should be executable.
        strategy = reg.get("pipeline_test_strategy")
        assert strategy is not None
        assert strategy.name == "pipeline_test_strategy"

    def test_multiple_cycles_latest_survivors_loaded(self, store: EvolutionStore) -> None:
        """Multiple cycles should accumulate survivors."""
        from strategies.registry import StrategyRegistry

        _seed_store_with_survivor(store, "gen1_strategy")
        _seed_store_with_survivor(store, "gen2_strategy")

        reg = StrategyRegistry()
        loaded = reg.load_survivors_from_store(store)

        assert loaded == 2
        assert "gen1_strategy" in reg.list_strategies()
        assert "gen2_strategy" in reg.list_strategies()
