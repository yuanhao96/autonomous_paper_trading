"""Pure indicator functions — single source of truth for all indicator math.

All functions take pd.Series (or scalar variants) and return pd.Series or float.
Used by screening (self.I() wrappers), validation (on_bar), and live signals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ── Trend / Moving Average ─────────────────────────────────────────


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=period).mean()


# ── Momentum ───────────────────────────────────────────────────────


def momentum_return(series: pd.Series, lookback: int) -> pd.Series:
    """N-bar lookback return: series / series.shift(lookback) - 1."""
    return series / series.shift(lookback) - 1


def momentum_return_scalar(series: pd.Series, lookback: int) -> float:
    """Scalar version: latest N-bar lookback return."""
    if len(series) < lookback + 1:
        return 0.0
    return float(series.iloc[-1] / series.iloc[-lookback - 1] - 1)


# ── RSI ────────────────────────────────────────────────────────────


def rsi(series: pd.Series, period: int) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    result = 100 - (100 / (1 + rs))
    # When loss=0 and gain>0, rs=inf → RSI=100; when both=0, rs=NaN → RSI=50
    return result.fillna(50.0)


def rsi_scalar(series: pd.Series, period: int) -> float:
    """Scalar RSI: latest value."""
    result = rsi(series, period)
    val = result.iloc[-1]
    return float(val) if not np.isnan(val) else 50.0


# ── Bollinger Bands ────────────────────────────────────────────────


def bollinger_bands(
    series: pd.Series, period: int, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands: (mid, upper, lower)."""
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return mid, upper, lower


# ── Volatility ─────────────────────────────────────────────────────


def realized_volatility(series: pd.Series, lookback: int) -> pd.Series:
    """Annualized realized volatility (rolling)."""
    return series.pct_change().rolling(lookback).std() * (252**0.5)


def realized_volatility_scalar(series: pd.Series, lookback: int) -> float:
    """Scalar annualized realized volatility."""
    if len(series) < lookback + 1:
        return 0.0
    return float(series.pct_change().iloc[-lookback:].std() * (252**0.5))


# ── Z-Score ────────────────────────────────────────────────────────


def zscore(series: pd.Series, lookback: int) -> pd.Series:
    """Rolling z-score."""
    mean = series.rolling(lookback).mean()
    std = series.rolling(lookback).std()
    return (series - mean) / std.replace(0, float("inf"))


def zscore_scalar(series: pd.Series, lookback: int) -> float:
    """Scalar z-score of last value vs rolling window."""
    if len(series) < lookback + 1:
        return 0.0
    window = series.iloc[-lookback:]
    mean = float(window.mean())
    std = float(window.std())
    if std < 1e-8:
        return 0.0
    return (float(series.iloc[-1]) - mean) / std


# ── Price Ratios ───────────────────────────────────────────────────


def price_to_ma_ratio(series: pd.Series, lookback: int) -> pd.Series:
    """Price-to-moving-average ratio: MA / price - 1 (value signal)."""
    return series.rolling(lookback).mean() / series - 1


def volume_ratio(volume: pd.Series, lookback: int) -> pd.Series:
    """Volume relative to rolling average."""
    return volume / volume.rolling(lookback).mean()


# ── Ichimoku ───────────────────────────────────────────────────────


def ichimoku_tenkan(high: pd.Series, low: pd.Series, period: int) -> pd.Series:
    """Ichimoku Tenkan-sen (conversion line)."""
    return (high.rolling(period).max() + low.rolling(period).min()) / 2


def ichimoku_kijun(high: pd.Series, low: pd.Series, period: int) -> pd.Series:
    """Ichimoku Kijun-sen (base line)."""
    return (high.rolling(period).max() + low.rolling(period).min()) / 2


# ── Channel ────────────────────────────────────────────────────────


def channel_upper(high: pd.Series, lookback: int) -> pd.Series:
    """Rolling channel upper bound (highest high)."""
    return high.rolling(lookback).max()


def channel_lower(low: pd.Series, lookback: int) -> pd.Series:
    """Rolling channel lower bound (lowest low)."""
    return low.rolling(lookback).min()
