"""Cross-sectional analysis: ranking, portfolios, IC, monotonicity, evaluation."""

import numpy as np
import pandas as pd
from scipy import stats


def rank_cross_sectionally(alpha_df: pd.DataFrame) -> pd.DataFrame:
    """Percentile ranks across tickers at each date."""
    return alpha_df.rank(axis=1, pct=True)


def form_portfolios(
    alpha_ranks: pd.DataFrame,
    returns_df: pd.DataFrame,
    n_groups: int = 3,
) -> dict[int, pd.Series]:
    """Group tickers by rank into n_groups at each date.

    Compute equal-weight next-day returns per group.
    Returns {1: bottom_series, ..., n: top_series}.
    """
    # Align indices
    common_idx = alpha_ranks.index.intersection(returns_df.index)
    alpha_ranks = alpha_ranks.loc[common_idx]
    returns_df = returns_df.loc[common_idx]

    # Assign groups: 1 (bottom) to n_groups (top)
    breakpoints = np.linspace(0, 1, n_groups + 1)
    group_returns: dict[int, list[float]] = {g: [] for g in range(1, n_groups + 1)}

    for date in common_idx:
        ranks = alpha_ranks.loc[date].dropna()
        rets = returns_df.loc[date].reindex(ranks.index).dropna()
        common_tickers = ranks.index.intersection(rets.index)
        if len(common_tickers) < n_groups:
            continue
        ranks = ranks[common_tickers]
        rets = rets[common_tickers]

        for g in range(1, n_groups + 1):
            low = breakpoints[g - 1]
            high = breakpoints[g]
            if g == n_groups:
                mask = (ranks >= low) & (ranks <= high)
            else:
                mask = (ranks >= low) & (ranks < high)
            if mask.sum() > 0:
                group_returns[g].append(rets[mask].mean())

    return {g: pd.Series(vals) for g, vals in group_returns.items()}


def compute_information_coefficient(
    alpha_df: pd.DataFrame,
    returns_df: pd.DataFrame,
) -> tuple[float, float]:
    """Daily Spearman corr of alpha vs next-day returns across tickers.

    Returns (mean_ic, ic_t_stat).
    """
    # Use next-day returns: shift returns back by 1
    fwd_returns = returns_df.shift(-1)

    common_idx = alpha_df.index.intersection(fwd_returns.index)
    alpha_df = alpha_df.loc[common_idx]
    fwd_returns = fwd_returns.loc[common_idx]

    daily_ics: list[float] = []
    for date in common_idx:
        a = alpha_df.loc[date].dropna()
        r = fwd_returns.loc[date].reindex(a.index).dropna()
        common = a.index.intersection(r.index)
        if len(common) < 4:
            continue
        corr, _ = stats.spearmanr(a[common], r[common])
        if not np.isnan(corr):
            daily_ics.append(corr)

    if len(daily_ics) < 2:
        return 0.0, 0.0

    mean_ic = float(np.mean(daily_ics))
    ic_std = float(np.std(daily_ics, ddof=1))
    ic_t_stat = mean_ic / (ic_std / np.sqrt(len(daily_ics))) if ic_std > 1e-10 else 0.0
    return mean_ic, ic_t_stat


def compute_monotonicity(group_mean_returns: dict[int, float]) -> float:
    """Fraction of adjacent group pairs with correct ordering.

    Returns 0.0 to 1.0. Correct ordering = higher group has higher return.
    """
    groups = sorted(group_mean_returns.keys())
    if len(groups) < 2:
        return 0.0

    correct = 0
    total = len(groups) - 1
    for i in range(total):
        if group_mean_returns[groups[i + 1]] >= group_mean_returns[groups[i]]:
            correct += 1

    return correct / total


def evaluate_cross_sectional(
    mean_ic: float,
    ic_t_stat: float,
    monotonicity: float,
    long_short_spread: float,
) -> tuple[str, list[str]]:
    """Evaluate cross-sectional factor quality.

    PASS: |IC| >= 0.03, |t-stat| >= 2.0, monotonicity >= 0.5, spread > 0
    MARGINAL: |IC| >= 0.01, monotonicity >= 0.5
    FAIL: otherwise
    """
    reasons: list[str] = []
    abs_ic = abs(mean_ic)
    abs_t = abs(ic_t_stat)

    # Check FAIL conditions
    if abs_ic < 0.01:
        reasons.append(f"FAIL: |IC| {abs_ic:.4f} < 0.01")
    if monotonicity < 0.5:
        reasons.append(f"FAIL: monotonicity {monotonicity:.2f} < 0.50")

    if any(r.startswith("FAIL") for r in reasons):
        return "FAIL", reasons

    # Check PASS conditions
    is_pass = True

    if abs_ic < 0.03:
        reasons.append(f"MARGINAL: |IC| {abs_ic:.4f} < 0.03")
        is_pass = False

    if abs_t < 2.0:
        reasons.append(f"MARGINAL: |t-stat| {abs_t:.2f} < 2.0")
        is_pass = False

    if long_short_spread <= 0:
        reasons.append(f"MARGINAL: L/S spread {long_short_spread:.4f} <= 0")
        is_pass = False

    if is_pass:
        reasons.append(
            f"IC {mean_ic:.4f}, t={ic_t_stat:.2f}, "
            f"mono={monotonicity:.2f}, L/S={long_short_spread:.4f}"
        )
        return "PASS", reasons
    else:
        return "MARGINAL", reasons
