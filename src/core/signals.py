"""Signal registry — single source of truth for all template signal decisions.

Each signal function takes (df: DataFrame, params: dict) and returns "long" | "flat".
The SIGNAL_REGISTRY maps every supported template slug to its signal function.

Used by:
  - src/live/signals.py (live position targeting)
  - src/screening/translator.py (generic signal builder)
  - src/validation/translator.py (NT on_bar delegation)
"""

from __future__ import annotations

import logging
from typing import Any, Callable

import numpy as np
import pandas as pd

from src.core.indicators import (
    bollinger_bands,
    ema,
    ichimoku_kijun,
    ichimoku_tenkan,
    momentum_return_scalar,
    price_to_ma_ratio,
    realized_volatility_scalar,
    rsi,
    sma,
    volume_ratio,
    zscore_scalar,
)

logger = logging.getLogger(__name__)

SignalFn = Callable[[pd.DataFrame, dict[str, Any]], str]


# ── Signal Functions (46 existing) ──────────────────────────────────


def signal_momentum_crosssectional(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback_months = params.get("lookback", 12)
    lookback_days = lookback_months * 21
    ret = momentum_return_scalar(df["Close"], lookback_days)
    return "long" if ret > 0 else "flat"


def signal_momentum_timeseries(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 252)
    threshold = params.get("threshold", 0.0)
    ret = momentum_return_scalar(df["Close"], lookback)
    return "long" if ret > threshold else "flat"


def signal_dual_momentum(df: pd.DataFrame, params: dict[str, Any]) -> str:
    abs_lookback = params.get("absolute_lookback", 252)
    ret = momentum_return_scalar(df["Close"], abs_lookback)
    return "long" if ret > 0 else "flat"


def signal_ma_crossover(df: pd.DataFrame, params: dict[str, Any]) -> str:
    fast = params.get("fast_period", 10)
    slow = params.get("slow_period", 50)
    close = df["Close"]
    if len(close) < slow + 1:
        return "flat"
    sma_fast = sma(close, fast).iloc[-1]
    sma_slow = sma(close, slow).iloc[-1]
    return "long" if sma_fast > sma_slow else "flat"


def signal_rsi_mean_reversion(df: pd.DataFrame, params: dict[str, Any]) -> str:
    period = params.get("rsi_period", 14)
    oversold = params.get("oversold", 30)
    overbought = params.get("overbought", 70)
    close = df["Close"]
    if len(close) < period + 1:
        return "flat"
    rsi_series = rsi(close, period)
    current_rsi = rsi_series.iloc[-1]
    if np.isnan(current_rsi):
        return "flat"
    if current_rsi < oversold:
        return "long"
    elif current_rsi > overbought:
        return "flat"
    return "flat"


def signal_bollinger_mean_reversion(df: pd.DataFrame, params: dict[str, Any]) -> str:
    period = params.get("bb_period", 20)
    num_std = params.get("bb_std", 2.0)
    close = df["Close"]
    if len(close) < period + 1:
        return "flat"
    _mid, upper, lower = bollinger_bands(close, period, num_std)
    price = close.iloc[-1]
    if price < lower.iloc[-1]:
        return "long"
    elif price > upper.iloc[-1]:
        return "flat"
    return "flat"


def signal_pairs_trading(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 60)
    entry_z = params.get("entry_z", 2.0)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    ratio = close / sma(close, lookback)
    zscore_series = (ratio - ratio.rolling(lookback).mean()) / ratio.rolling(lookback).std()
    z = zscore_series.iloc[-1]
    if np.isnan(z):
        return "flat"
    return "long" if z < -entry_z else "flat"


def signal_value_factor(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 252)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    value_signal = price_to_ma_ratio(close, lookback).iloc[-1]
    return "long" if value_signal > 0.1 else "flat"


def signal_breakout(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 20)
    if len(df) < lookback + 2:
        return "flat"
    upper = df["High"].rolling(lookback).max().iloc[-2]
    price = df["Close"].iloc[-1]
    return "long" if price > upper else "flat"


def signal_trend_following(df: pd.DataFrame, params: dict[str, Any]) -> str:
    fast = params.get("fast_period", 20)
    slow = params.get("slow_period", 100)
    close = df["Close"]
    if len(close) < slow + 1:
        return "flat"
    ema_fast = ema(close, fast).iloc[-1]
    ema_slow = ema(close, slow).iloc[-1]
    return "long" if ema_fast > ema_slow else "flat"


def signal_momentum_volatility(df: pd.DataFrame, params: dict[str, Any]) -> str:
    mom_lookback = params.get("mom_lookback", 126)
    close = df["Close"]
    mom = momentum_return_scalar(close, mom_lookback)
    vol = realized_volatility_scalar(close, 30)
    return "long" if mom > 0 and vol < 0.25 else "flat"


def signal_residual_momentum(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 126)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    residual = close.iloc[-1] / sma(close, lookback).iloc[-1] - 1
    return "long" if residual > 0.02 else "flat"


def signal_momentum_volume(df: pd.DataFrame, params: dict[str, Any]) -> str:
    mom_lookback = params.get("mom_lookback", 126)
    vol_ratio_threshold = params.get("vol_ratio", 1.5)
    close = df["Close"]
    vol = df["Volume"]
    mom = momentum_return_scalar(close, mom_lookback)
    if len(vol) < 21:
        return "flat"
    vr = volume_ratio(vol, 20).iloc[-1]
    return "long" if mom > 0 and vr > vol_ratio_threshold else "flat"


def signal_short_term_reversal(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 5)
    ret = momentum_return_scalar(df["Close"], lookback)
    return "long" if ret < -0.03 else "flat"


def signal_ichimoku(df: pd.DataFrame, params: dict[str, Any]) -> str:
    tenkan = params.get("tenkan", 9)
    kijun = params.get("kijun", 26)
    if len(df) < kijun + 1:
        return "flat"
    tenkan_sen = ichimoku_tenkan(df["High"], df["Low"], tenkan).iloc[-1]
    kijun_sen = ichimoku_kijun(df["High"], df["Low"], kijun).iloc[-1]
    return "long" if tenkan_sen > kijun_sen else "flat"


def signal_fama_french(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 252)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    value = price_to_ma_ratio(close, lookback).iloc[-1]
    mom = momentum_return_scalar(close, lookback)
    return "long" if value > 0.05 and mom > 0 else "flat"


def signal_low_vol(df: pd.DataFrame, params: dict[str, Any]) -> str:
    vol_lookback = params.get("vol_lookback", 30)
    vol = realized_volatility_scalar(df["Close"], vol_lookback)
    return "long" if vol < 0.20 else "flat"


def signal_earnings_quality(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 252)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    vol = realized_volatility_scalar(close, 60)
    value = price_to_ma_ratio(close, lookback).iloc[-1]
    return "long" if vol < 0.25 and value > 0.05 else "flat"


def signal_g_score(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 126)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    value = price_to_ma_ratio(close, lookback).iloc[-1]
    vol = realized_volatility_scalar(close, 30)
    short_mom = close.iloc[-1] > close.iloc[-21] if len(close) > 21 else False
    score = (1 if value > 0 else 0) + (1 if vol < 0.25 else 0) + (1 if short_mom else 0)
    return "long" if score >= 2 else "flat"


def signal_turn_of_month(df: pd.DataFrame, params: dict[str, Any]) -> str:
    if df.index.empty:
        return "flat"
    dom = df.index[-1].day
    return "long" if dom >= 27 or dom <= 3 else "flat"


def signal_january_effect(df: pd.DataFrame, params: dict[str, Any]) -> str:
    if df.index.empty:
        return "flat"
    month = df.index[-1].month
    return "long" if month == 1 else "flat"


def signal_pre_holiday(df: pd.DataFrame, params: dict[str, Any]) -> str:
    if df.index.empty:
        return "flat"
    dow = df.index[-1].dayofweek
    return "long" if dow == 4 else "flat"  # Friday


def signal_seasonality(df: pd.DataFrame, params: dict[str, Any]) -> str:
    if df.index.empty:
        return "flat"
    month = df.index[-1].month
    return "long" if month in (11, 12, 1, 2, 3, 4) else "flat"


def signal_vol_risk_premium(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 30)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    short_vol = realized_volatility_scalar(close, 10)
    long_vol = realized_volatility_scalar(close, lookback)
    return "long" if short_vol < long_vol else "flat"


def signal_vix_mean_reversion(df: pd.DataFrame, params: dict[str, Any]) -> str:
    threshold = params.get("threshold", 25)
    close = df["Close"]
    if len(close) < 21:
        return "flat"
    vix_proxy = realized_volatility_scalar(close, 20) * 100
    return "long" if vix_proxy > threshold else "flat"


def signal_leveraged_etf(df: pd.DataFrame, params: dict[str, Any]) -> str:
    lookback = params.get("lookback", 20)
    vol_target = params.get("vol_target", 0.15)
    close = df["Close"]
    vol = realized_volatility_scalar(close, lookback)
    mom = momentum_return_scalar(close, lookback)
    return "long" if vol < vol_target and mom > 0 else "flat"


def signal_forex_mr_momentum(df: pd.DataFrame, params: dict[str, Any]) -> str:
    mom_lookback = params.get("mom_lookback", 126)
    close = df["Close"]
    if len(close) < mom_lookback + 1:
        return "flat"
    mom = momentum_return_scalar(close, mom_lookback)
    mr = price_to_ma_ratio(close, 10).iloc[-1]
    return "long" if mom > 0 and mr > 0.01 else "flat"


# ── New Signal Functions (Category B — 19 templates) ────────────────


def signal_january_barometer(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """If January return > 0, hold rest of year."""
    if df.index.empty:
        return "flat"
    month = df.index[-1].month
    close = df["Close"]
    if month == 1:
        return "flat"  # Wait for January to finish
    # Check last January's return
    jan_data = close[close.index.month == 1]
    if len(jan_data) < 2:
        return "flat"
    jan_ret = jan_data.iloc[-1] / jan_data.iloc[0] - 1
    return "long" if jan_ret > 0 else "flat"


def signal_12_month_cycle(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Same-month-last-year return predictor."""
    close = df["Close"]
    if len(close) < 252 + 21:
        return "flat"
    # Return from ~12 months ago for the same calendar period
    ret_12m_ago = momentum_return_scalar(close.iloc[:-252], 21) if len(close) > 273 else 0.0
    return "long" if ret_12m_ago > 0 else "flat"


def signal_lunar_cycle(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """~30-day phase cycle proxy using day-of-month."""
    if df.index.empty:
        return "flat"
    dom = df.index[-1].day
    # Approximate: buy in first half of lunar cycle
    return "long" if dom <= 15 else "flat"


def signal_option_expiration_week(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Hold during OpEx week (days 14-20 of month)."""
    if df.index.empty:
        return "flat"
    dom = df.index[-1].day
    return "long" if 14 <= dom <= 20 else "flat"


def signal_momentum_market_filter(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Momentum + 200-day SMA regime filter."""
    lookback = params.get("lookback", 252)
    close = df["Close"]
    if len(close) < max(lookback, 200) + 1:
        return "flat"
    mom = momentum_return_scalar(close, lookback)
    above_200 = close.iloc[-1] > sma(close, 200).iloc[-1]
    return "long" if mom > 0 and above_200 else "flat"


def signal_momentum_style_rotation(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Momentum + value/growth tilt."""
    lookback = params.get("lookback", 126)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    mom = momentum_return_scalar(close, lookback)
    value = price_to_ma_ratio(close, lookback).iloc[-1]
    return "long" if mom > 0 and value > -0.05 else "flat"


def signal_momentum_short_term_reversal(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Long-term momentum + short-term dip."""
    long_lookback = params.get("lookback", 252)
    short_lookback = params.get("short_lookback", 5)
    close = df["Close"]
    if len(close) < long_lookback + 1:
        return "flat"
    long_mom = momentum_return_scalar(close, long_lookback)
    short_ret = momentum_return_scalar(close, short_lookback)
    return "long" if long_mom > 0 and short_ret < -0.02 else "flat"


def signal_improved_commodity_momentum(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Momentum + term structure proxy (short MA vs long MA)."""
    lookback = params.get("lookback", 126)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    mom = momentum_return_scalar(close, lookback)
    short_ma = sma(close, 20).iloc[-1]
    long_ma = sma(close, 60).iloc[-1]
    contango = short_ma < long_ma  # term structure positive for longs
    return "long" if mom > 0 and not contango else "flat"


def signal_intraday_etf_momentum(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Daily proxy: 1-5 day momentum."""
    lookback = params.get("lookback", 5)
    ret = momentum_return_scalar(df["Close"], lookback)
    return "long" if ret > 0.01 else "flat"


def signal_price_earnings_momentum(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Price momentum + earnings proxy (smoothed returns)."""
    lookback = params.get("lookback", 126)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    mom = momentum_return_scalar(close, lookback)
    # Earnings proxy: smoothed 3-month return
    smoothed = momentum_return_scalar(sma(close, 21), 63) if len(close) > 84 else 0.0
    return "long" if mom > 0 and smoothed > 0 else "flat"


def signal_sentiment_style_rotation(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Volume surge + momentum."""
    lookback = params.get("lookback", 126)
    close = df["Close"]
    vol = df["Volume"]
    if len(close) < lookback + 1:
        return "flat"
    mom = momentum_return_scalar(close, lookback)
    vr = volume_ratio(vol, 20).iloc[-1] if len(vol) > 20 else 1.0
    return "long" if mom > 0 and vr > 1.2 else "flat"


def signal_dynamic_pairs(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Z-score with dynamic threshold (vol-adjusted)."""
    lookback = params.get("lookback", 60)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    z = zscore_scalar(close, lookback)
    vol = realized_volatility_scalar(close, 20)
    # Higher vol → wider threshold
    threshold = 1.5 + vol * 2
    return "long" if z < -threshold else "flat"


def signal_optimal_pairs(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Z-score with wider bounds (lookback=90, entry_z=1.5)."""
    lookback = params.get("lookback", 90)
    entry_z = params.get("entry_z", 1.5)
    close = df["Close"]
    z = zscore_scalar(close, lookback)
    return "long" if z < -entry_z else "flat"


def signal_pairs_ratio_zscore(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Ratio z-score (copula-style)."""
    lookback = params.get("lookback", 60)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    ratio = close / sma(close, lookback)
    z = zscore_scalar(ratio, lookback)
    return "long" if z < -2.0 else "flat"


def signal_etf_arbitrage(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """ETF mean reversion (z-score < -1.5)."""
    lookback = params.get("lookback", 20)
    z = zscore_scalar(df["Close"], lookback)
    return "long" if z < -1.5 else "flat"


def signal_crude_oil_equity(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Momentum with higher threshold."""
    lookback = params.get("lookback", 126)
    ret = momentum_return_scalar(df["Close"], lookback)
    return "long" if ret > 0.05 else "flat"


def signal_wti_brent_spread(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Price-to-MA ratio as spread proxy."""
    lookback = params.get("lookback", 60)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    ratio = price_to_ma_ratio(close, lookback).iloc[-1]
    return "long" if ratio > 0.02 else "flat"


def signal_dynamic_breakout(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Vol-adjusted channel breakout."""
    lookback = params.get("lookback", 20)
    if len(df) < lookback + 2:
        return "flat"
    close = df["Close"]
    upper = df["High"].rolling(lookback).max().iloc[-2]
    vol = realized_volatility_scalar(close, lookback)
    # Adjust threshold: lower vol → tighter breakout needed
    threshold = upper * (1 - vol * 0.1)
    return "long" if close.iloc[-1] > threshold else "flat"


def signal_capm_alpha(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Momentum proxy: ret > 5%."""
    lookback = params.get("lookback", 126)
    ret = momentum_return_scalar(df["Close"], lookback)
    return "long" if ret > 0.05 else "flat"


def signal_idiosyncratic_skewness(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Low skewness factor — prefer low skew."""
    lookback = params.get("lookback", 60)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    returns = close.pct_change().dropna().iloc[-lookback:]
    if len(returns) < 20:
        return "flat"
    skew = float(returns.skew())
    return "long" if skew < 0.5 else "flat"


def signal_asset_growth(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Low growth + low vol proxy."""
    lookback = params.get("lookback", 252)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    growth = momentum_return_scalar(close, lookback)
    vol = realized_volatility_scalar(close, 60)
    return "long" if growth < 0.20 and vol < 0.25 else "flat"


def signal_roa_effect(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Low volatility proxy for ROA."""
    vol_lookback = params.get("vol_lookback", 60)
    vol = realized_volatility_scalar(df["Close"], vol_lookback)
    return "long" if vol < 0.20 else "flat"


def signal_unexpected_earnings(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Recent outperformance proxy for SUE."""
    lookback = params.get("lookback", 21)
    close = df["Close"]
    ret = momentum_return_scalar(close, lookback)
    return "long" if ret > 0.03 else "flat"


def signal_multi_factor_composite(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Multi-factor composite: value + momentum + low vol."""
    lookback = params.get("lookback", 126)
    close = df["Close"]
    if len(close) < lookback + 1:
        return "flat"
    value = price_to_ma_ratio(close, lookback).iloc[-1]
    mom = momentum_return_scalar(close, lookback)
    vol = realized_volatility_scalar(close, 30)
    score = (1 if value > 0 else 0) + (1 if mom > 0 else 0) + (1 if vol < 0.25 else 0)
    return "long" if score >= 2 else "flat"


def signal_vix_term_structure(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Short-term vol < long-term vol."""
    close = df["Close"]
    if len(close) < 61:
        return "flat"
    short_vol = realized_volatility_scalar(close, 10)
    long_vol = realized_volatility_scalar(close, 60)
    return "long" if short_vol < long_vol else "flat"


def signal_forex_risk_premia(df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Carry-like: positive trend + moderate vol."""
    lookback = params.get("lookback", 63)
    close = df["Close"]
    ret = momentum_return_scalar(close, lookback)
    vol = realized_volatility_scalar(close, 20)
    return "long" if ret > 0 and vol < 0.15 else "flat"


# ── Public API ──────────────────────────────────────────────────────


def compute_signal(template_slug: str, df: pd.DataFrame, params: dict[str, Any]) -> str:
    """Compute signal for a given template slug.

    Args:
        template_slug: Template name (without category prefix).
        df: OHLCV DataFrame with DatetimeIndex.
        params: Strategy parameters dict.

    Returns:
        "long" or "flat".
    """
    fn = SIGNAL_REGISTRY.get(template_slug, signal_momentum_timeseries)
    try:
        return fn(df, params)
    except Exception as e:
        logger.error("Signal computation failed for %s: %s", template_slug, e)
        return "flat"


# ── Signal Registry ─────────────────────────────────────────────────


SIGNAL_REGISTRY: dict[str, SignalFn] = {
    # ── Momentum (10 existing) ────────────────────────────────
    "momentum-effect-in-stocks": signal_momentum_crosssectional,
    "time-series-momentum": signal_momentum_timeseries,
    "time-series-momentum-effect": signal_momentum_timeseries,
    "dual-momentum": signal_dual_momentum,
    "sector-momentum": signal_momentum_timeseries,
    "asset-class-momentum": signal_momentum_timeseries,
    "asset-class-trend-following": signal_trend_following,
    "momentum-and-reversal-combined-with-volatility-effect-in-stocks": signal_momentum_volatility,
    "residual-momentum": signal_residual_momentum,
    "combining-momentum-effect-with-volume": signal_momentum_volume,
    # ── Mean Reversion (7 existing) ───────────────────────────
    "mean-reversion-rsi": signal_rsi_mean_reversion,
    "mean-reversion-bollinger": signal_bollinger_mean_reversion,
    "pairs-trading": signal_pairs_trading,
    "short-term-reversal": signal_short_term_reversal,
    "short-term-reversal-strategy-in-stocks": signal_short_term_reversal,
    "mean-reversion-statistical-arbitrage-in-stocks": signal_pairs_trading,
    "pairs-trading-with-stocks": signal_pairs_trading,
    # ── Technical (6 existing) ────────────────────────────────
    "moving-average-crossover": signal_ma_crossover,
    "breakout": signal_breakout,
    "trend-following": signal_trend_following,
    "ichimoku-clouds-in-energy-sector": signal_ichimoku,
    "dual-thrust-trading-algorithm": signal_breakout,
    "paired-switching": signal_momentum_timeseries,
    # ── Factor Investing (5 existing) ─────────────────────────
    "fama-french-five-factors": signal_fama_french,
    "beta-factors-in-stocks": signal_low_vol,
    "liquidity-effect-in-stocks": signal_momentum_timeseries,
    "accrual-anomaly": signal_value_factor,
    "earnings-quality-factor": signal_earnings_quality,
    # ── Value & Fundamental (5 existing) ──────────────────────
    "value-factor": signal_value_factor,
    "price-earnings-anomaly": signal_value_factor,
    "book-to-market-value-anomaly": signal_value_factor,
    "small-capitalization-stocks-premium-anomaly": signal_momentum_timeseries,
    "g-score-investing": signal_g_score,
    # ── Calendar Anomalies (5 existing) ───────────────────────
    "turn-of-the-month-in-equity-indexes": signal_turn_of_month,
    "january-effect-in-stocks": signal_january_effect,
    "pre-holiday-effect": signal_pre_holiday,
    "overnight-anomaly": signal_momentum_timeseries,
    "seasonality-effect-same-calendar-month": signal_seasonality,
    # ── Volatility (4 existing) ───────────────────────────────
    "volatility-effect-in-stocks": signal_low_vol,
    "volatility-risk-premium-effect": signal_vol_risk_premium,
    "vix-predicts-stock-index-returns": signal_vix_mean_reversion,
    "leveraged-etfs-with-systematic-risk-management": signal_leveraged_etf,
    # ── Forex (2 existing) ────────────────────────────────────
    "forex-carry-trade": signal_momentum_timeseries,
    "combining-mean-reversion-and-momentum-in-forex": signal_forex_mr_momentum,
    # ── Commodities (2 existing) ──────────────────────────────
    "term-structure-effect-in-commodities": signal_ma_crossover,
    "gold-market-timing": signal_momentum_timeseries,
    # ── Category A: Reuse existing (13 new) ───────────────────
    "momentum-effect-in-country-equity-indexes": signal_momentum_crosssectional,
    "momentum-effect-in-reits": signal_momentum_crosssectional,
    "momentum-effect-in-stocks-in-small-portfolios": signal_momentum_crosssectional,
    "momentum-in-mutual-fund-returns": signal_momentum_crosssectional,
    "momentum-effect-in-commodities-futures": signal_momentum_timeseries,
    "commodities-futures-trend-following": signal_trend_following,
    "forex-momentum": signal_momentum_timeseries,
    "momentum-strategy-low-frequency-forex": signal_momentum_timeseries,
    "mean-reversion-effect-in-country-equity-indexes": signal_bollinger_mean_reversion,
    "pairs-trading-with-country-etfs": signal_pairs_trading,
    "short-term-reversal-with-futures": signal_short_term_reversal,
    "beta-factor-in-country-equity-indexes": signal_low_vol,
    "value-effect-within-countries": signal_value_factor,
    # ── Category B: New signals (19 new) ──────────────────────
    # Calendar (4)
    "january-barometer": signal_january_barometer,
    "12-month-cycle-cross-section": signal_12_month_cycle,
    "lunar-cycle-in-equity-market": signal_lunar_cycle,
    "option-expiration-week-effect": signal_option_expiration_week,
    # Momentum variants (8)
    "momentum-and-state-of-market-filters": signal_momentum_market_filter,
    "momentum-and-style-rotation-effect": signal_momentum_style_rotation,
    "momentum-short-term-reversal-strategy": signal_momentum_short_term_reversal,
    "improved-momentum-strategy-on-commodities-futures": signal_improved_commodity_momentum,
    "momentum-effect-combined-with-term-structure-in-commodities": (
        signal_improved_commodity_momentum
    ),
    "intraday-etf-momentum": signal_intraday_etf_momentum,
    "price-and-earnings-momentum": signal_price_earnings_momentum,
    "sentiment-and-style-rotation-effect-in-stocks": signal_sentiment_style_rotation,
    # Pairs/Mean-Reversion (4)
    "intraday-dynamic-pairs-trading": signal_dynamic_pairs,
    "optimal-pairs-trading": signal_optimal_pairs,
    "pairs-trading-copula-vs-cointegration": signal_pairs_ratio_zscore,
    "intraday-arbitrage-between-index-etfs": signal_etf_arbitrage,
    # Cross-Asset/Spread (2)
    "can-crude-oil-predict-equity-returns": signal_crude_oil_equity,
    "trading-with-wti-brent-spread": signal_wti_brent_spread,
    # Technical (1)
    "dynamic-breakout-ii-strategy": signal_dynamic_breakout,
    # Factor/Fundamental (6)
    "capm-alpha-ranking-dow-30": signal_capm_alpha,
    "expected-idiosyncratic-skewness": signal_idiosyncratic_skewness,
    "asset-growth-effect": signal_asset_growth,
    "roa-effect-within-stocks": signal_roa_effect,
    "standardized-unexpected-earnings": signal_unexpected_earnings,
    "fundamental-factor-long-short-strategy": signal_multi_factor_composite,
    "stock-selection-based-on-fundamental-factors": signal_multi_factor_composite,
    # Volatility (1)
    "exploiting-term-structure-of-vix-futures": signal_vix_term_structure,
    # Forex (1)
    "risk-premia-in-forex-markets": signal_forex_risk_premia,
}
