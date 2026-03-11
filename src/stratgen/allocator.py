"""Portfolio allocation: convert composite alpha scores to portfolio weights."""

from __future__ import annotations

import pandas as pd


def allocate_alpha_proportional(
    scores: pd.Series,
    top_n: int = 20,
    max_position: float = 0.05,
    min_score: float = 0.0,
) -> pd.Series:
    """Allocate portfolio weights proportional to alpha scores.

    Steps:
      1. Filter to top_n stocks with score > min_score
      2. Normalize: weight_i = score_i / sum(scores)
      3. Apply position cap: redistribute excess to uncapped positions
      4. Return weights (sum to 1.0 or less)

    Args:
        scores: Series(ticker -> composite alpha score), higher = better.
        top_n: Number of top stocks to include.
        max_position: Maximum weight per position (default 5%).
        min_score: Minimum alpha score to include (default 0 = long-only).

    Returns:
        Series(ticker -> weight), sorted descending. Sums to ~1.0.
    """
    # 1. Filter: only positive scores, top N
    eligible = scores[scores > min_score].nlargest(top_n)

    if eligible.empty:
        return pd.Series(dtype=float)

    # 2. Normalize to sum to 1.0
    weights = eligible / eligible.sum()

    # 3. Apply position cap iteratively
    for _ in range(20):  # max iterations to converge
        capped = weights > max_position + 1e-10
        if not capped.any():
            break

        excess = (weights[capped] - max_position).sum()
        weights[capped] = max_position

        # Redistribute excess to uncapped positions proportionally
        uncapped = ~capped & (weights < max_position - 1e-10)
        if uncapped.any():
            uncapped_total = weights[uncapped].sum()
            if uncapped_total > 0:
                # Scale uncapped weights to absorb excess while staying within cap
                scale = (uncapped_total + excess) / uncapped_total
                weights[uncapped] *= scale
        # If no uncapped positions available, excess is lost (all at cap)

    return weights.sort_values(ascending=False)
