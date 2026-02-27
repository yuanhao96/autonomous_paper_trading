"""Market regime detection — classifies historical periods by regime type.

Regimes:
  - bull: sustained uptrend (positive returns, low drawdown)
  - bear: sustained downtrend (negative returns, increasing drawdown)
  - high_vol: elevated volatility regardless of direction
  - sideways: range-bound, low volatility, near-zero returns

Uses a simple rule-based approach with rolling statistics. This is
deterministic and fast — no ML or hidden state.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class RegimePeriod:
    """A detected market regime period."""

    regime: str  # bull | bear | high_vol | sideways
    start: pd.Timestamp
    end: pd.Timestamp
    annual_return: float
    volatility: float
    max_drawdown: float

    @property
    def days(self) -> int:
        return (self.end - self.start).days

    def __repr__(self) -> str:
        return (
            f"RegimePeriod({self.regime}, {self.start.date()} to {self.end.date()}, "
            f"{self.days}d, ret={self.annual_return:.1%}, vol={self.volatility:.1%})"
        )


def detect_regimes(
    prices: pd.Series,
    window: int = 126,
    vol_threshold: float = 0.25,
    bull_threshold: float = 0.10,
    bear_threshold: float = -0.10,
    smooth_days: int = 21,
    merge_gap: int = 10,
) -> list[RegimePeriod]:
    """Detect market regimes from a price series.

    Uses a two-pass approach:
    1. Classify each day using rolling statistics
    2. Smooth labels (majority vote over smooth_days window) to remove noise
    3. Merge nearby same-regime periods separated by short gaps

    Args:
        prices: Daily close prices with DatetimeIndex.
        window: Rolling window in trading days (~6 months = 126).
        vol_threshold: Annualized vol above this → high_vol regime.
        bull_threshold: Annualized return above this → bull (if not high_vol).
        bear_threshold: Annualized return below this → bear (if not high_vol).
        smooth_days: Window for majority-vote smoothing of labels.
        merge_gap: Merge same-regime periods separated by <= this many days.

    Returns:
        List of RegimePeriod objects covering the full price history.
    """
    if len(prices) < window + 1:
        return []

    returns = prices.pct_change().dropna()

    # Rolling statistics (longer window = less noise)
    rolling_ret = returns.rolling(window).mean() * 252  # annualized
    rolling_vol = returns.rolling(window).std() * np.sqrt(252)  # annualized

    # Classify each day
    labels = pd.Series("sideways", index=rolling_ret.index)
    labels[rolling_vol > vol_threshold] = "high_vol"
    labels[(rolling_ret > bull_threshold) & (rolling_vol <= vol_threshold)] = "bull"
    labels[(rolling_ret < bear_threshold) & (rolling_vol <= vol_threshold)] = "bear"

    # Drop NaN window
    labels = labels.dropna()
    if labels.empty:
        return []

    # Pass 2: Majority-vote smoothing to eliminate short flickers
    if smooth_days > 1 and len(labels) > smooth_days:
        labels = _smooth_labels(labels, smooth_days)

    # Merge consecutive same-regime days into periods
    raw_periods = _merge_consecutive(prices, labels)

    # Pass 3: Merge nearby same-regime periods separated by short gaps
    if merge_gap > 0:
        raw_periods = _merge_nearby(prices, raw_periods, merge_gap)

    # Pass 4: Drop very short noise periods (< 5 trading days)
    raw_periods = [p for p in raw_periods if p.days >= 5]

    return raw_periods


def _smooth_labels(labels: pd.Series, window: int) -> pd.Series:
    """Majority-vote smoothing: each day gets the most common label in its window."""
    regime_map = {"bull": 0, "bear": 1, "high_vol": 2, "sideways": 3}
    reverse_map = {v: k for k, v in regime_map.items()}

    numeric = labels.map(regime_map).values
    smoothed = np.empty_like(numeric)

    half = window // 2
    for i in range(len(numeric)):
        start = max(0, i - half)
        end = min(len(numeric), i + half + 1)
        counts = np.bincount(numeric[start:end], minlength=4)
        smoothed[i] = counts.argmax()

    return pd.Series(
        [reverse_map[int(v)] for v in smoothed],
        index=labels.index,
    )


def _merge_consecutive(
    prices: pd.Series, labels: pd.Series
) -> list[RegimePeriod]:
    """Merge consecutive same-regime days into RegimePeriod objects."""
    periods: list[RegimePeriod] = []
    current_regime = labels.iloc[0]
    period_start = labels.index[0]

    for i in range(1, len(labels)):
        if labels.iloc[i] != current_regime:
            period_end = labels.index[i - 1]
            period = _build_period(prices, current_regime, period_start, period_end)
            if period is not None:
                periods.append(period)
            current_regime = labels.iloc[i]
            period_start = labels.index[i]

    # Final period
    period = _build_period(prices, current_regime, period_start, labels.index[-1])
    if period is not None:
        periods.append(period)

    return periods


def _merge_nearby(
    prices: pd.Series,
    periods: list[RegimePeriod],
    max_gap_days: int,
) -> list[RegimePeriod]:
    """Merge same-regime periods separated by <= max_gap_days trading days."""
    if len(periods) <= 1:
        return periods

    merged: list[RegimePeriod] = [periods[0]]
    for p in periods[1:]:
        prev = merged[-1]
        gap = (p.start - prev.end).days
        if p.regime == prev.regime and gap <= max_gap_days:
            # Merge: extend prev to cover p
            new_period = _build_period(prices, prev.regime, prev.start, p.end)
            if new_period is not None:
                merged[-1] = new_period
            else:
                merged.append(p)
        else:
            merged.append(p)
    return merged


def select_regime_periods(
    prices: pd.Series,
    min_days: int = 30,
    window: int = 126,
) -> dict[str, RegimePeriod]:
    """Select the best (longest) period for each regime type.

    Returns a dict with up to 4 entries: {regime_name: RegimePeriod}.
    Only includes regimes with at least min_days duration.
    """
    all_periods = detect_regimes(prices, window=window)

    best: dict[str, RegimePeriod] = {}
    for period in all_periods:
        if period.days < min_days:
            continue
        existing = best.get(period.regime)
        if existing is None or period.days > existing.days:
            best[period.regime] = period

    return best


def get_regime_date_ranges(
    prices: pd.Series,
    min_days: int = 30,
) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    """Convenience: get (start, end) tuples for each regime."""
    periods = select_regime_periods(prices, min_days=min_days)
    return {name: (p.start, p.end) for name, p in periods.items()}


def _build_period(
    prices: pd.Series,
    regime: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> RegimePeriod | None:
    """Build a RegimePeriod from a price slice."""
    mask = (prices.index >= start) & (prices.index <= end)
    segment = prices[mask]
    if len(segment) < 2:
        return None

    total_return = segment.iloc[-1] / segment.iloc[0] - 1
    days = (end - start).days
    years = max(days / 365.25, 0.01)
    annual_return = (1 + total_return) ** (1 / years) - 1

    daily_returns = segment.pct_change().dropna()
    volatility = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 1 else 0.0

    # Max drawdown
    cummax = segment.cummax()
    drawdown = (segment - cummax) / cummax
    max_drawdown = drawdown.min()

    return RegimePeriod(
        regime=regime,
        start=start,
        end=end,
        annual_return=annual_return,
        volatility=volatility,
        max_drawdown=max_drawdown,
    )
