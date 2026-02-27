"""Tests for src/core/indicators.py — pure indicator functions."""

import numpy as np
import pandas as pd
import pytest

from src.core.indicators import (
    bollinger_bands,
    channel_lower,
    channel_upper,
    ema,
    ichimoku_kijun,
    ichimoku_tenkan,
    momentum_return,
    momentum_return_scalar,
    price_to_ma_ratio,
    realized_volatility,
    realized_volatility_scalar,
    rsi,
    rsi_scalar,
    sma,
    volume_ratio,
    zscore,
    zscore_scalar,
)


def _make_series(n: int = 100, start: float = 100.0, trend: float = 0.5) -> pd.Series:
    rng = np.random.default_rng(42)
    return pd.Series(start + np.cumsum(rng.normal(trend / n, 1.0, n)))


class TestSMA:
    def test_basic(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = sma(s, 3)
        assert result.iloc[-1] == pytest.approx(4.0)
        assert np.isnan(result.iloc[0])

    def test_period_one(self):
        s = pd.Series([10.0, 20.0, 30.0])
        result = sma(s, 1)
        assert result.iloc[-1] == pytest.approx(30.0)


class TestEMA:
    def test_basic(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = ema(s, 3)
        assert not np.isnan(result.iloc[-1])
        assert result.iloc[-1] > result.iloc[-2]


class TestMomentumReturn:
    def test_series(self):
        s = pd.Series([100.0, 110.0, 121.0])
        result = momentum_return(s, 1)
        assert result.iloc[-1] == pytest.approx(0.1)

    def test_scalar(self):
        s = pd.Series([100.0] * 10 + [110.0])
        assert momentum_return_scalar(s, 10) == pytest.approx(0.1)

    def test_scalar_insufficient(self):
        s = pd.Series([100.0])
        assert momentum_return_scalar(s, 10) == 0.0


class TestRSI:
    def test_uptrend_high_rsi(self):
        s = pd.Series([100.0 + i for i in range(30)])
        result = rsi(s, 14)
        assert result.iloc[-1] > 70

    def test_downtrend_low_rsi(self):
        s = pd.Series([200.0 - i * 2 for i in range(30)])
        result = rsi(s, 14)
        assert result.iloc[-1] < 30

    def test_scalar(self):
        s = pd.Series([100.0 + i for i in range(30)])
        val = rsi_scalar(s, 14)
        assert 0 <= val <= 100


class TestBollingerBands:
    def test_structure(self):
        s = _make_series(50)
        mid, upper, lower = bollinger_bands(s, 20)
        assert len(mid) == len(s)
        # Upper > Mid > Lower where not NaN
        valid = ~np.isnan(upper) & ~np.isnan(lower)
        assert (upper[valid] >= mid[valid]).all()
        assert (mid[valid] >= lower[valid]).all()


class TestRealizedVolatility:
    def test_series(self):
        s = _make_series(100)
        result = realized_volatility(s, 20)
        assert not np.isnan(result.iloc[-1])
        assert result.iloc[-1] > 0

    def test_scalar(self):
        s = _make_series(100)
        val = realized_volatility_scalar(s, 20)
        assert val > 0


class TestZScore:
    def test_series(self):
        s = pd.Series([100.0] * 20 + [120.0])
        result = zscore(s, 20)
        assert result.iloc[-1] > 2  # 120 is 2+ stdev above mean of 100

    def test_scalar(self):
        s = pd.Series([100.0] * 20 + [120.0])
        val = zscore_scalar(s, 20)
        assert val > 2

    def test_scalar_insufficient(self):
        s = pd.Series([100.0])
        assert zscore_scalar(s, 20) == 0.0


class TestPriceToMARatio:
    def test_above_ma(self):
        # Price rising → MA/price - 1 < 0 (price above MA)
        s = pd.Series([100.0 + i * 2 for i in range(30)])
        result = price_to_ma_ratio(s, 10)
        assert result.iloc[-1] < 0

    def test_below_ma(self):
        # Price dropping → MA/price - 1 > 0 (MA above price)
        s = pd.Series([200.0 - i * 2 for i in range(30)])
        result = price_to_ma_ratio(s, 10)
        assert result.iloc[-1] > 0


class TestVolumeRatio:
    def test_spike(self):
        v = pd.Series([1_000_000] * 20 + [5_000_000])
        result = volume_ratio(v, 20)
        assert result.iloc[-1] > 4


class TestIchimoku:
    def test_tenkan_kijun(self):
        high = pd.Series([110.0 + i for i in range(30)])
        low = pd.Series([90.0 + i for i in range(30)])
        tenkan = ichimoku_tenkan(high, low, 9)
        kijun = ichimoku_kijun(high, low, 26)
        assert not np.isnan(tenkan.iloc[-1])
        assert not np.isnan(kijun.iloc[-1])


class TestChannel:
    def test_upper_lower(self):
        high = pd.Series([100.0 + i for i in range(30)])
        low = pd.Series([90.0 + i for i in range(30)])
        u = channel_upper(high, 10)
        lo = channel_lower(low, 10)
        assert u.iloc[-1] > lo.iloc[-1]
