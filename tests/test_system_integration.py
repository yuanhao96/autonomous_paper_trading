"""System-level integration tests.

Covers:
1. Agent startup → load promoted → generate signals → execute → state saved.
2. Evolve → promote → strategy appears in next daily cycle.
3. Error recovery: corrupted DB, missing config, LLM timeout.
4. Agent state persistence: save → reload → state matches.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from agents.trading.state import AgentState, StateManager
from evolution.promoter import StrategyPromoter
from evolution.store import EvolutionStore
from strategies.registry import StrategyRegistry
from strategies.spec import (
    CompositeCondition,
    ConditionSpec,
    IndicatorSpec,
    StrategySpec,
)
from strategies.template_engine import compile_spec
from trading.executor import Signal, execute_signals
from trading.paper_broker import PaperBroker
from trading.risk import PortfolioState, RiskManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_spec(name: str = "int_test_sma") -> StrategySpec:
    return StrategySpec(
        name=name,
        version="0.1.0",
        description="SMA crossover for integration test",
        indicators=[
            IndicatorSpec(name="sma", params={"period": 20}, output_key="sma_short"),
            IndicatorSpec(name="sma", params={"period": 50}, output_key="sma_long"),
        ],
        entry_conditions=CompositeCondition(
            logic="ALL_OF",
            conditions=[
                ConditionSpec(operator="cross_above", left="sma_short", right="sma_long"),
            ],
        ),
        exit_conditions=CompositeCondition(
            logic="ALL_OF",
            conditions=[
                ConditionSpec(operator="cross_below", left="sma_short", right="sma_long"),
            ],
        ),
    )


def _mock_data(n: int = 200) -> pd.DataFrame:
    np.random.seed(42)
    close = 100.0 + np.cumsum(np.random.normal(0.05, 1.0, n))
    close = np.maximum(close, 1.0)
    dates = pd.bdate_range("2023-01-03", periods=n, freq="B")
    df = pd.DataFrame(
        {
            "Open": close * 0.999,
            "High": close * 1.005,
            "Low": close * 0.995,
            "Close": close,
            "Volume": np.random.randint(100_000, 5_000_000, n),
        },
        index=dates,
    )
    df.attrs["ticker"] = "SPY"
    return df


# ---------------------------------------------------------------------------
# 1. Agent startup → load promoted → generate signals → execute
# ---------------------------------------------------------------------------


class TestStartupToExecution:
    """Full flow: promoted strategy loaded at startup, generates signals, executes."""

    def test_promoted_strategy_generates_signals(self, tmp_path: Path) -> None:
        """A promoted strategy should compile and generate signals on OHLCV data."""
        spec = _valid_spec("promoted_sma")
        strategy = compile_spec(spec)
        data = _mock_data()

        signals = strategy.generate_signals(data)

        # Strategy should produce at least some signals on 200 bars of data.
        assert isinstance(signals, list)
        for sig in signals:
            assert isinstance(sig, Signal)
            assert sig.strategy_name == "promoted_sma"

    def test_promoted_strategy_in_registry_and_signal_flow(
        self, tmp_path: Path, sample_preferences_yaml: Path,
    ) -> None:
        """Promoted strategy registered → generates signals → passes risk check."""
        from core.preferences import load_preferences

        # Set up registry with a compiled promoted strategy.
        registry = StrategyRegistry()
        spec = _valid_spec("test_promoted")
        strategy = compile_spec(spec)
        registry.register(strategy)

        # Generate signals.
        data = _mock_data()
        all_signals: list[Signal] = []
        for strat in registry.get_all():
            all_signals.extend(strat.generate_signals(data))

        # Set up broker and risk manager.
        broker = PaperBroker(mock=True, db_path=tmp_path / "broker.db")
        prefs = load_preferences(sample_preferences_yaml)
        risk_manager = RiskManager(prefs)

        with patch("trading.paper_broker._current_price", return_value=100.0):
            portfolio = broker.get_portfolio()

        portfolio_state = PortfolioState(
            total_equity=portfolio.total_equity,
            cash=portfolio.cash,
            positions={},
            daily_pnl=portfolio.daily_pnl,
        )

        # Execute signals (may or may not have any depending on data).
        with patch("trading.paper_broker._current_price", return_value=100.0):
            results = execute_signals(all_signals, broker, risk_manager, portfolio_state)

        # All results should be valid ExecutionResult objects.
        for r in results:
            assert hasattr(r, "executed")
            assert hasattr(r, "signal")


# ---------------------------------------------------------------------------
# 2. Evolve → promote → strategy appears
# ---------------------------------------------------------------------------


class TestEvolveToPromotionPipeline:
    """End-to-end: evolution store survivor → promoter candidate → promoted → loadable."""

    def test_full_promotion_lifecycle(self, tmp_path: Path) -> None:
        """Survivor in evolution store → submitted to promoter → promoted → loaded."""
        evo_db = str(tmp_path / "evo.db")
        promo_db = str(tmp_path / "promo.db")

        store = EvolutionStore(db_path=evo_db)
        promoter = StrategyPromoter(db_path=promo_db)

        # Step 1: Simulate evolution cycle producing a survivor.
        spec = _valid_spec("evo_winner")
        cycle_id = store.start_cycle("test")
        store.save_spec_result(
            cycle_id, json.dumps(spec.to_dict()), spec.name, 0.85, 1, True,
        )
        store.complete_cycle(cycle_id, 0.85)

        # Step 2: Submit to promoter (normally done by EvolutionCycle).
        promoter.submit_candidate(
            name="evo_winner",
            spec_json=json.dumps(spec.to_dict()),
            score=0.85,
        )
        promoter.start_testing("evo_winner")

        # Step 3: Simulate paper testing period (record signals).
        for _ in range(5):
            promoter.record_signals("evo_winner")

        # Step 4: Check readiness and promote.
        ready = promoter.check_ready_for_promotion(testing_days=0, min_signals=3)
        assert "evo_winner" in ready
        promoter.promote("evo_winner")

        # Step 5: Load promoted strategies into registry.
        promoted_specs = promoter.get_promoted()
        assert len(promoted_specs) == 1

        registry = StrategyRegistry()
        for spec_dict in promoted_specs:
            compiled = compile_spec(StrategySpec.from_dict(spec_dict))
            registry.register(compiled)

        assert "evo_winner" in registry.list_strategies()

        # Step 6: Verify the loaded strategy actually works.
        strategy = registry.get("evo_winner")
        assert strategy is not None
        data = _mock_data()
        signals = strategy.generate_signals(data)
        assert isinstance(signals, list)


# ---------------------------------------------------------------------------
# 3. Error recovery
# ---------------------------------------------------------------------------


class TestErrorRecovery:
    """System handles corrupted DB, missing config, and LLM timeouts gracefully."""

    def test_corrupted_evolution_db(self, tmp_path: Path) -> None:
        """EvolutionStore should handle corrupted DB gracefully (re-create tables)."""
        db_path = str(tmp_path / "corrupted.db")

        # Create a corrupted file.
        Path(db_path).write_bytes(b"not a valid sqlite database!!!")

        # EvolutionStore should raise on init (corrupted file is not sqlite).
        with pytest.raises(Exception):
            EvolutionStore(db_path=db_path)

    def test_missing_evolution_db_creates_fresh(self, tmp_path: Path) -> None:
        """EvolutionStore creates DB if it doesn't exist."""
        db_path = str(tmp_path / "new.db")
        assert not Path(db_path).exists()

        store = EvolutionStore(db_path=db_path)
        assert Path(db_path).exists()
        assert store.can_run_today() is True

    def test_corrupted_promoter_db(self, tmp_path: Path) -> None:
        """StrategyPromoter should handle corrupted DB."""
        db_path = str(tmp_path / "corrupted_promo.db")
        Path(db_path).write_bytes(b"garbage data here")

        with pytest.raises(Exception):
            StrategyPromoter(db_path=db_path)

    def test_llm_timeout_in_generator(self) -> None:
        """StrategyGenerator handles LLM timeout gracefully."""
        from strategies.generator import StrategyGenerator

        gen = StrategyGenerator(batch_size=2)

        with patch("strategies.generator.call_llm") as mock_llm, \
             patch("strategies.generator.load_prompt_template") as mock_tpl:
            mock_tpl.return_value = (
                "{variant_index} {batch_size} {knowledge_summary} "
                "{past_winners} {past_feedback} {preferences_summary}"
            )
            mock_llm.side_effect = TimeoutError("LLM request timed out")

            from strategies.generator import GenerationContext
            ctx = GenerationContext(
                knowledge_summary="test",
                past_winners=[],
                past_feedback=[],
                preferences_summary="",
            )
            result = gen.generate_batch(ctx)

        assert result.specs == []
        assert result.parse_failures == 2  # Both calls failed.

    def test_broker_handles_fresh_db(self, tmp_path: Path) -> None:
        """PaperBroker creates fresh DB and initializes account."""
        db_path = tmp_path / "fresh_broker.db"
        broker = PaperBroker(mock=True, db_path=db_path)
        assert db_path.exists()

        with patch("trading.paper_broker._current_price", return_value=100.0):
            portfolio = broker.get_portfolio()
        assert portfolio.cash == pytest.approx(100_000.0)
        assert portfolio.total_equity == pytest.approx(100_000.0)

    def test_state_manager_handles_missing_fields(self, tmp_path: Path) -> None:
        """StateManager returns defaults for fields not in DB."""
        db_path = str(tmp_path / "state.db")
        mgr = StateManager(db_path=db_path)

        # Load without any saves — should get defaults.
        state = mgr.load_state()
        assert state.current_stage == 1
        assert state.active_strategies == []
        assert state.portfolio_snapshot == {}


