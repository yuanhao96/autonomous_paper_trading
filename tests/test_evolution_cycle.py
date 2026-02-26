"""Integration tests for the evolution cycle orchestration."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from evaluation.multi_period import MultiPeriodBacktester, PeriodConfig
from evaluation.tournament import Tournament
from evolution.cycle import EvolutionCycle, EvolutionCycleResult
from evolution.planner import EvolutionPlanner
from evolution.store import EvolutionStore
from knowledge.store import MarkdownMemory
from strategies.generator import StrategyGenerator
from strategies.spec import (
    CompositeCondition,
    ConditionSpec,
    IndicatorSpec,
    StrategySpec,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _valid_spec(name: str = "test_sma") -> StrategySpec:
    return StrategySpec(
        name=name,
        version="0.1.0",
        description="SMA crossover test",
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


def _mock_data_fetcher(ticker, start, end, interval="1d"):
    np.random.seed(hash(start) % 10000)
    n = 400
    close = 100.0 + np.cumsum(np.random.normal(0.05, 1.0, n))
    close = np.maximum(close, 1.0)
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B")
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
    df.attrs["ticker"] = ticker
    return df


@pytest.fixture
def evo_db(tmp_path: Path) -> str:
    return str(tmp_path / "test_evolution.db")


@pytest.fixture
def store(evo_db: str) -> EvolutionStore:
    return EvolutionStore(db_path=evo_db)


@pytest.fixture
def backtester() -> MultiPeriodBacktester:
    periods = [
        PeriodConfig("A", "2020-01-01", "2021-06-30", 1.0),
        PeriodConfig("B", "2021-07-01", "2022-12-31", 1.5),
    ]
    return MultiPeriodBacktester(
        periods=periods,
        min_sharpe_floor=-999,  # Lenient for testing.
        ticker="SPY",
        data_fetcher=_mock_data_fetcher,
    )


# ---------------------------------------------------------------------------
# Store tests
# ---------------------------------------------------------------------------


class TestEvolutionStore:
    def test_cycle_lifecycle(self, store: EvolutionStore) -> None:
        cycle_id = store.start_cycle("test")
        assert cycle_id >= 1

        store.complete_cycle(cycle_id, 0.5)

        with sqlite3.connect(store._db_path) as conn:
            row = conn.execute(
                "SELECT status, best_score FROM cycles WHERE id = ?", (cycle_id,)
            ).fetchone()
        assert row[0] == "completed"
        assert row[1] == pytest.approx(0.5)

    def test_can_run_today(self, store: EvolutionStore) -> None:
        assert store.can_run_today()

        cycle_id = store.start_cycle("test")
        store.complete_cycle(cycle_id, 1.0)

        assert not store.can_run_today()

    def test_save_and_get_winners(self, store: EvolutionStore) -> None:
        cycle_id = store.start_cycle("test")
        spec = _valid_spec()
        store.save_spec_result(
            cycle_id, json.dumps(spec.to_dict()), spec.name, 0.8, 1, True
        )
        store.complete_cycle(cycle_id, 0.8)

        winners = store.get_recent_winners(limit=5)
        assert len(winners) == 1
        assert winners[0]["name"] == "test_sma"

    def test_save_and_get_feedback(self, store: EvolutionStore) -> None:
        cycle_id = store.start_cycle("test")
        store.save_feedback(cycle_id, "test_strategy", "Good momentum strategy", [])
        store.complete_cycle(cycle_id, 0.5)

        feedback = store.get_recent_feedback(limit=5)
        assert len(feedback) == 1
        assert "momentum" in feedback[0]

    def test_exhaustion_not_detected_few_cycles(self, store: EvolutionStore) -> None:
        for i in range(3):
            cid = store.start_cycle("test")
            store.complete_cycle(cid, 0.5)
        assert not store.check_exhaustion(plateau_cycles=5, min_improvement=0.01)

    def test_exhaustion_detected(self, store: EvolutionStore) -> None:
        for i in range(5):
            cid = store.start_cycle("test")
            store.complete_cycle(cid, 0.500)
        assert store.check_exhaustion(plateau_cycles=5, min_improvement=0.01)


# ---------------------------------------------------------------------------
# Full cycle integration test
# ---------------------------------------------------------------------------


class TestEvolutionCycle:
    @patch("strategies.generator.call_llm")
    @patch("strategies.generator.load_prompt_template")
    def test_full_cycle(
        self,
        mock_template,
        mock_llm,
        store: EvolutionStore,
        backtester: MultiPeriodBacktester,
    ) -> None:
        """Full cycle: generate → compile → backtest → tournament → audit → persist."""
        mock_template.return_value = (
            "{variant_index} {batch_size} {knowledge_summary} "
            "{past_winners} {past_feedback} {preferences_summary}"
        )
        spec = _valid_spec()
        mock_llm.return_value = json.dumps(spec.to_dict())

        generator = StrategyGenerator(batch_size=3)
        memory = MagicMock(spec=MarkdownMemory)
        memory.search.return_value = []

        planner = EvolutionPlanner(memory, generator, store)
        tournament = Tournament(backtester, survivor_count=2)

        # Mock the auditor to avoid LLM calls.
        auditor = MagicMock()
        mock_report = MagicMock()
        mock_report.findings = []
        mock_report.feedback = "Looks good"
        mock_report.passed = True
        auditor.audit_strategy_spec.return_value = mock_report

        cycle = EvolutionCycle(
            planner=planner,
            backtester=backtester,
            tournament=tournament,
            auditor=auditor,
            store=store,
            settings={
                "batch_size": 3,
                "survivor_count": 2,
                "exhaustion_detection": {"plateau_cycles": 5, "min_score_improvement": 0.01},
            },
        )

        result = cycle.run(trigger="test")

        assert isinstance(result, EvolutionCycleResult)
        assert result.cycle_id >= 1
        assert result.specs_generated == 3
        assert result.specs_compiled == 3
        assert result.tournament_result is not None
        assert isinstance(result.best_score, float)

        # Verify DB has records.
        with sqlite3.connect(store._db_path) as conn:
            cycles = conn.execute("SELECT COUNT(*) FROM cycles").fetchone()[0]
            specs = conn.execute("SELECT COUNT(*) FROM strategy_specs").fetchone()[0]
        assert cycles == 1
        assert specs == 3

    @patch("strategies.generator.call_llm")
    @patch("strategies.generator.load_prompt_template")
    def test_daily_limit(
        self,
        mock_template,
        mock_llm,
        store: EvolutionStore,
        backtester: MultiPeriodBacktester,
    ) -> None:
        """Second run on the same day should be blocked."""
        mock_template.return_value = (
            "{variant_index} {batch_size} {knowledge_summary} "
            "{past_winners} {past_feedback} {preferences_summary}"
        )
        spec = _valid_spec()
        mock_llm.return_value = json.dumps(spec.to_dict())

        generator = StrategyGenerator(batch_size=2)
        memory = MagicMock(spec=MarkdownMemory)
        memory.search.return_value = []

        planner = EvolutionPlanner(memory, generator, store)
        tournament = Tournament(backtester, survivor_count=1)
        auditor = MagicMock()
        mock_report = MagicMock()
        mock_report.findings = []
        mock_report.feedback = ""
        mock_report.passed = True
        auditor.audit_strategy_spec.return_value = mock_report

        cycle = EvolutionCycle(
            planner=planner,
            backtester=backtester,
            tournament=tournament,
            auditor=auditor,
            store=store,
            settings={"batch_size": 2, "survivor_count": 1, "exhaustion_detection": {}},
        )

        # First run should succeed.
        result1 = cycle.run(trigger="test")
        assert result1.specs_generated > 0

        # Second run should be blocked.
        result2 = cycle.run(trigger="test")
        assert result2.specs_generated == 0


class TestAuditBlocksPromotion:
    """Verify that audit failures prevent strategy promotion."""

    @patch("strategies.generator.call_llm")
    @patch("strategies.generator.load_prompt_template")
    def test_failed_audit_blocks_promotion(
        self,
        mock_template,
        mock_llm,
        store: EvolutionStore,
        backtester: MultiPeriodBacktester,
        tmp_path: Path,
    ) -> None:
        """Strategies that fail audit should NOT be submitted as candidates."""
        from evolution.promoter import StrategyPromoter

        mock_template.return_value = (
            "{variant_index} {batch_size} {knowledge_summary} "
            "{past_winners} {past_feedback} {preferences_summary}"
        )
        spec = _valid_spec()
        mock_llm.return_value = json.dumps(spec.to_dict())

        generator = StrategyGenerator(batch_size=2)
        memory = MagicMock(spec=MarkdownMemory)
        memory.search.return_value = []
        planner = EvolutionPlanner(memory, generator, store)
        tournament = Tournament(backtester, survivor_count=2)

        # Auditor returns a FAILED report.
        auditor = MagicMock()
        mock_report = MagicMock()
        mock_report.findings = [MagicMock(
            check_name="test", severity="critical", description="bad",
        )]
        mock_report.feedback = "Fix this"
        mock_report.passed = False
        auditor.audit_strategy_spec.return_value = mock_report

        promoter = StrategyPromoter(
            db_path=str(tmp_path / "promo.db"),
        )

        cycle = EvolutionCycle(
            planner=planner,
            backtester=backtester,
            tournament=tournament,
            auditor=auditor,
            store=store,
            promoter=promoter,
            settings={
                "batch_size": 2, "survivor_count": 2,
                "exhaustion_detection": {},
            },
        )

        result = cycle.run(trigger="test")
        assert result.specs_generated > 0

        # No candidates should be submitted because audit failed.
        candidates = promoter.get_candidates()
        assert len(candidates) == 0

    @patch("strategies.generator.call_llm")
    @patch("strategies.generator.load_prompt_template")
    def test_audit_exception_blocks_promotion(
        self,
        mock_template,
        mock_llm,
        store: EvolutionStore,
        backtester: MultiPeriodBacktester,
        tmp_path: Path,
    ) -> None:
        """If auditor raises an exception, strategy should NOT be promoted."""
        from evolution.promoter import StrategyPromoter

        mock_template.return_value = (
            "{variant_index} {batch_size} {knowledge_summary} "
            "{past_winners} {past_feedback} {preferences_summary}"
        )
        spec = _valid_spec()
        mock_llm.return_value = json.dumps(spec.to_dict())

        generator = StrategyGenerator(batch_size=2)
        memory = MagicMock(spec=MarkdownMemory)
        memory.search.return_value = []
        planner = EvolutionPlanner(memory, generator, store)
        tournament = Tournament(backtester, survivor_count=2)

        # Auditor raises an exception.
        auditor = MagicMock()
        auditor.audit_strategy_spec.side_effect = RuntimeError("LLM down")

        promoter = StrategyPromoter(
            db_path=str(tmp_path / "promo.db"),
        )

        cycle = EvolutionCycle(
            planner=planner,
            backtester=backtester,
            tournament=tournament,
            auditor=auditor,
            store=store,
            promoter=promoter,
            settings={
                "batch_size": 2, "survivor_count": 2,
                "exhaustion_detection": {},
            },
        )

        result = cycle.run(trigger="test")
        assert result.specs_generated > 0

        # No candidates because auditor crashed.
        candidates = promoter.get_candidates()
        assert len(candidates) == 0


class TestExhaustionBlocksCycle:
    """Verify that exhaustion detection blocks new cycles."""

    def test_exhaustion_skips_generation(
        self, store: EvolutionStore, backtester: MultiPeriodBacktester,
    ) -> None:
        """When exhaustion is detected, cycle should abort before generation."""
        # Seed 5 identical-score cycles to trigger exhaustion.
        for _ in range(5):
            cid = store.start_cycle("test")
            store.complete_cycle(cid, 0.500)

        auditor = MagicMock()
        cycle = EvolutionCycle(
            backtester=backtester,
            auditor=auditor,
            store=store,
            settings={
                "batch_size": 2,
                "survivor_count": 1,
                "exhaustion_detection": {
                    "plateau_cycles": 5,
                    "min_score_improvement": 0.01,
                },
            },
        )

        # Bypass daily limit (seeded cycles completed "today") so
        # the exhaustion check actually runs.
        with patch.object(store, "can_run_today", return_value=True):
            result = cycle.run(trigger="test")

        assert result.exhaustion_detected is True
        assert result.specs_generated == 0
        assert result.cycle_id == 0  # No cycle started.


class TestFeedbackRetrieval:
    """Verify that past feedback is loaded and passed to the generator."""

    def test_planner_loads_feedback(self, store: EvolutionStore) -> None:
        # Save some feedback.
        cid = store.start_cycle("test")
        store.save_feedback(cid, "strat_a", "Reduce drawdown", [])
        store.save_feedback(cid, "strat_b", "Add stop loss", [])
        store.complete_cycle(cid, 0.5)

        memory = MagicMock(spec=MarkdownMemory)
        memory.search.return_value = []
        generator = MagicMock(spec=StrategyGenerator)
        planner = EvolutionPlanner(memory, generator, store)

        context = planner.plan_generation()

        assert len(context.past_feedback) == 2
        assert "Reduce drawdown" in context.past_feedback
        assert "Add stop loss" in context.past_feedback


class TestRegistrySurvivorLoading:
    def test_load_survivors(self, store: EvolutionStore) -> None:
        from strategies.registry import StrategyRegistry

        cycle_id = store.start_cycle("test")
        spec = _valid_spec("evolved_sma")
        store.save_spec_result(
            cycle_id, json.dumps(spec.to_dict()), spec.name, 0.7, 1, True
        )
        store.complete_cycle(cycle_id, 0.7)

        registry = StrategyRegistry()
        loaded = registry.load_survivors_from_store(store)

        assert loaded == 1
        assert "evolved_sma" in registry.list_strategies()
