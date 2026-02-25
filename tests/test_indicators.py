"""Tests for the indicator library."""

from __future__ import annotations

import pandas as pd
import pytest

from strategies.indicators import (
    INDICATOR_REGISTRY,
    adx,
    atr,
    bollinger_bands,
    ema,
    macd,
    obv,
    rsi,
    sma,
)


@pytest.fixture
def simple_data() -> pd.DataFrame:
    """Small deterministic OHLCV DataFrame for known-value checks."""
    close = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    n = len(close)
    return pd.DataFrame(
        {
            "Open": close,
            "High": [c + 0.5 for c in close],
            "Low": [c - 0.5 for c in close],
            "Close": close,
            "Volume": [100] * n,
        },
        index=pd.bdate_range("2024-01-01", periods=n),
    )


class TestSMA:
    def test_basic(self, simple_data: pd.DataFrame) -> None:
        result = sma(simple_data, period=3)
        assert len(result) == len(simple_data)
        # First 2 values should be NaN (need 3 bars).
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        # SMA of [1,2,3] period=3 should be 2.0
        assert result.iloc[2] == pytest.approx(2.0)
        # SMA of [2,3,4] period=3 should be 3.0
        assert result.iloc[3] == pytest.approx(3.0)

    def test_custom_source(self, simple_data: pd.DataFrame) -> None:
        result = sma(simple_data, period=3, source="High")
        assert result.iloc[2] == pytest.approx(2.5)


class TestEMA:
    def test_basic(self, simple_data: pd.DataFrame) -> None:
        result = ema(simple_data, period=3)
        assert len(result) == len(simple_data)
        # EMA is never NaN (ewm with adjust=False starts from first value).
        assert not pd.isna(result.iloc[0])
        # Final value should be close to recent prices.
        assert result.iloc[-1] > 7.0


class TestRSI:
    def test_trending_up(self, simple_data: pd.DataFrame) -> None:
        """Monotonically increasing prices should give RSI near 100."""
        result = rsi(simple_data, period=5)
        # After enough data points, RSI should be very high for uptrend.
        last_val = result.iloc[-1]
        assert last_val > 90.0

    def test_range(self, sample_ohlcv_data: pd.DataFrame) -> None:
        result = rsi(sample_ohlcv_data, period=14)
        valid = result.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()


class TestADX:
    def test_returns_series(self, sample_ohlcv_data: pd.DataFrame) -> None:
        result = adx(sample_ohlcv_data, period=14)
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv_data)


class TestATR:
    def test_positive(self, sample_ohlcv_data: pd.DataFrame) -> None:
        result = atr(sample_ohlcv_data, period=14)
        valid = result.dropna()
        assert (valid >= 0).all()


class TestOBV:
    def test_cumulative(self, simple_data: pd.DataFrame) -> None:
        result = obv(simple_data)
        assert len(result) == len(simple_data)
        # Monotonically increasing close → all +volume days → OBV increases.
        assert result.iloc[-1] > 0


class TestMACD:
    def test_keys(self, sample_ohlcv_data: pd.DataFrame) -> None:
        result = macd(sample_ohlcv_data)
        assert isinstance(result, dict)
        assert set(result.keys()) == {"line", "signal", "histogram"}
        for v in result.values():
            assert isinstance(v, pd.Series)
            assert len(v) == len(sample_ohlcv_data)


class TestBollingerBands:
    def test_keys(self, sample_ohlcv_data: pd.DataFrame) -> None:
        result = bollinger_bands(sample_ohlcv_data)
        assert isinstance(result, dict)
        assert set(result.keys()) == {"upper", "middle", "lower"}

    def test_band_ordering(self, sample_ohlcv_data: pd.DataFrame) -> None:
        result = bollinger_bands(sample_ohlcv_data, period=20)
        valid_idx = result["middle"].dropna().index
        upper = result["upper"].loc[valid_idx]
        middle = result["middle"].loc[valid_idx]
        lower = result["lower"].loc[valid_idx]
        assert (upper >= middle).all()
        assert (middle >= lower).all()


class TestRegistry:
    def test_all_indicators_registered(self) -> None:
        expected = {"sma", "ema", "rsi", "adx", "atr", "obv", "macd", "bollinger_bands"}
        assert set(INDICATOR_REGISTRY.keys()) == expected

    def test_callable(self) -> None:
        for name, func in INDICATOR_REGISTRY.items():
            assert callable(func), f"{name} is not callable"