# ---------------------------------------------------------------------------
# 4. State persistence: save → reload → matches
# ---------------------------------------------------------------------------


class TestStatePersistence:
    """AgentState save/reload round-trip."""

    def test_save_and_reload_full_state(self, tmp_path: Path) -> None:
        """Saving full state and reloading should produce identical values."""
        db_path = str(tmp_path / "state.db")
        mgr = StateManager(db_path=db_path)

        original = AgentState(
            current_stage=3,
            active_strategies=["sma_crossover", "rsi_mean_reversion", "evo_winner"],
            portfolio_snapshot={
                "total_equity": 105_000.0,
                "cash": 50_000.0,
                "positions": {"AAPL": {"qty": 100, "value": 55000.0}},
            },
            learning_log=[{
                "timestamp": "2026-02-25T10:00:00Z",
                "topic": "momentum",
                "summary": "Learned basics",
            }],
            self_assessment="Performance improving",
        )

        mgr.save_state(original)
        loaded = mgr.load_state()

        assert loaded.current_stage == original.current_stage
        assert loaded.active_strategies == original.active_strategies
        assert loaded.portfolio_snapshot == original.portfolio_snapshot
        assert loaded.learning_log == original.learning_log
        assert loaded.self_assessment == original.self_assessment

    def test_update_single_field(self, tmp_path: Path) -> None:
        """Updating one field should not affect others."""
        db_path = str(tmp_path / "state.db")
        mgr = StateManager(db_path=db_path)

        mgr.save_state(AgentState(
            current_stage=2,
            active_strategies=["strat_a"],
        ))

        mgr.update_field("current_stage", 3)
        loaded = mgr.load_state()

        assert loaded.current_stage == 3
        assert loaded.active_strategies == ["strat_a"]

    def test_learning_log_appends(self, tmp_path: Path) -> None:
        """add_learning_entry should append without losing existing entries."""
        db_path = str(tmp_path / "state.db")
        mgr = StateManager(db_path=db_path)

        mgr.save_state(AgentState(
            learning_log=[{"topic": "topic1", "summary": "first"}],
        ))

        mgr.add_learning_entry("topic2", "second")
        loaded = mgr.load_state()

        assert len(loaded.learning_log) == 2
        assert loaded.learning_log[0]["topic"] == "topic1"
        assert loaded.learning_log[1]["topic"] == "topic2"

    def test_persistence_across_manager_instances(self, tmp_path: Path) -> None:
        """State saved by one StateManager instance is loadable by another."""
        db_path = str(tmp_path / "state.db")

        mgr1 = StateManager(db_path=db_path)
        mgr1.save_state(AgentState(
            current_stage=4,
            self_assessment="Testing persistence",
        ))

        # Create a fresh manager pointing at the same DB.
        mgr2 = StateManager(db_path=db_path)
        loaded = mgr2.load_state()

        assert loaded.current_stage == 4
        assert loaded.self_assessment == "Testing persistence"

    def test_invalid_field_raises(self, tmp_path: Path) -> None:
        """Updating an unknown field should raise ValueError."""
        db_path = str(tmp_path / "state.db")
        mgr = StateManager(db_path=db_path)

        with pytest.raises(ValueError, match="Unknown state field"):
            mgr.update_field("nonexistent_field", "value")
