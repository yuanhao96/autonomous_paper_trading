"""Technical indicator library for the template-based strategy engine.

Provides 8 core indicators usable in declarative strategy specs.
All functions accept an OHLCV DataFrame and return either a single
``pd.Series`` or a ``dict[str, pd.Series]`` for multi-output indicators.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Single-output indicators
# ---------------------------------------------------------------------------


def sma(data: pd.DataFrame, period: int, source: str = "Close") -> pd.Series:
    """Simple Moving Average."""
    return data[source].rolling(window=period).mean()


def ema(data: pd.DataFrame, period: int, source: str = "Close") -> pd.Series:
    """Exponential Moving Average."""
    return data[source].ewm(span=period, adjust=False).mean()


def rsi(data: pd.DataFrame, period: int = 14, source: str = "Close") -> pd.Series:
    """Relative Strength Index (Wilder's smoothing)."""
    delta = data[source].diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100.0 - (100.0 / (1.0 + rs))
    # When avg_loss is zero (pure uptrend), RS is inf → RSI should be 100.
    result = result.fillna(100.0)
    # When avg_gain is also zero (no movement), mark as 50 (neutral).
    no_movement = (avg_gain == 0) & (avg_loss == 0)
    result[no_movement] = 50.0
    return result


def adx(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Directional Index."""
    high = data["High"]
    low = data["Low"]
    close = data["Close"]

    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr_vals = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    plus_di = 100.0 * (
        plus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        / atr_vals.replace(0, np.nan)
    )
    minus_di = 100.0 * (
        minus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        / atr_vals.replace(0, np.nan)
    )

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    high = data["High"]
    low = data["Low"]
    close = data["Close"]

    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def obv(data: pd.DataFrame) -> pd.Series:
    """On-Balance Volume."""
    close = data["Close"]
    volume = data["Volume"].astype(float)

    direction = np.sign(close.diff())
    direction.iloc[0] = 0.0

    return (volume * direction).cumsum()


# ---------------------------------------------------------------------------
# Multi-output indicators
# ---------------------------------------------------------------------------


def macd(
    data: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    source: str = "Close",
) -> dict[str, pd.Series]:
    """Moving Average Convergence Divergence.

    Returns dict with keys ``line``, ``signal``, ``histogram``.
    """
    src = data[source]
    fast_ema = src.ewm(span=fast, adjust=False).mean()
    slow_ema = src.ewm(span=slow, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return {"line": macd_line, "signal": signal_line, "histogram": histogram}


def bollinger_bands(
    data: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    source: str = "Close",
) -> dict[str, pd.Series]:
    """Bollinger Bands.

    Returns dict with keys ``upper``, ``middle``, ``lower``.
    """
    src = data[source]
    middle = src.rolling(window=period).mean()
    std = src.rolling(window=period).std(ddof=0)
    upper = middle + std_dev * std
    lower = middle - std_dev * std

    return {"upper": upper, "middle": middle, "lower": lower}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

INDICATOR_REGISTRY: dict[str, Callable] = {
    "sma": sma,
    "ema": ema,
    "rsi": rsi,
    "adx": adx,
    "atr": atr,
    "obv": obv,
    "macd": macd,
    "bollinger_bands": bollinger_bands,
}

# Indicators that return dict[str, Series] instead of a single Series.
MULTI_OUTPUT_INDICATORS: set[str] = {"macd", "bollinger_bands"}
