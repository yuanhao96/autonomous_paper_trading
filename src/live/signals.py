"""Signal engine — compute target positions from StrategySpec + current prices.

Extracts the signal logic from the screening translator's strategy templates
and applies it to current market data to determine target portfolio weights.
Each symbol gets a signal: "long" (hold), or "flat" (no position).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from src.strategies.spec import StrategySpec

logger = logging.getLogger(__name__)


def compute_signals(
    spec: StrategySpec,
    prices: dict[str, pd.DataFrame],
    lookback_bars: int = 300,
) -> dict[str, str]:
    """Compute current signal for each symbol.

    Args:
        spec: Strategy specification (template + parameters).
        prices: {symbol: OHLCV DataFrame} with DatetimeIndex, columns [Open,High,Low,Close,Volume].
        lookback_bars: Minimum bars of history needed.

    Returns:
        {symbol: "long" | "flat"} for each symbol.
    """
    template = spec.template.split("/")[-1] if "/" in spec.template else spec.template
    params = spec.parameters

    signal_fn = _SIGNAL_MAP.get(template, _signal_momentum_timeseries)

    signals: dict[str, str] = {}
    for symbol, df in prices.items():
        if len(df) < lookback_bars:
            logger.warning("Insufficient data for %s: %d bars (need %d)", symbol, len(df), lookback_bars)
            signals[symbol] = "flat"
            continue
        try:
            signals[symbol] = signal_fn(df, params)
        except Exception as e:
            logger.error("Signal computation failed for %s: %s", symbol, e)
            signals[symbol] = "flat"

    return signals


def compute_target_weights(
    spec: StrategySpec,
    signals: dict[str, str],
) -> dict[str, float]:
    """Convert signals to target portfolio weights.

    Args:
        spec: Strategy specification (for position sizing).
        signals: {symbol: "long" | "flat"} from compute_signals().

    Returns:
        {symbol: weight} where weight is 0.0 (flat) or position fraction.
    """
    long_symbols = [s for s, sig in signals.items() if sig == "long"]

    if not long_symbols:
        return {s: 0.0 for s in signals}

    method = spec.risk.position_size_method
    max_pos = spec.risk.max_position_pct
    max_positions = spec.risk.max_positions

    # Limit number of positions
    if len(long_symbols) > max_positions:
        long_symbols = long_symbols[:max_positions]

    weights: dict[str, float] = {}

    if method == "equal_weight":
        weight = min(max_pos, 1.0 / len(long_symbols))
        for s in signals:
            weights[s] = weight if s in long_symbols else 0.0
    else:
        # Default to equal weight for other methods
        weight = min(max_pos, 1.0 / len(long_symbols))
        for s in signals:
            weights[s] = weight if s in long_symbols else 0.0

    return weights


# ── Signal functions per template ──────────────────────────────────


def _signal_momentum_crosssectional(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback_months = params.get("lookback", 12)
    lookback_days = lookback_months * 21
    close = df["Close"]
    if len(close) < lookback_days + 1:
        return "flat"
    momentum = close.iloc[-1] / close.iloc[-lookback_days - 1] - 1
    return "long" if momentum > 0 else "flat"


def _signal_momentum_timeseries(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 252)
    threshold = params.get("threshold", 0.0)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    ret = close.iloc[-1] / close.iloc[-lookback - 1] - 1
    return "long" if ret > threshold else "flat"


def _signal_dual_momentum(df: pd.DataFrame, params: dict[str, Any]) -> str:
    abs_lookback = params.get("absolute_lookback", 252)
    close = df["Close"]
    if len(close) < abs_lookback + 1:
        return "flat"
    abs_ret = close.iloc[-1] / close.iloc[-abs_lookback - 1] - 1
    return "long" if abs_ret > 0 else "flat"


def _signal_ma_crossover(df: pd.DataFrame, params: dict[str, Any]) -> str:
    fast = params.get("fast_period", 10)
    slow = params.get("slow_period", 50)
    close = df["Close"]
    if len(close) < slow + 1:
        return "flat"
    sma_fast = close.rolling(fast).mean().iloc[-1]
    sma_slow = close.rolling(slow).mean().iloc[-1]
    return "long" if sma_fast > sma_slow else "flat"


def _signal_rsi_mean_reversion(df: pd.DataFrame, params: dict[str, Any]) -> str:
    period = params.get("rsi_period", 14)
    oversold = params.get("oversold", 30)
    overbought = params.get("overbought", 70)
    close = df["Close"]
    if len(close) < period + 1:
        return "flat"
    rsi = _calc_rsi(close, period)
    current_rsi = rsi.iloc[-1]
    if np.isnan(current_rsi):
        return "flat"
    # For mean reversion: buy when oversold, flat when overbought
    # If currently in "long" territory (RSI was recently oversold and hasn't reached overbought)
    # Simplified: check if RSI is below midpoint (still recovering from oversold)
    if current_rsi < oversold:
        return "long"
    elif current_rsi > overbought:
        return "flat"
    # In the middle — maintain current signal (default to flat for new entry)
    return "flat"


def _signal_bollinger_mean_reversion(df: pd.DataFrame, params: dict[str, Any]) -> str:
    period = params.get("bb_period", 20)
    num_std = params.get("bb_std", 2.0)
    close = df["Close"]
    if len(close) < period + 1:
        return "flat"
    sma = close.rolling(period).mean().iloc[-1]
    std = close.rolling(period).std().iloc[-1]
    lower = sma - num_std * std
    upper = sma + num_std * std
    price = close.iloc[-1]
    if price < lower:
        return "long"
    elif price > upper:
        return "flat"
    return "flat"


def _signal_pairs_trading(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 60)
    entry_z = params.get("entry_z", 2.0)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    ratio = close / close.rolling(lookback).mean()
    zscore_series = (ratio - ratio.rolling(lookback).mean()) / ratio.rolling(lookback).std()
    zscore = zscore_series.iloc[-1]
    if np.isnan(zscore):
        return "flat"
    return "long" if zscore < -entry_z else "flat"


def _signal_value_factor(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 252)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    value_signal = close.rolling(lookback).mean().iloc[-1] / close.iloc[-1] - 1
    return "long" if value_signal > 0.1 else "flat"


def _signal_breakout(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 20)
    if len(df) < lookback + 2:
        return "flat"
    upper = df["High"].rolling(lookback).max().iloc[-2]  # Previous bar's channel high
    price = df["Close"].iloc[-1]
    return "long" if price > upper else "flat"


def _signal_trend_following(df: pd.DataFrame, params: dict[str, Any]) -> str:
    fast = params.get("fast_period", 20)
    slow = params.get("slow_period", 100)
    close = df["Close"]
    if len(close) < slow + 1:
        return "flat"
    ema_fast = close.ewm(span=fast).mean().iloc[-1]
    ema_slow = close.ewm(span=slow).mean().iloc[-1]
    return "long" if ema_fast > ema_slow else "flat"


# ── New signal functions ──────────────────────────────────────────────


def _signal_momentum_volatility(df: pd.DataFrame, params: dict[str, Any]) -> str:
    mom_lookback = params.get("mom_lookback", 126)
    vol_lookback = params.get("vol_lookback", 30)
    close = df["Close"]
    if len(close) < mom_lookback + 1:
        return "flat"
    mom = close.iloc[-1] / close.iloc[-mom_lookback - 1] - 1
    vol = close.pct_change().iloc[-vol_lookback:].std() * (252 ** 0.5)
    return "long" if mom > 0 and vol < 0.25 else "flat"


def _signal_residual_momentum(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 126)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    residual = close.iloc[-1] / close.rolling(lookback).mean().iloc[-1] - 1
    return "long" if residual > 0.02 else "flat"


def _signal_momentum_volume(df: pd.DataFrame, params: dict[str, Any]) -> str:
    mom_lookback = params.get("mom_lookback", 126)
    vol_ratio = params.get("vol_ratio", 1.5)
    close = df["Close"]
    volume = df["Volume"]
    if len(close) < mom_lookback + 1:
        return "flat"
    mom = close.iloc[-1] / close.iloc[-mom_lookback - 1] - 1
    avg_vol = volume.rolling(20).mean().iloc[-1]
    current_vol = volume.iloc[-1]
    return "long" if mom > 0 and current_vol > avg_vol * vol_ratio else "flat"


def _signal_short_term_reversal(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 5)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    ret = close.iloc[-1] / close.iloc[-lookback - 1] - 1
    return "long" if ret < -0.03 else "flat"


def _signal_ichimoku(df: pd.DataFrame, params: dict[str, Any]) -> str:
    tenkan = params.get("tenkan", 9)
    kijun = params.get("kijun", 26)
    if len(df) < kijun + 1:
        return "flat"
    high, low = df["High"], df["Low"]
    tenkan_sen = (high.rolling(tenkan).max().iloc[-1] + low.rolling(tenkan).min().iloc[-1]) / 2
    kijun_sen = (high.rolling(kijun).max().iloc[-1] + low.rolling(kijun).min().iloc[-1]) / 2
    return "long" if tenkan_sen > kijun_sen else "flat"


def _signal_fama_french(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 252)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    value = close.rolling(lookback).mean().iloc[-1] / close.iloc[-1] - 1
    mom = close.iloc[-1] / close.iloc[-lookback - 1] - 1
    return "long" if value > 0.05 and mom > 0 else "flat"


def _signal_low_vol(df: pd.DataFrame, params: dict[str, Any]) -> str:
    vol_lookback = params.get("vol_lookback", 30)
    close = df["Close"]
    if len(close) < vol_lookback + 1:
        return "flat"
    vol = close.pct_change().iloc[-vol_lookback:].std() * (252 ** 0.5)
    return "long" if vol < 0.20 else "flat"


def _signal_earnings_quality(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 252)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    vol = close.pct_change().iloc[-60:].std() * (252 ** 0.5)
    value = close.rolling(lookback).mean().iloc[-1] / close.iloc[-1] - 1
    return "long" if vol < 0.25 and value > 0.05 else "flat"


def _signal_g_score(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 126)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    value = close.rolling(lookback).mean().iloc[-1] / close.iloc[-1] - 1
    vol = close.pct_change().iloc[-30:].std() * (252 ** 0.5)
    short_mom = close.iloc[-1] > close.iloc[-21] if len(close) > 21 else False
    score = (1 if value > 0 else 0) + (1 if vol < 0.25 else 0) + (1 if short_mom else 0)
    return "long" if score >= 2 else "flat"


def _signal_turn_of_month(df: pd.DataFrame, params: dict[str, Any]) -> str:
    if df.index.empty:
        return "flat"
    dom = df.index[-1].day
    return "long" if dom >= 27 or dom <= 3 else "flat"


def _signal_january_effect(df: pd.DataFrame, params: dict[str, Any]) -> str:
    if df.index.empty:
        return "flat"
    month = df.index[-1].month
    return "long" if month == 1 else "flat"


def _signal_pre_holiday(df: pd.DataFrame, params: dict[str, Any]) -> str:
    if df.index.empty:
        return "flat"
    dow = df.index[-1].dayofweek
    return "long" if dow == 4 else "flat"  # Friday


def _signal_seasonality(df: pd.DataFrame, params: dict[str, Any]) -> str:
    if df.index.empty:
        return "flat"
    month = df.index[-1].month
    return "long" if month in (11, 12, 1, 2, 3, 4) else "flat"


def _signal_vol_risk_premium(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 30)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    short_vol = close.pct_change().iloc[-10:].std() * (252 ** 0.5)
    long_vol = close.pct_change().iloc[-lookback:].std() * (252 ** 0.5)
    return "long" if short_vol < long_vol else "flat"


def _signal_vix_mean_reversion(df: pd.DataFrame, params: dict[str, Any]) -> str:
    threshold = params.get("threshold", 25)
    close = df["Close"]
    if len(close) < 21:
        return "flat"
    vix_proxy = close.pct_change().iloc[-20:].std() * (252 ** 0.5) * 100
    return "long" if vix_proxy > threshold else "flat"


def _signal_leveraged_etf(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 20)
    vol_target = params.get("vol_target", 0.15)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    vol = close.pct_change().iloc[-lookback:].std() * (252 ** 0.5)
    mom = close.iloc[-1] / close.iloc[-lookback - 1] - 1
    return "long" if vol < vol_target and mom > 0 else "flat"


def _signal_forex_mr_momentum(df: pd.DataFrame, params: dict[str, Any]) -> str:
    mom_lookback = params.get("mom_lookback", 126)
    mr_lookback = params.get("mr_lookback", 10)
    close = df["Close"]
    if len(close) < mom_lookback + 1:
        return "flat"
    mom = close.iloc[-1] / close.iloc[-mom_lookback - 1] - 1
    mr = close.rolling(mr_lookback).mean().iloc[-1] / close.iloc[-1] - 1
    return "long" if mom > 0 and mr > 0.01 else "flat"


# ── Helpers ──────────────────────────────────────────────────────────


def _calc_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("inf"))
    return 100 - (100 / (1 + rs))


# ── Signal function registry ────────────────────────────────────────

_SIGNAL_MAP = {
    # ── Momentum ──────────────────────────────────────────────
    "momentum-effect-in-stocks": _signal_momentum_crosssectional,
    "time-series-momentum": _signal_momentum_timeseries,
    "time-series-momentum-effect": _signal_momentum_timeseries,
    "dual-momentum": _signal_dual_momentum,
    "sector-momentum": _signal_momentum_timeseries,
    "asset-class-momentum": _signal_momentum_timeseries,
    "asset-class-trend-following": _signal_trend_following,
    "momentum-and-reversal-combined-with-volatility-effect-in-stocks": _signal_momentum_volatility,
    "residual-momentum": _signal_residual_momentum,
    "combining-momentum-effect-with-volume": _signal_momentum_volume,
    # ── Mean Reversion ────────────────────────────────────────
    "mean-reversion-rsi": _signal_rsi_mean_reversion,
    "mean-reversion-bollinger": _signal_bollinger_mean_reversion,
    "pairs-trading": _signal_pairs_trading,
    "short-term-reversal": _signal_short_term_reversal,
    "short-term-reversal-strategy-in-stocks": _signal_short_term_reversal,
    "mean-reversion-statistical-arbitrage-in-stocks": _signal_pairs_trading,
    "pairs-trading-with-stocks": _signal_pairs_trading,
    # ── Technical ─────────────────────────────────────────────
    "moving-average-crossover": _signal_ma_crossover,
    "breakout": _signal_breakout,
    "trend-following": _signal_trend_following,
    "ichimoku-clouds-in-energy-sector": _signal_ichimoku,
    "dual-thrust-trading-algorithm": _signal_breakout,
    "paired-switching": _signal_momentum_timeseries,
    # ── Factor Investing ──────────────────────────────────────
    "fama-french-five-factors": _signal_fama_french,
    "beta-factors-in-stocks": _signal_low_vol,
    "liquidity-effect-in-stocks": _signal_momentum_timeseries,
    "accrual-anomaly": _signal_value_factor,
    "earnings-quality-factor": _signal_earnings_quality,
    # ── Value & Fundamental ───────────────────────────────────
    "value-factor": _signal_value_factor,
    "price-earnings-anomaly": _signal_value_factor,
    "book-to-market-value-anomaly": _signal_value_factor,
    "small-capitalization-stocks-premium-anomaly": _signal_momentum_timeseries,
    "g-score-investing": _signal_g_score,
    # ── Calendar Anomalies ────────────────────────────────────
    "turn-of-the-month-in-equity-indexes": _signal_turn_of_month,
    "january-effect-in-stocks": _signal_january_effect,
    "pre-holiday-effect": _signal_pre_holiday,
    "overnight-anomaly": _signal_momentum_timeseries,
    "seasonality-effect-same-calendar-month": _signal_seasonality,
    # ── Volatility ────────────────────────────────────────────
    "volatility-effect-in-stocks": _signal_low_vol,
    "volatility-risk-premium-effect": _signal_vol_risk_premium,
    "vix-predicts-stock-index-returns": _signal_vix_mean_reversion,
    "leveraged-etfs-with-systematic-risk-management": _signal_leveraged_etf,
    # ── Forex ─────────────────────────────────────────────────
    "forex-carry-trade": _signal_momentum_timeseries,
    "combining-mean-reversion-and-momentum-in-forex": _signal_forex_mr_momentum,
    # ── Commodities ───────────────────────────────────────────
    "term-structure-effect-in-commodities": _signal_ma_crossover,
    "gold-market-timing": _signal_momentum_timeseries,
}
