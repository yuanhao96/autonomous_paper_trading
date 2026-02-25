"""Tests for multi-period backtesting and tournament selection."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from evaluation.multi_period import (
    MultiPeriodBacktester,
    MultiPeriodResult,
    PeriodConfig,
)
from evaluation.tournament import Tournament
from strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from strategies.sma_crossover import SMACrossoverStrategy

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_synthetic_data(n: int = 400, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV data without network calls."""
    np.random.seed(seed)
    close = 100.0 + np.cumsum(np.random.normal(0.05, 1.0, n))
    close = np.maximum(close, 1.0)
    dates = pd.bdate_range("2020-01-01", periods=n, freq="B")
    df = pd.DataFrame(
        {
            "Open": close * (1 + np.random.uniform(-0.01, 0.01, n)),
            "High": close * (1 + np.random.uniform(0.0, 0.02, n)),
            "Low": close * (1 - np.random.uniform(0.0, 0.02, n)),
            "Close": close,
            "Volume": np.random.randint(100_000, 10_000_000, n),
        },
        index=dates,
    )
    return df


def _mock_data_fetcher(ticker: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    """Deterministic data fetcher that ignores date range (returns same synthetic data)."""
    return _make_synthetic_data(n=400, seed=hash(start) % 10000)


@pytest.fixture
def short_periods() -> list[PeriodConfig]:
    """Two short periods for fast testing."""
    return [
        PeriodConfig(name="Period A", start="2020-01-01", end="2021-06-30", weight=1.0),
        PeriodConfig(name="Period B", start="2021-07-01", end="2022-12-31", weight=1.5),
    ]


@pytest.fixture
def backtester(short_periods: list[PeriodConfig]) -> MultiPeriodBacktester:
    return MultiPeriodBacktester(
        periods=short_periods,
        min_sharpe_floor=-0.5,
        ticker="SPY",
        data_fetcher=_mock_data_fetcher,
    )


# ---------------------------------------------------------------------------
# Multi-period backtesting tests
# ---------------------------------------------------------------------------


class TestMultiPeriodBacktester:
    def test_run_returns_result(self, backtester: MultiPeriodBacktester) -> None:
        strategy = SMACrossoverStrategy()
        result = backtester.run(strategy)
        assert isinstance(result, MultiPeriodResult)
        assert result.strategy_name == "sma_crossover"
        assert len(result.period_results) == 2

    def test_composite_score_computed(self, backtester: MultiPeriodBacktester) -> None:
        strategy = SMACrossoverStrategy()
        result = backtester.run(strategy)
        if not result.disqualified:
            # Composite score should be some finite value.
            assert isinstance(result.composite_score, float)
            assert np.isfinite(result.composite_score)

    def test_floor_check(self, short_periods: list[PeriodConfig]) -> None:
        """Very strict floor should disqualify most strategies."""
        strict_bt = MultiPeriodBacktester(
            periods=short_periods,
            min_sharpe_floor=100.0,  # Impossible to pass.
            ticker="SPY",
            data_fetcher=_mock_data_fetcher,
        )
        strategy = SMACrossoverStrategy()
        result = strict_bt.run(strategy)
        assert result.disqualified
        assert "floor" in result.disqualification_reason.lower()

    def test_rank_orders_by_score(self, backtester: MultiPeriodBacktester) -> None:
        sma = SMACrossoverStrategy()
        rsi = RSIMeanReversionStrategy()
        results = [backtester.run(sma), backtester.run(rsi)]
        ranked = backtester.rank(results)

        # Non-disqualified should come first.
        non_dq = [r for r in ranked if not r.disqualified]
        for i in range(len(non_dq) - 1):
            assert non_dq[i].composite_score >= non_dq[i + 1].composite_score

    def test_empty_data_handled(self) -> None:
        """If the data fetcher returns empty, the strategy should be DQ'd or get empty periods."""
        def empty_fetcher(ticker, start, end, interval="1d"):
            return pd.DataFrame()

        bt = MultiPeriodBacktester(
            periods=[PeriodConfig("Empty", "2020-01-01", "2020-06-01", 1.0)],
            min_sharpe_floor=-999,
            ticker="SPY",
            data_fetcher=empty_fetcher,
        )
        result = bt.run(SMACrossoverStrategy())
        # Should not crash; either has empty period_results or is DQ'd.
        assert isinstance(result, MultiPeriodResult)


# ---------------------------------------------------------------------------
# Tournament tests
# ---------------------------------------------------------------------------


class TestTournament:
    def test_survivors_selected(self, backtester: MultiPeriodBacktester) -> None:
        tournament = Tournament(backtester, survivor_count=1)
        strategies = [SMACrossoverStrategy(), RSIMeanReversionStrategy()]
        result = tournament.run(strategies, cycle_number=1)

        assert result.cycle_number == 1
        assert len(result.survivors) <= 1
        assert len(result.all_results) == 2
        assert len(result.survivors) + len(result.eliminated) == 2

    def test_more_survivors_than_candidates(
        self, backtester: MultiPeriodBacktester
    ) -> None:
        """If survivor_count >= candidates, all survive."""
        tournament = Tournament(backtester, survivor_count=10)
        strategies = [SMACrossoverStrategy()]
        result = tournament.run(strategies, cycle_number=0)
        assert len(result.survivors) == 1
        assert len(result.eliminated) == 0

    def test_exception_handling(self, backtester: MultiPeriodBacktester) -> None:
        """A strategy that crashes should be DQ'd, not crash the tournament."""

        class CrashingStrategy:
            name = "crasher"
            version = "0.0.0"
            def generate_signals(self, data):
                raise RuntimeError("boom")
            def describe(self):
                return "crashes"

        tournament = Tournament(backtester, survivor_count=1)
        result = tournament.run([CrashingStrategy(), SMACrossoverStrategy()], cycle_number=0)
        # The crasher should be DQ'd.
        dq_names = [r.strategy_name for r in result.all_results if r.disqualified]
        assert "crasher" in dq_names
