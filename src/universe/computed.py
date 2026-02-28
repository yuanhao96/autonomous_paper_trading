"""Computed universe builders — Level 3 universe selection.

Implements statistical and quantitative methods for dynamic equity screening:
  - momentum_screen: Rank by trailing return, pick top N
  - volume_screen: Filter by average daily trading volume
  - sector_rotation: Pick top-performing sector ETFs
  - cointegration_pairs: Find cointegrated pairs (Engle-Granger)
  - mean_reversion_screen: Stocks with high mean-reversion tendency (ADF)
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from src.data.manager import DataManager

logger = logging.getLogger(__name__)


# ── Registry of computed universe builders ───────────────────────────

_COMPUTED_BUILDERS: dict[str, "type"] = {}


def register_builder(name: str):
    """Decorator to register a computed universe builder."""
    def wrapper(func):
        _COMPUTED_BUILDERS[name] = func
        return func
    return wrapper


def get_available_computations() -> list[str]:
    """Return names of available computed universe builders."""
    return list(_COMPUTED_BUILDERS.keys())


def compute_universe(
    name: str,
    base_symbols: list[str],
    data_manager: DataManager,
    params: dict[str, Any] | None = None,
) -> list[str]:
    """Run a computed universe builder.

    Args:
        name: Builder name (e.g., "momentum_screen").
        base_symbols: Starting pool of symbols.
        data_manager: DataManager for fetching price data.
        params: Builder-specific parameters.

    Returns:
        Filtered/ranked list of symbols.
    """
    if name not in _COMPUTED_BUILDERS:
        available = ", ".join(_COMPUTED_BUILDERS.keys())
        raise ValueError(f"Unknown computation: {name}. Available: {available}")

    params = params or {}
    builder = _COMPUTED_BUILDERS[name]
    return builder(base_symbols, data_manager, params)


# ── Builder implementations ──────────────────────────────────────────


@register_builder("momentum_screen")
def _momentum_screen(
    symbols: list[str],
    dm: DataManager,
    params: dict[str, Any],
) -> list[str]:
    """Rank symbols by trailing momentum, return top N.

    Params:
        lookback_days: Period for momentum calculation (default 126 = ~6 months).
        top_n: Number of top symbols to return (default 10).
        min_bars: Minimum data bars required (default 200).
    """
    lookback = params.get("lookback_days", 126)
    top_n = params.get("top_n", 10)
    min_bars = params.get("min_bars", 200)

    momentum_scores: dict[str, float] = {}

    for symbol in symbols:
        try:
            df = dm.get_ohlcv(symbol, period="2y")
            if df is None or len(df) < min_bars:
                continue
            close = df["Close"]
            if len(close) < lookback:
                continue
            ret = (close.iloc[-1] / close.iloc[-lookback]) - 1
            momentum_scores[symbol] = ret
        except Exception as e:
            logger.debug("Momentum screen skipping %s: %s", symbol, e)
            continue

    if not momentum_scores:
        return []

    ranked = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
    return [s for s, _ in ranked[:top_n]]


@register_builder("volume_screen")
def _volume_screen(
    symbols: list[str],
    dm: DataManager,
    params: dict[str, Any],
) -> list[str]:
    """Filter symbols by average daily trading volume.

    Params:
        min_adv: Minimum average daily volume in shares (default 1_000_000).
        period_days: Period for ADV calculation (default 20).
        min_bars: Minimum data bars required (default 50).
    """
    min_adv = params.get("min_adv", 1_000_000)
    period_days = params.get("period_days", 20)
    min_bars = params.get("min_bars", 50)

    result: list[str] = []

    for symbol in symbols:
        try:
            df = dm.get_ohlcv(symbol, period="1y")
            if df is None or len(df) < min_bars:
                continue
            avg_vol = df["Volume"].iloc[-period_days:].mean()
            if avg_vol >= min_adv:
                result.append(symbol)
        except Exception as e:
            logger.debug("Volume screen skipping %s: %s", symbol, e)
            continue

    return result


@register_builder("sector_rotation")
def _sector_rotation(
    symbols: list[str],
    dm: DataManager,
    params: dict[str, Any],
) -> list[str]:
    """Pick top-performing sectors by recent momentum.

    Params:
        lookback_days: Momentum period (default 63 = ~3 months).
        top_n: Number of sectors to pick (default 3).
    """
    lookback = params.get("lookback_days", 63)
    top_n = params.get("top_n", 3)

    sector_scores: dict[str, float] = {}

    for symbol in symbols:
        try:
            df = dm.get_ohlcv(symbol, period="1y")
            if df is None or len(df) < lookback + 10:
                continue
            close = df["Close"]
            ret = (close.iloc[-1] / close.iloc[-lookback]) - 1
            sector_scores[symbol] = ret
        except Exception as e:
            logger.debug("Sector rotation skipping %s: %s", symbol, e)
            continue

    if not sector_scores:
        return []

    ranked = sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)
    return [s for s, _ in ranked[:top_n]]


@register_builder("cointegration_pairs")
def _cointegration_pairs(
    symbols: list[str],
    dm: DataManager,
    params: dict[str, Any],
) -> list[str]:
    """Find cointegrated pairs using the Engle-Granger test (simplified).

    Returns symbols that participate in at least one cointegrated pair.
    The returned list contains alternating pairs: [A, B, C, D, ...]
    where (A,B) and (C,D) are cointegrated pairs.

    Params:
        lookback_days: Data period for cointegration test (default 252).
        p_threshold: ADF p-value threshold (default 0.05).
            Also accepts ``p_value_threshold`` (architecture doc convention).
        max_pairs: Maximum pairs to return (default 5).
        min_bars: Minimum data bars (default 200).
    """
    lookback = params.get("lookback_days", 252)
    # Accept both p_threshold and p_value_threshold (architecture doc alias)
    p_threshold = params.get("p_threshold", params.get("p_value_threshold", 0.05))
    max_pairs = params.get("max_pairs", 5)
    min_bars = params.get("min_bars", 200)

    # Collect price series
    price_data: dict[str, pd.Series] = {}
    for symbol in symbols:
        try:
            df = dm.get_ohlcv(symbol, period="2y")
            if df is not None and len(df) >= min_bars:
                price_data[symbol] = df["Close"].iloc[-lookback:]
        except Exception:
            continue

    if len(price_data) < 2:
        return []

    # Align all series to common dates
    price_df = pd.DataFrame(price_data).dropna()
    if len(price_df) < min_bars // 2:
        return []

    syms = list(price_df.columns)
    pairs: list[tuple[str, str, float]] = []

    for i in range(len(syms)):
        for j in range(i + 1, len(syms)):
            try:
                p_val = _engle_granger_pvalue(
                    price_df[syms[i]].values,
                    price_df[syms[j]].values,
                )
                if p_val < p_threshold:
                    pairs.append((syms[i], syms[j], p_val))
            except Exception:
                continue

    if not pairs:
        return []

    pairs.sort(key=lambda x: x[2])  # Sort by p-value ascending
    result: list[str] = []
    for a, b, _ in pairs[:max_pairs]:
        if a not in result:
            result.append(a)
        if b not in result:
            result.append(b)

    return result


@register_builder("mean_reversion_screen")
def _mean_reversion_screen(
    symbols: list[str],
    dm: DataManager,
    params: dict[str, Any],
) -> list[str]:
    """Find symbols with strong mean-reversion tendency via ADF test.

    Params:
        lookback_days: Period for ADF test (default 252).
        p_threshold: ADF p-value threshold for stationarity (default 0.05).
            Also accepts ``p_value_threshold`` (architecture doc convention).
        top_n: Number of symbols to return (default 10).
        min_bars: Minimum data bars (default 200).
    """
    lookback = params.get("lookback_days", 252)
    p_threshold = params.get("p_threshold", params.get("p_value_threshold", 0.05))
    top_n = params.get("top_n", 10)
    min_bars = params.get("min_bars", 200)

    scores: dict[str, float] = {}

    for symbol in symbols:
        try:
            df = dm.get_ohlcv(symbol, period="2y")
            if df is None or len(df) < min_bars:
                continue
            close = df["Close"].iloc[-lookback:]
            # Test log-price stationarity (mean-reversion)
            log_prices = np.log(close.values)
            adf_stat, p_val = _simple_adf(log_prices)
            if p_val < p_threshold:
                scores[symbol] = -p_val  # Lower p-value = stronger mean reversion
        except Exception as e:
            logger.debug("Mean reversion screen skipping %s: %s", symbol, e)
            continue

    if not scores:
        return []

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [s for s, _ in ranked[:top_n]]


# ── Statistical helpers ──────────────────────────────────────────────


def _engle_granger_pvalue(y: np.ndarray, x: np.ndarray) -> float:
    """Simplified Engle-Granger cointegration test.

    Runs OLS regression y ~ x, then tests residuals for stationarity via ADF.
    Returns the ADF p-value of the residuals.
    """
    # OLS: y = alpha + beta * x + residuals
    x_with_const = np.column_stack([np.ones(len(x)), x])
    try:
        beta, _, _, _ = np.linalg.lstsq(x_with_const, y, rcond=None)
    except np.linalg.LinAlgError:
        return 1.0

    residuals = y - x_with_const @ beta
    _, p_val = _simple_adf(residuals)
    return p_val


def _simple_adf(series: np.ndarray) -> tuple[float, float]:
    """Simplified Augmented Dickey-Fuller test.

    Tests H0: unit root (non-stationary) vs H1: stationary.
    Returns (adf_statistic, approximate p-value).

    Uses a first-difference regression: dy(t) = alpha + gamma*y(t-1) + e(t)
    with MacKinnon approximate critical values for p-value.
    """
    n = len(series)
    if n < 20:
        return 0.0, 1.0

    dy = np.diff(series)
    y_lag = series[:-1]

    # Regression: dy = alpha + gamma * y_lag
    x_mat = np.column_stack([np.ones(len(y_lag)), y_lag])
    try:
        coeffs, residuals_arr, _, _ = np.linalg.lstsq(x_mat, dy, rcond=None)
    except np.linalg.LinAlgError:
        return 0.0, 1.0

    gamma = coeffs[1]

    # Standard error of gamma
    fitted = x_mat @ coeffs
    resid = dy - fitted
    sigma2 = np.sum(resid ** 2) / max(n - 3, 1)
    try:
        cov = sigma2 * np.linalg.inv(x_mat.T @ x_mat)
        se_gamma = np.sqrt(max(cov[1, 1], 1e-12))
    except np.linalg.LinAlgError:
        return 0.0, 1.0

    adf_stat = gamma / se_gamma

    # Approximate p-value using MacKinnon critical values (constant, no trend)
    # Critical values for n=inf: 1%: -3.43, 5%: -2.86, 10%: -2.57
    if adf_stat < -3.43:
        p_val = 0.005
    elif adf_stat < -2.86:
        p_val = 0.03
    elif adf_stat < -2.57:
        p_val = 0.07
    elif adf_stat < -1.94:
        p_val = 0.15
    elif adf_stat < -1.62:
        p_val = 0.30
    else:
        p_val = 0.50 + min(0.49, max(0, (adf_stat + 1.62) * 0.10))

    return adf_stat, p_val
