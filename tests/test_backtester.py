"""Tests for evaluation.backtester — walk-forward backtesting engine."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pytest

from evaluation.backtester import BacktestConfig, Backtester, BacktestResult
from evaluation.metrics import PerformanceSummary

# ---------------------------------------------------------------------------
# Mock strategy and signal
# ---------------------------------------------------------------------------


@dataclass
class MockSignal:
    ticker: str
    side: str  # "buy" or "sell"
    date: pd.Timestamp


class BuyAndHoldStrategy:
    """Issues a buy signal on the first day of each test window."""

    def generate_signals(self, data: pd.DataFrame) -> list[MockSignal]:
        if data.empty:
            return []
        return [
            MockSignal(ticker="TEST", side="buy", date=data.index[0]),
        ]


class BuySellStrategy:
    """Issues a buy signal on the first day and a sell signal mid-window."""

    def generate_signals(self, data: pd.DataFrame) -> list[MockSignal]:
        if len(data) < 4:
            return []
        return [
            MockSignal(ticker="TEST", side="buy", date=data.index[0]),
            MockSignal(ticker="TEST", side="sell", date=data.index[len(data) // 2]),
        ]


class EmptyStrategy:
    """Generates no signals."""

    def generate_signals(self, data: pd.DataFrame) -> list[MockSignal]:
        return []


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def short_config() -> BacktestConfig:
    """Use smaller windows so tests work with the 400-day sample data."""
    return BacktestConfig(
        train_window_days=100,
        test_window_days=30,
        step_days=20,
    )


# ---------------------------------------------------------------------------
# Tests — basic backtest execution
# ---------------------------------------------------------------------------


class TestBacktesterRun:
    def test_produces_backtest_result(
        self,
        sample_ohlcv_data: pd.DataFrame,
        short_config: BacktestConfig,
    ) -> None:
        bt = Backtester(config=short_config)
        result = bt.run(BuySellStrategy(), sample_ohlcv_data)

        assert isinstance(result, BacktestResult)
        assert isinstance(result.metrics, PerformanceSummary)
        assert result.windows_used > 0
        assert len(result.equity_curve) > 0

    def test_trades_have_expected_keys(
        self,
        sample_ohlcv_data: pd.DataFrame,
        short_config: BacktestConfig,
    ) -> None:
        bt = Backtester(config=short_config)
        result = bt.run(BuySellStrategy(), sample_ohlcv_data)

        if result.trades:
            trade = result.trades[0]
            expected_keys = {
                "ticker", "entry_date", "exit_date", "side",
                "entry_price", "exit_price", "pnl", "return_pct",
            }
            assert expected_keys.issubset(set(trade.keys()))

    def test_equity_curve_is_reasonable(
        self,
        sample_ohlcv_data: pd.DataFrame,
        short_config: BacktestConfig,
    ) -> None:
        bt = Backtester(config=short_config)
        result = bt.run(BuyAndHoldStrategy(), sample_ohlcv_data)

        # Equity should never be zero or negative for a long-only strategy
        # on data with positive prices.
        assert (result.equity_curve > 0).all()

    def test_empty_strategy_still_runs(
        self,
        sample_ohlcv_data: pd.DataFrame,
        short_config: BacktestConfig,
    ) -> None:
        bt = Backtester(config=short_config)
        result = bt.run(EmptyStrategy(), sample_ohlcv_data)

        assert isinstance(result, BacktestResult)
        # No trades should be generated.
        assert result.trades == []
        # Windows are still iterated (even if no signals).
        assert result.windows_used > 0


# ---------------------------------------------------------------------------
# Tests — insufficient data
# ---------------------------------------------------------------------------


class TestInsufficientData:
    def test_too_little_data_returns_empty_result(self) -> None:
        """When data is shorter than train + test windows, return empty."""
        small_data = pd.DataFrame(
            {
                "Open": [100.0] * 10,
                "High": [105.0] * 10,
                "Low": [95.0] * 10,
                "Close": [100.0] * 10,
                "Volume": [1_000_000] * 10,
            },
            index=pd.bdate_range("2023-01-01", periods=10),
        )
        bt = Backtester()  # default config: train=252, test=63
        result = bt.run(BuyAndHoldStrategy(), small_data)

        assert result.windows_used == 0
        assert result.trades == []
        assert result.equity_curve.empty


# ---------------------------------------------------------------------------
# Tests — metrics integration
# ---------------------------------------------------------------------------


class TestMetricsIntegration:
    def test_metrics_populated(
        self,
        sample_ohlcv_data: pd.DataFrame,
        short_config: BacktestConfig,
    ) -> None:
        bt = Backtester(config=short_config)
        result = bt.run(BuySellStrategy(), sample_ohlcv_data)

        m = result.metrics
        assert isinstance(m.sharpe_ratio, float)
        assert isinstance(m.max_drawdown, float)
        assert m.max_drawdown >= 0.0
        assert 0.0 <= m.win_rate <= 1.0
        assert m.num_trades >= 0
