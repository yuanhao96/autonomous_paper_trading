"""Tests for the live signal engine."""

import numpy as np
import pandas as pd
import pytest

from src.live.signals import compute_signals, compute_target_weights
from src.strategies.spec import RiskParams, StrategySpec


def _make_spec(template: str, params: dict, **kwargs) -> StrategySpec:
    return StrategySpec(
        template=template,
        parameters=params,
        universe_id="test",
        **kwargs,
    )


def _make_price_df(prices: list[float], days: int = 0) -> pd.DataFrame:
    """Create a simple OHLCV DataFrame from close prices."""
    if days == 0:
        days = len(prices)
    idx = pd.date_range("2020-01-01", periods=days, freq="B")[:len(prices)]
    close = pd.Series(prices, index=idx)
    return pd.DataFrame({
        "Open": close * 0.99,
        "High": close * 1.01,
        "Low": close * 0.98,
        "Close": close,
        "Volume": [1_000_000] * len(close),
    })


class TestComputeSignals:
    def test_momentum_timeseries_long(self):
        """Positive return over lookback → long."""
        # Create 260 bars of uptrending prices
        prices = [100 + i * 0.5 for i in range(260)]
        spec = _make_spec("momentum/time-series-momentum", {"lookback": 252, "threshold": 0.0})
        df = _make_price_df(prices)
        signals = compute_signals(spec, {"SPY": df}, lookback_bars=253)
        assert signals["SPY"] == "long"

    def test_momentum_timeseries_flat(self):
        """Negative return over lookback → flat."""
        prices = [200 - i * 0.5 for i in range(260)]
        spec = _make_spec("momentum/time-series-momentum", {"lookback": 252, "threshold": 0.0})
        df = _make_price_df(prices)
        signals = compute_signals(spec, {"SPY": df}, lookback_bars=253)
        assert signals["SPY"] == "flat"

    def test_ma_crossover_long(self):
        """Fast MA above slow MA → long."""
        # Uptrend: fast MA will be above slow MA
        prices = [100 + i for i in range(100)]
        spec = _make_spec("technical/moving-average-crossover", {"fast_period": 10, "slow_period": 50})
        df = _make_price_df(prices)
        signals = compute_signals(spec, {"QQQ": df}, lookback_bars=51)
        assert signals["QQQ"] == "long"

    def test_ma_crossover_flat(self):
        """Fast MA below slow MA → flat."""
        # Downtrend
        prices = [200 - i for i in range(100)]
        spec = _make_spec("technical/moving-average-crossover", {"fast_period": 10, "slow_period": 50})
        df = _make_price_df(prices)
        signals = compute_signals(spec, {"QQQ": df}, lookback_bars=51)
        assert signals["QQQ"] == "flat"

    def test_rsi_oversold(self):
        """Sharp drop → RSI oversold → long."""
        # Steady price then sharp drop
        prices = [100.0] * 50 + [100 - i * 2 for i in range(20)]
        spec = _make_spec("mean-reversion/mean-reversion-rsi", {"rsi_period": 14, "oversold": 30, "overbought": 70})
        df = _make_price_df(prices)
        signals = compute_signals(spec, {"IWM": df}, lookback_bars=15)
        # After sharp drop, RSI should be oversold
        assert signals["IWM"] == "long"

    def test_breakout_long(self):
        """Price above previous high → long."""
        # Flat then breakout
        prices = [100.0] * 25 + [110.0]
        spec = _make_spec("technical/breakout", {"lookback": 20})
        df = _make_price_df(prices)
        signals = compute_signals(spec, {"SPY": df}, lookback_bars=22)
        assert signals["SPY"] == "long"

    def test_insufficient_data_flat(self):
        """Too few bars → flat signal."""
        prices = [100.0] * 5
        spec = _make_spec("momentum/time-series-momentum", {"lookback": 252})
        df = _make_price_df(prices)
        signals = compute_signals(spec, {"SPY": df}, lookback_bars=10)
        assert signals["SPY"] == "flat"

    def test_multiple_symbols(self):
        """Signals for multiple symbols."""
        up = _make_price_df([100 + i for i in range(260)])
        down = _make_price_df([200 - i * 0.5 for i in range(260)])
        spec = _make_spec("momentum/time-series-momentum", {"lookback": 252, "threshold": 0.0})
        signals = compute_signals(spec, {"UP": up, "DOWN": down}, lookback_bars=253)
        assert signals["UP"] == "long"
        assert signals["DOWN"] == "flat"

    def test_unknown_template_fallback(self):
        """Unknown template falls back to momentum time-series."""
        prices = [100 + i * 0.5 for i in range(260)]
        spec = _make_spec("unknown/template", {"lookback": 252})
        df = _make_price_df(prices)
        signals = compute_signals(spec, {"SPY": df}, lookback_bars=253)
        assert signals["SPY"] == "long"


class TestComputeTargetWeights:
    def test_equal_weight(self):
        spec = _make_spec("momentum/time-series-momentum", {}, risk=RiskParams(max_position_pct=0.10, max_positions=10))
        signals = {"SPY": "long", "QQQ": "long", "IWM": "flat"}
        weights = compute_target_weights(spec, signals)
        assert weights["SPY"] == pytest.approx(0.10)  # min(0.10, 1/2=0.50)
        assert weights["QQQ"] == pytest.approx(0.10)
        assert weights["IWM"] == 0.0

    def test_all_flat(self):
        spec = _make_spec("momentum/time-series-momentum", {})
        signals = {"SPY": "flat", "QQQ": "flat"}
        weights = compute_target_weights(spec, signals)
        assert all(w == 0.0 for w in weights.values())

    def test_max_positions_limit(self):
        spec = _make_spec("momentum/time-series-momentum", {}, risk=RiskParams(max_position_pct=0.10, max_positions=2))
        signals = {"A": "long", "B": "long", "C": "long", "D": "flat"}
        weights = compute_target_weights(spec, signals)
        long_count = sum(1 for w in weights.values() if w > 0)
        assert long_count <= 2
