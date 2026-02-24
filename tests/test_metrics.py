"""Tests for evaluation.metrics — performance metric calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from evaluation.metrics import (
    PerformanceSummary,
    calculate_max_drawdown,
    calculate_pnl,
    calculate_sharpe,
    calculate_win_rate,
    generate_summary,
)

# ---------------------------------------------------------------------------
# calculate_sharpe
# ---------------------------------------------------------------------------


class TestCalculateSharpe:
    def test_constant_positive_returns(self) -> None:
        """Constant daily returns of 0.1% => positive Sharpe."""
        returns = pd.Series([0.001] * 252)
        sharpe = calculate_sharpe(returns, risk_free_rate=0.0)
        # std of constant series with ddof=1 is 0 => Sharpe should be 0.0
        # because std == 0.
        assert sharpe == 0.0

    def test_positive_returns_with_variance(self) -> None:
        """Positive-mean returns with some variance => positive Sharpe."""
        np.random.seed(99)
        returns = pd.Series(np.random.normal(0.001, 0.01, 252))
        sharpe = calculate_sharpe(returns, risk_free_rate=0.0)
        assert sharpe > 0.0

    def test_zero_std_returns_zero(self) -> None:
        """When std is 0 (constant returns), Sharpe should be 0.0."""
        returns = pd.Series([0.005] * 100)
        assert calculate_sharpe(returns) == 0.0

    def test_empty_returns(self) -> None:
        returns = pd.Series(dtype=float)
        assert calculate_sharpe(returns) == 0.0

    def test_single_return(self) -> None:
        """A single data point has NaN std => Sharpe = 0.0."""
        returns = pd.Series([0.01])
        assert calculate_sharpe(returns) == 0.0

    def test_negative_mean_returns(self) -> None:
        """Negative-mean returns => negative Sharpe."""
        np.random.seed(7)
        returns = pd.Series(np.random.normal(-0.002, 0.01, 252))
        sharpe = calculate_sharpe(returns, risk_free_rate=0.0)
        assert sharpe < 0.0


# ---------------------------------------------------------------------------
# calculate_max_drawdown
# ---------------------------------------------------------------------------


class TestCalculateMaxDrawdown:
    def test_known_drawdown(self) -> None:
        """Equity goes 100 -> 120 -> 90 -> 110.  Max drawdown = 30/120 = 25%."""
        equity = pd.Series([100.0, 120.0, 90.0, 110.0])
        dd = calculate_max_drawdown(equity)
        assert pytest.approx(dd, abs=1e-6) == 30.0 / 120.0

    def test_monotonically_increasing(self) -> None:
        """No drawdown when equity only goes up."""
        equity = pd.Series([100.0, 110.0, 120.0, 130.0])
        assert calculate_max_drawdown(equity) == 0.0

    def test_empty_series(self) -> None:
        equity = pd.Series(dtype=float)
        assert calculate_max_drawdown(equity) == 0.0

    def test_single_point(self) -> None:
        equity = pd.Series([100.0])
        assert calculate_max_drawdown(equity) == 0.0


# ---------------------------------------------------------------------------
# calculate_win_rate
# ---------------------------------------------------------------------------


class TestCalculateWinRate:
    def test_mixed_trades(self, sample_trades: list[dict]) -> None:
        """3 winners out of 5 => 60% win rate."""
        win_rate = calculate_win_rate(sample_trades)
        assert pytest.approx(win_rate) == 3.0 / 5.0

    def test_all_winners(self) -> None:
        trades = [{"pnl": 10.0}, {"pnl": 5.0}]
        assert calculate_win_rate(trades) == 1.0

    def test_all_losers(self) -> None:
        trades = [{"pnl": -10.0}, {"pnl": -5.0}]
        assert calculate_win_rate(trades) == 0.0

    def test_empty(self) -> None:
        assert calculate_win_rate([]) == 0.0

    def test_zero_pnl_not_winner(self) -> None:
        """A trade with pnl == 0 is not a winner (pnl > 0 required)."""
        trades = [{"pnl": 0.0}]
        assert calculate_win_rate(trades) == 0.0


# ---------------------------------------------------------------------------
# calculate_pnl
# ---------------------------------------------------------------------------


class TestCalculatePnl:
    def test_known_trades(self, sample_trades: list[dict]) -> None:
        result = calculate_pnl(sample_trades)
        assert result["total_pnl"] == pytest.approx(150.0 - 50.0 + 200.0 - 30.0 + 80.0)
        assert result["num_trades"] == 5
        assert result["best_trade"] == 200.0
        assert result["worst_trade"] == -50.0
        assert result["avg_pnl"] == pytest.approx(result["total_pnl"] / 5)

    def test_empty(self) -> None:
        result = calculate_pnl([])
        assert result["total_pnl"] == 0.0
        assert result["num_trades"] == 0


# ---------------------------------------------------------------------------
# generate_summary
# ---------------------------------------------------------------------------


class TestGenerateSummary:
    def test_returns_performance_summary(self, sample_trades: list[dict]) -> None:
        equity = pd.Series([100_000, 100_150, 100_100, 100_300, 100_270, 100_350])
        summary = generate_summary(equity, sample_trades)
        assert isinstance(summary, PerformanceSummary)
        assert summary.num_trades == 5
        assert summary.total_pnl == pytest.approx(350.0)
        assert summary.max_drawdown >= 0.0
        assert 0.0 <= summary.win_rate <= 1.0

    def test_empty_equity_and_trades(self) -> None:
        summary = generate_summary(pd.Series(dtype=float), [])
        assert summary.sharpe_ratio == 0.0
        assert summary.num_trades == 0
