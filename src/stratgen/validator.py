"""Validation functions: quintile analysis, composite IC, multi-horizon evaluation."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy import stats


def form_quintile_returns(
    alpha: pd.DataFrame,
    returns: pd.DataFrame,
    n_groups: int = 5,
    horizon: int = 1,
) -> dict[int, pd.Series]:
    """Group stocks into quintiles by alpha score, compute forward returns per group.

    At each date:
      - Rank stocks by alpha into n_groups (1=bottom, n=top)
      - Compute equal-weight forward return over `horizon` days for each group

    Returns {1: bottom_series, ..., n: top_series} where each Series is
    indexed by date with mean forward return for that group.
    """
    # Forward returns over horizon
    if horizon == 1:
        fwd_ret = returns.shift(-1)
    else:
        # Cumulative return over horizon days
        fwd_ret = (1 + returns).rolling(horizon).apply(np.prod, raw=True).shift(-horizon) - 1

    common_idx = alpha.index.intersection(fwd_ret.index)
    alpha = alpha.loc[common_idx]
    fwd_ret = fwd_ret.loc[common_idx]

    breakpoints = np.linspace(0, 1, n_groups + 1)
    group_returns: dict[int, list[float]] = {g: [] for g in range(1, n_groups + 1)}
    group_dates: list = []

    for date in common_idx:
        a = alpha.loc[date].dropna()
        r = fwd_ret.loc[date].reindex(a.index).dropna()
        common = a.index.intersection(r.index)
        if len(common) < n_groups * 4:
            continue

        ranks = a[common].rank(pct=True)
        group_dates.append(date)

        for g in range(1, n_groups + 1):
            low = breakpoints[g - 1]
            high = breakpoints[g]
            if g == n_groups:
                mask = (ranks >= low) & (ranks <= high)
            else:
                mask = (ranks >= low) & (ranks < high)
            if mask.sum() > 0:
                group_returns[g].append(float(r[common][mask].mean()))
            else:
                group_returns[g].append(np.nan)

    return {g: pd.Series(vals, index=group_dates[:len(vals)]) for g, vals in group_returns.items()}


def compute_quintile_stats(
    group_returns: dict[int, pd.Series],
) -> dict[str, float]:
    """Compute summary stats from quintile returns.

    Returns dict with:
      - mean_return_q1..q5: annualized mean return per group
      - long_short_spread: top minus bottom group (annualized)
      - monotonicity: fraction of adjacent pairs with correct ordering
    """
    result: dict[str, float] = {}
    n_groups = len(group_returns)
    group_means: dict[int, float] = {}

    for g, series in sorted(group_returns.items()):
        mean_daily = float(series.mean()) if len(series) > 0 else 0.0
        ann = mean_daily * 252
        result[f"mean_return_q{g}"] = round(ann, 6)
        group_means[g] = mean_daily

    # Long-short spread (top - bottom, annualized)
    top = group_means.get(n_groups, 0.0)
    bottom = group_means.get(1, 0.0)
    result["long_short_spread_ann"] = round((top - bottom) * 252, 6)

    # Monotonicity
    groups = sorted(group_means.keys())
    if len(groups) >= 2:
        correct = sum(
            1 for i in range(len(groups) - 1)
            if group_means[groups[i + 1]] >= group_means[groups[i]]
        )
        result["monotonicity"] = round(correct / (len(groups) - 1), 4)
    else:
        result["monotonicity"] = 0.0

    return result


def compute_composite_ic(
    alpha: pd.DataFrame,
    returns: pd.DataFrame,
    horizon: int = 1,
) -> dict[str, float]:
    """Compute Spearman IC of composite alpha vs forward returns.

    Returns dict with mean_ic, ic_std, ic_t_stat, ic_ir (information ratio),
    pct_positive (fraction of days with positive IC).
    """
    if horizon == 1:
        fwd_ret = returns.shift(-1)
    else:
        fwd_ret = (1 + returns).rolling(horizon).apply(np.prod, raw=True).shift(-horizon) - 1

    common_idx = alpha.index.intersection(fwd_ret.index)
    alpha = alpha.loc[common_idx]
    fwd_ret = fwd_ret.loc[common_idx]

    daily_ics: list[float] = []
    for date in common_idx:
        a = alpha.loc[date].dropna()
        r = fwd_ret.loc[date].reindex(a.index).dropna()
        common = a.index.intersection(r.index)
        if len(common) < 10:
            continue
        if a[common].nunique() < 2 or r[common].nunique() < 2:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", stats.ConstantInputWarning)
            corr, _ = stats.spearmanr(a[common], r[common])
        if not np.isnan(corr):
            daily_ics.append(corr)

    if len(daily_ics) < 2:
        return {"mean_ic": 0.0, "ic_std": 0.0, "ic_t_stat": 0.0, "ic_ir": 0.0,
                "pct_positive": 0.0, "n_days": 0}

    arr = np.array(daily_ics)
    mean_ic = float(arr.mean())
    ic_std = float(arr.std(ddof=1))
    n = len(arr)
    ic_t = mean_ic / (ic_std / np.sqrt(n)) if ic_std > 1e-10 else 0.0
    ic_ir = mean_ic / ic_std if ic_std > 1e-10 else 0.0
    pct_pos = float((arr > 0).mean())

    return {
        "mean_ic": round(mean_ic, 6),
        "ic_std": round(ic_std, 6),
        "ic_t_stat": round(ic_t, 4),
        "ic_ir": round(ic_ir, 6),
        "pct_positive": round(pct_pos, 4),
        "n_days": n,
    }


def multi_horizon_ic(
    alpha: pd.DataFrame,
    returns: pd.DataFrame,
    horizons: list[int] | None = None,
) -> dict[int, dict[str, float]]:
    """Compute composite IC at multiple forward return horizons.

    Returns {horizon: ic_stats_dict} for each horizon.
    """
    if horizons is None:
        horizons = [1, 5, 10, 20]

    return {h: compute_composite_ic(alpha, returns, horizon=h) for h in horizons}


def evaluate_composite(
    ic_stats: dict[str, float],
    quintile_stats: dict[str, float],
) -> tuple[str, list[str]]:
    """Evaluate composite alpha quality.

    STRONG: |IC| >= 0.03, |t| >= 3.0, monotonicity >= 0.75, spread > 0
    WEAK: |IC| >= 0.01, |t| >= 1.5, monotonicity >= 0.5
    NONE: otherwise
    """
    reasons: list[str] = []
    abs_ic = abs(ic_stats["mean_ic"])
    abs_t = abs(ic_stats["ic_t_stat"])
    mono = quintile_stats["monotonicity"]
    spread = quintile_stats["long_short_spread_ann"]

    # Check NONE conditions
    if abs_ic < 0.005:
        reasons.append(f"|IC| {abs_ic:.4f} < 0.005 — no detectable signal")
    if abs_t < 1.0:
        reasons.append(f"|t-stat| {abs_t:.2f} < 1.0 — not significant")

    if abs_ic < 0.005 or abs_t < 1.0:
        return "NONE", reasons

    # Check WEAK vs STRONG
    is_strong = True

    if abs_ic < 0.03:
        reasons.append(f"|IC| {abs_ic:.4f} < 0.03")
        is_strong = False
    if abs_t < 3.0:
        reasons.append(f"|t-stat| {abs_t:.2f} < 3.0")
        is_strong = False
    if mono < 0.75:
        reasons.append(f"monotonicity {mono:.2f} < 0.75")
        is_strong = False
    if spread <= 0:
        reasons.append(f"L/S spread {spread:.4f} <= 0")
        is_strong = False

    if is_strong:
        reasons.append(
            f"IC={ic_stats['mean_ic']:.4f}, t={abs_t:.2f}, "
            f"mono={mono:.2f}, L/S={spread:.4f}"
        )
        return "STRONG", reasons

    # WEAK: check minimums
    if abs_ic < 0.01 or mono < 0.5:
        return "NONE", reasons

    return "WEAK", reasons
