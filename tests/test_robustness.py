"""Edge-case tests for template engine and backtester robustness."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from evaluation.backtester import BacktestConfig, Backtester
from strategies.spec import (
    CompositeCondition,
    ConditionSpec,
    IndicatorSpec,
    RiskParams,
    StrategySpec,
)
from strategies.template_engine import compile_spec

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv(n: int = 100, start: str = "2023-01-01") -> pd.DataFrame:
    """Generate a minimal valid OHLCV DataFrame."""
    dates = pd.bdate_range(start, periods=n)
    rng = np.random.default_rng(42)
    close = 100.0 + np.cumsum(rng.standard_normal(n))
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": rng.integers(1000, 10000, n),
        },
        index=dates,
    )


def _make_spec() -> StrategySpec:
    """Return a simple SMA crossover spec for testing."""
    return StrategySpec(
        name="test_sma_cross",
        version="1.0",
        description="SMA crossover for robustness testing",
        indicators=[
            IndicatorSpec(name="sma", params={"period": 5}, output_key="fast_sma"),
            IndicatorSpec(name="sma", params={"period": 20}, output_key="slow_sma"),
        ],
        entry_conditions=CompositeCondition(
            logic="ALL_OF",
            conditions=[
                ConditionSpec(operator="cross_above", left="fast_sma", right="slow_sma"),
            ],
        ),
        exit_conditions=CompositeCondition(
            logic="ALL_OF",
            conditions=[
                ConditionSpec(operator="cross_below", left="fast_sma", right="slow_sma"),
            ],
        ),
        risk=RiskParams(),
    )


# ---------------------------------------------------------------------------
# Template Engine Robustness
# ---------------------------------------------------------------------------


class TestTemplateEngineMissingColumns:
    """Template engine should handle missing OHLCV columns."""

    def test_missing_volume_returns_empty(self) -> None:
        spec = _make_spec()
        strategy = compile_spec(spec)
        data = _make_ohlcv(50).drop(columns=["Volume"])
        signals = strategy.generate_signals(data)
        assert signals == []

    def test_missing_close_returns_empty(self) -> None:
        spec = _make_spec()
        strategy = compile_spec(spec)
        data = _make_ohlcv(50).drop(columns=["Close"])
        signals = strategy.generate_signals(data)
        assert signals == []

    def test_empty_dataframe_returns_empty(self) -> None:
        spec = _make_spec()
        strategy = compile_spec(spec)
        data = pd.DataFrame()
        signals = strategy.generate_signals(data)
        assert signals == []

    def test_single_row_returns_empty(self) -> None:
        spec = _make_spec()
        strategy = compile_spec(spec)
        data = _make_ohlcv(1)
        signals = strategy.generate_signals(data)
        assert signals == []


class TestTemplateEngineNaNData:
    """Template engine should handle NaN values in indicators."""

    def test_all_nan_close_returns_no_crash(self) -> None:
        spec = _make_spec()
        strategy = compile_spec(spec)
        data = _make_ohlcv(50)
        data["Close"] = np.nan
        # Should not crash; may return empty signals.
        signals = strategy.generate_signals(data)
        assert isinstance(signals, list)

    def test_partial_nan_does_not_crash(self) -> None:
        spec = _make_spec()
        strategy = compile_spec(spec)
        data = _make_ohlcv(50)
        data.loc[data.index[:10], "Close"] = np.nan
        signals = strategy.generate_signals(data)
        assert isinstance(signals, list)


class TestTemplateEngineInvalidIndicator:
    """Template engine should handle unknown indicator names gracefully."""

    def test_unknown_indicator_returns_empty_signals(self) -> None:
        spec = StrategySpec(
            name="bad_indicator",
            version="1.0",
            description="Uses a non-existent indicator",
            indicators=[
                IndicatorSpec(name="nonexistent_indicator", params={}, output_key="bad"),
            ],
            entry_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(operator="greater_than", left="bad", right="50"),
                ],
            ),
            exit_conditions=CompositeCondition(logic="ALL_OF", conditions=[]),
            risk=RiskParams(),
        )
        # validate() will catch this, but compile_spec raises ValueError.
        with pytest.raises(ValueError):
            compile_spec(spec)


class TestTemplateEngineInsufficientBars:
    """Template engine should handle data too short for indicators."""

    def test_short_data_for_long_period_sma(self) -> None:
        """SMA with period=50 on only 10 bars of data."""
        spec = StrategySpec(
            name="long_sma",
            version="1.0",
            description="Needs 50 bars",
            indicators=[
                IndicatorSpec(name="sma", params={"period": 50}, output_key="long_sma"),
            ],
            entry_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(operator="greater_than", left="long_sma", right="100"),
                ],
            ),
            exit_conditions=CompositeCondition(logic="ALL_OF", conditions=[]),
            risk=RiskParams(),
        )
        strategy = compile_spec(spec)
        data = _make_ohlcv(10)
        # SMA of 50 on 10 bars → all NaN → no signals (not a crash).
        signals = strategy.generate_signals(data)
        assert isinstance(signals, list)


# ---------------------------------------------------------------------------
# Backtester Robustness
# ---------------------------------------------------------------------------


class TestBacktesterEdgeCases:
    """Backtester should handle edge cases without crashing."""

    def test_nan_prices_in_data(self) -> None:
        """Backtester should handle NaN values in OHLCV."""
        data = _make_ohlcv(400)
        data.loc[data.index[200:210], "Open"] = np.nan
        data.loc[data.index[200:210], "Close"] = np.nan
        config = BacktestConfig(train_window_days=100, test_window_days=50, step_days=50)
        bt = Backtester(config)

        from strategies.sma_crossover import SMACrossoverStrategy
        result = bt.run(SMACrossoverStrategy(), data)
        assert result.windows_used > 0

    def test_very_short_data(self) -> None:
        """Backtester with data shorter than one window returns empty."""
        data = _make_ohlcv(10)
        config = BacktestConfig(train_window_days=100, test_window_days=50)
        bt = Backtester(config)

        from strategies.sma_crossover import SMACrossoverStrategy
        result = bt.run(SMACrossoverStrategy(), data)
        assert result.windows_used == 0
        assert result.trades == []

    def test_single_test_day_window(self) -> None:
        """Backtester with test_window_days=2 should work (skip i=0, use i=1)."""
        data = _make_ohlcv(200)
        config = BacktestConfig(train_window_days=100, test_window_days=2, step_days=2)
        bt = Backtester(config)

        from strategies.sma_crossover import SMACrossoverStrategy
        result = bt.run(SMACrossoverStrategy(), data)
        # Should still produce windows without crashing.
        assert result.windows_used >= 1

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame should return empty result."""
        data = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        bt = Backtester()

        from strategies.sma_crossover import SMACrossoverStrategy
        result = bt.run(SMACrossoverStrategy(), data)
        assert result.windows_used == 0


class TestBacktesterMinimumSlice:
    """The backtester day-by-day roll should not pass 1-bar slices."""

    def test_no_single_bar_slices(self) -> None:
        """Verify the strategy never receives a 1-bar DataFrame."""
        received_lengths: list[int] = []

        class LengthTracker:
            def generate_signals(self, data: pd.DataFrame) -> list:
                received_lengths.append(len(data))
                return []

        data = _make_ohlcv(400)
        config = BacktestConfig(train_window_days=100, test_window_days=50, step_days=50)
        bt = Backtester(config)
        bt.run(LengthTracker(), data)

        assert len(received_lengths) > 0
        assert all(n >= 2 for n in received_lengths), (
            f"Strategy received 1-bar slices: {[n for n in received_lengths if n < 2]}"
        )
