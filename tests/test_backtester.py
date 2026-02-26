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


# ---------------------------------------------------------------------------
# Tests — slippage and commission realism
# ---------------------------------------------------------------------------


class TestSlippageAndCommission:
    """Verify that slippage degrades returns, commission accumulates,
    and zero-slippage matches legacy behavior."""

    def test_zero_slippage_matches_baseline(
        self,
        sample_ohlcv_data: pd.DataFrame,
        short_config: BacktestConfig,
    ) -> None:
        """BacktestConfig with explicit 0.0 slippage/commission should
        produce identical results to a config without those fields."""
        baseline = Backtester(config=short_config)
        explicit_zero = Backtester(config=BacktestConfig(
            train_window_days=short_config.train_window_days,
            test_window_days=short_config.test_window_days,
            step_days=short_config.step_days,
            slippage_pct=0.0,
            commission_per_trade=0.0,
        ))

        r_base = baseline.run(BuySellStrategy(), sample_ohlcv_data)
        r_zero = explicit_zero.run(BuySellStrategy(), sample_ohlcv_data)

        assert r_base.metrics.total_pnl == pytest.approx(r_zero.metrics.total_pnl)
        assert len(r_base.trades) == len(r_zero.trades)

    def test_slippage_degrades_returns(
        self,
        sample_ohlcv_data: pd.DataFrame,
    ) -> None:
        """Adding slippage should reduce total P&L compared to zero slippage."""
        cfg_no_slip = BacktestConfig(
            train_window_days=100, test_window_days=30, step_days=20,
            slippage_pct=0.0, commission_per_trade=0.0,
        )
        cfg_with_slip = BacktestConfig(
            train_window_days=100, test_window_days=30, step_days=20,
            slippage_pct=0.01, commission_per_trade=0.0,
        )

        r_clean = Backtester(config=cfg_no_slip).run(
            BuySellStrategy(), sample_ohlcv_data,
        )
        r_slip = Backtester(config=cfg_with_slip).run(
            BuySellStrategy(), sample_ohlcv_data,
        )

        # Slippage should reduce total P&L.
        assert r_slip.metrics.total_pnl < r_clean.metrics.total_pnl

    def test_commission_accumulates(
        self,
        sample_ohlcv_data: pd.DataFrame,
    ) -> None:
        """Commission should reduce total P&L proportionally to trade count."""
        commission = 5.0
        cfg_no_comm = BacktestConfig(
            train_window_days=100, test_window_days=30, step_days=20,
            slippage_pct=0.0, commission_per_trade=0.0,
        )
        cfg_with_comm = BacktestConfig(
            train_window_days=100, test_window_days=30, step_days=20,
            slippage_pct=0.0, commission_per_trade=commission,
        )

        r_clean = Backtester(config=cfg_no_comm).run(
            BuySellStrategy(), sample_ohlcv_data,
        )
        r_comm = Backtester(config=cfg_with_comm).run(
            BuySellStrategy(), sample_ohlcv_data,
        )

        num_trades = len(r_comm.trades)
        assert num_trades > 0
        expected_cost = num_trades * commission
        # Total P&L difference should equal total commission paid.
        pnl_diff = r_clean.metrics.total_pnl - r_comm.metrics.total_pnl
        assert pnl_diff == pytest.approx(expected_cost, abs=0.01)

    def test_slippage_affects_individual_trade_prices(
        self,
        sample_ohlcv_data: pd.DataFrame,
    ) -> None:
        """With slippage, entry prices should be higher and exit prices
        lower compared to zero slippage."""
        cfg_clean = BacktestConfig(
            train_window_days=100, test_window_days=30, step_days=20,
            slippage_pct=0.0,
        )
        cfg_slip = BacktestConfig(
            train_window_days=100, test_window_days=30, step_days=20,
            slippage_pct=0.005,
        )

        r_clean = Backtester(config=cfg_clean).run(
            BuySellStrategy(), sample_ohlcv_data,
        )
        r_slip = Backtester(config=cfg_slip).run(
            BuySellStrategy(), sample_ohlcv_data,
        )

        assert len(r_clean.trades) == len(r_slip.trades)
        for t_clean, t_slip in zip(r_clean.trades, r_slip.trades):
            # Entry should be worse (higher) with slippage.
            assert t_slip["entry_price"] >= t_clean["entry_price"]
            # Exit should be worse (lower) with slippage.
            assert t_slip["exit_price"] <= t_clean["exit_price"]

    def test_high_slippage_produces_losses(
        self,
        sample_ohlcv_data: pd.DataFrame,
    ) -> None:
        """Extreme slippage (5%) should reliably produce net losses."""
        cfg = BacktestConfig(
            train_window_days=100, test_window_days=30, step_days=20,
            slippage_pct=0.05, commission_per_trade=0.0,
        )
        result = Backtester(config=cfg).run(
            BuySellStrategy(), sample_ohlcv_data,
        )

        assert result.metrics.total_pnl < 0

    def test_combined_slippage_and_commission(
        self,
        sample_ohlcv_data: pd.DataFrame,
    ) -> None:
        """Both slippage + commission together should degrade more than either alone."""
        base = BacktestConfig(
            train_window_days=100, test_window_days=30, step_days=20,
        )
        slip_only = BacktestConfig(
            train_window_days=100, test_window_days=30, step_days=20,
            slippage_pct=0.005,
        )
        comm_only = BacktestConfig(
            train_window_days=100, test_window_days=30, step_days=20,
            commission_per_trade=5.0,
        )
        both = BacktestConfig(
            train_window_days=100, test_window_days=30, step_days=20,
            slippage_pct=0.005, commission_per_trade=5.0,
        )

        pnl_base = Backtester(config=base).run(
            BuySellStrategy(), sample_ohlcv_data,
        ).metrics.total_pnl
        pnl_slip = Backtester(config=slip_only).run(
            BuySellStrategy(), sample_ohlcv_data,
        ).metrics.total_pnl
        pnl_comm = Backtester(config=comm_only).run(
            BuySellStrategy(), sample_ohlcv_data,
        ).metrics.total_pnl
        pnl_both = Backtester(config=both).run(
            BuySellStrategy(), sample_ohlcv_data,
        ).metrics.total_pnl

        assert pnl_both < pnl_slip
        assert pnl_both < pnl_comm
        assert pnl_both < pnl_base

    def test_config_defaults_are_zero(self) -> None:
        """Default BacktestConfig should have zero slippage and commission."""
        cfg = BacktestConfig()
        assert cfg.slippage_pct == 0.0
        assert cfg.commission_per_trade == 0.0
