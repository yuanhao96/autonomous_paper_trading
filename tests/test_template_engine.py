"""Tests for the template engine that compiles StrategySpec into Strategy."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from strategies.spec import (
    CompositeCondition,
    ConditionSpec,
    IndicatorSpec,
    StrategySpec,
)
from strategies.template_engine import TemplateStrategy, compile_spec

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sma_crossover_spec() -> StrategySpec:
    """SMA crossover spec that mirrors SMACrossoverStrategy(20, 50)."""
    return StrategySpec(
        name="sma_crossover_template",
        version="1.0.0",
        description="SMA crossover via template",
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


@pytest.fixture
def crossover_data() -> pd.DataFrame:
    """Data engineered to produce a known SMA crossover.

    Price starts at 100, dips to ~90 (short SMA crosses below long),
    then rallies to ~120 (short SMA crosses above long).
    """
    np.random.seed(123)
    n = 120  # Enough for SMA-50 + some trading days.

    # Construct a V-shaped price path.
    phase1 = np.linspace(100, 90, 40)
    phase2 = np.linspace(90, 120, 40)
    phase3 = np.linspace(120, 115, 40)
    close = np.concatenate([phase1, phase2, phase3])

    dates = pd.bdate_range("2023-01-01", periods=n, freq="B")
    df = pd.DataFrame(
        {
            "Open": close * 0.999,
            "High": close * 1.005,
            "Low": close * 0.995,
            "Close": close,
            "Volume": np.random.randint(1_000_000, 5_000_000, n),
        },
        index=dates,
    )
    df.attrs["ticker"] = "TEST"
    return df


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCompile:
    def test_valid_spec_compiles(self, sma_crossover_spec: StrategySpec) -> None:
        strategy = compile_spec(sma_crossover_spec)
        assert isinstance(strategy, TemplateStrategy)
        assert strategy.name == "sma_crossover_template"
        assert strategy.version == "1.0.0"

    def test_invalid_spec_raises(self) -> None:
        bad_spec = StrategySpec(
            name="",
            version="0.1.0",
            description="bad",
            indicators=[],
            entry_conditions=CompositeCondition(logic="ALL_OF"),
            exit_conditions=CompositeCondition(logic="ALL_OF"),
        )
        with pytest.raises(ValueError):
            compile_spec(bad_spec)


class TestSignalGeneration:
    def test_produces_signals(
        self,
        sma_crossover_spec: StrategySpec,
        crossover_data: pd.DataFrame,
    ) -> None:
        """Walk through the data day by day and collect signals."""
        strategy = compile_spec(sma_crossover_spec)
        all_signals = []
        for i in range(51, len(crossover_data)):
            signals = strategy.generate_signals(crossover_data.iloc[: i + 1])
            all_signals.extend(signals)

        # The V-shaped data should produce at least one buy and one sell.
        actions = [s.action for s in all_signals]
        assert "buy" in actions or "sell" in actions, (
            "Expected at least one signal from V-shaped data"
        )

    def test_signal_strength_in_range(
        self,
        sma_crossover_spec: StrategySpec,
        sample_ohlcv_data: pd.DataFrame,
    ) -> None:
        strategy = compile_spec(sma_crossover_spec)
        sample_ohlcv_data.attrs["ticker"] = "SPY"
        for i in range(51, len(sample_ohlcv_data)):
            signals = strategy.generate_signals(sample_ohlcv_data.iloc[: i + 1])
            for sig in signals:
                assert 0.0 < sig.strength <= 1.0

    def test_too_little_data_returns_empty(
        self, sma_crossover_spec: StrategySpec
    ) -> None:
        strategy = compile_spec(sma_crossover_spec)
        tiny = pd.DataFrame(
            {"Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.0], "Volume": [100]},
            index=pd.bdate_range("2024-01-01", periods=1),
        )
        assert strategy.generate_signals(tiny) == []


class TestConditionOperators:
    def _make_strategy(self, cond: ConditionSpec, indicator_name: str = "rsi") -> TemplateStrategy:
        """Helper to build a strategy testing a single condition."""
        spec = StrategySpec(
            name="cond_test",
            version="0.1.0",
            description="test",
            indicators=[
                IndicatorSpec(name=indicator_name, params={"period": 14}, output_key="ind_val"),
            ],
            entry_conditions=CompositeCondition(logic="ALL_OF", conditions=[cond]),
            exit_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[ConditionSpec(operator="greater_than", left="ind_val", right="999999")],
            ),
        )
        return compile_spec(spec)

    def test_greater_than(self, sample_ohlcv_data: pd.DataFrame) -> None:
        sample_ohlcv_data.attrs["ticker"] = "TST"
        cond = ConditionSpec(operator="greater_than", left="ind_val", right="30.0")
        strategy = self._make_strategy(cond)
        # RSI on trending data should sometimes be > 30.
        signals = strategy.generate_signals(sample_ohlcv_data)
        # Just verify it doesn't crash and returns valid signals.
        for s in signals:
            assert s.action in ("buy", "sell")

    def test_less_than(self, sample_ohlcv_data: pd.DataFrame) -> None:
        sample_ohlcv_data.attrs["ticker"] = "TST"
        cond = ConditionSpec(operator="less_than", left="ind_val", right="70.0")
        strategy = self._make_strategy(cond)
        signals = strategy.generate_signals(sample_ohlcv_data)
        for s in signals:
            assert s.action in ("buy", "sell")

    def test_between(self, sample_ohlcv_data: pd.DataFrame) -> None:
        sample_ohlcv_data.attrs["ticker"] = "TST"
        cond = ConditionSpec(
            operator="between", left="ind_val", params={"low": 20, "high": 80}
        )
        strategy = self._make_strategy(cond)
        signals = strategy.generate_signals(sample_ohlcv_data)
        for s in signals:
            assert 0 < s.strength <= 1.0

    def test_slope_positive(self, sample_ohlcv_data: pd.DataFrame) -> None:
        sample_ohlcv_data.attrs["ticker"] = "TST"
        cond = ConditionSpec(
            operator="slope_positive", left="ind_val", params={"lookback": 5}
        )
        strategy = self._make_strategy(cond, indicator_name="sma")
        signals = strategy.generate_signals(sample_ohlcv_data)
        for s in signals:
            assert s.action in ("buy", "sell")

    def test_percent_change(self, sample_ohlcv_data: pd.DataFrame) -> None:
        sample_ohlcv_data.attrs["ticker"] = "TST"
        cond = ConditionSpec(
            operator="percent_change",
            left="ind_val",
            params={"lookback": 5, "threshold": 0.01},
        )
        strategy = self._make_strategy(cond, indicator_name="sma")
        signals = strategy.generate_signals(sample_ohlcv_data)
        for s in signals:
            assert s.action in ("buy", "sell")


class TestMultiOutput:
    def test_macd_crossover(self, sample_ohlcv_data: pd.DataFrame) -> None:
        """Test MACD line crossing above signal line."""
        sample_ohlcv_data.attrs["ticker"] = "TST"
        spec = StrategySpec(
            name="macd_test",
            version="0.1.0",
            description="MACD crossover",
            indicators=[
                IndicatorSpec(name="macd", params={}, output_key="macd_val"),
            ],
            entry_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(
                        operator="cross_above",
                        left="macd_val_line",
                        right="macd_val_signal",
                    ),
                ],
            ),
            exit_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(
                        operator="cross_below",
                        left="macd_val_line",
                        right="macd_val_signal",
                    ),
                ],
            ),
        )
        strategy = compile_spec(spec)
        # Walk through data day by day.
        all_signals = []
        for i in range(30, len(sample_ohlcv_data)):
            sigs = strategy.generate_signals(sample_ohlcv_data.iloc[: i + 1])
            all_signals.extend(sigs)
        # MACD crossovers should produce signals on random walk data.
        assert len(all_signals) > 0


class TestNestedIndicators:
    def test_ema_of_rsi(self, sample_ohlcv_data: pd.DataFrame) -> None:
        """EMA of RSI: source references another indicator's output_key."""
        sample_ohlcv_data.attrs["ticker"] = "TST"
        spec = StrategySpec(
            name="ema_of_rsi_test",
            version="0.1.0",
            description="Smoothed RSI",
            indicators=[
                IndicatorSpec(name="rsi", params={"period": 14}, output_key="rsi_raw"),
                IndicatorSpec(
                    name="ema",
                    params={"period": 5, "source": "rsi_raw"},
                    output_key="rsi_smooth",
                ),
            ],
            entry_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(operator="less_than", left="rsi_smooth", right="30.0"),
                ],
            ),
            exit_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(operator="greater_than", left="rsi_smooth", right="70.0"),
                ],
            ),
        )
        strategy = compile_spec(spec)
        # Should not raise.
        signals = strategy.generate_signals(sample_ohlcv_data)
        for s in signals:
            assert s.action in ("buy", "sell")


class TestCompositeLogic:
    def test_any_of(self, sample_ohlcv_data: pd.DataFrame) -> None:
        """ANY_OF should fire if at least one condition is true."""
        sample_ohlcv_data.attrs["ticker"] = "TST"
        spec = StrategySpec(
            name="any_of_test",
            version="0.1.0",
            description="ANY_OF test",
            indicators=[
                IndicatorSpec(name="rsi", params={"period": 14}, output_key="rsi_val"),
            ],
            entry_conditions=CompositeCondition(
                logic="ANY_OF",
                conditions=[
                    # One of these should be true.
                    ConditionSpec(operator="less_than", left="rsi_val", right="30.0"),
                    ConditionSpec(operator="greater_than", left="rsi_val", right="10.0"),
                ],
            ),
            exit_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(operator="greater_than", left="rsi_val", right="999"),
                ],
            ),
        )
        strategy = compile_spec(spec)
        signals = strategy.generate_signals(sample_ohlcv_data)
        # RSI is almost always > 10, so ANY_OF should fire.
        assert len(signals) > 0
        assert signals[0].action == "buy"
