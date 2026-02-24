"""Performance metrics calculations.

Provides functions for computing standard trading performance statistics
(Sharpe ratio, max drawdown, win rate, P&L breakdown) and a convenience
function that bundles them all into a single ``PerformanceSummary``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TRADING_DAYS_PER_YEAR: int = 252


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PerformanceSummary:
    """Aggregated performance snapshot for a strategy or portfolio."""

    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_pnl: float
    avg_pnl: float
    best_trade: float
    worst_trade: float
    num_trades: int


# ---------------------------------------------------------------------------
# Individual metric functions
# ---------------------------------------------------------------------------


def calculate_sharpe(
    returns: pd.Series,
    risk_free_rate: float = 0.05,
) -> float:
    """Annualised Sharpe ratio from a series of *daily* returns.

    Parameters
    ----------
    returns:
        Daily simple returns (e.g. 0.01 for +1 %).
    risk_free_rate:
        Annual risk-free rate used to compute the daily excess return.

    Returns
    -------
    float
        Annualised Sharpe ratio, or 0.0 when the standard deviation of
        returns is zero (or the series is empty).
    """
    if returns.empty:
        return 0.0

    daily_rfr: float = risk_free_rate / _TRADING_DAYS_PER_YEAR
    excess_returns: pd.Series = returns - daily_rfr

    std: float = float(excess_returns.std(ddof=1))
    if std < 1e-12 or math.isnan(std):
        return 0.0

    mean_excess: float = float(excess_returns.mean())
    sharpe: float = (mean_excess / std) * np.sqrt(_TRADING_DAYS_PER_YEAR)
    return float(sharpe)


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """Maximum drawdown expressed as a positive fraction.

    Parameters
    ----------
    equity_curve:
        Cumulative portfolio value over time (e.g. starting at 100 000).

    Returns
    -------
    float
        Max drawdown as a positive fraction (e.g. 0.15 for a 15 % drawdown).
        Returns 0.0 for empty or single-point equity curves.
    """
    if equity_curve.empty or len(equity_curve) < 2:
        return 0.0

    cumulative_max: pd.Series = equity_curve.cummax()
    drawdown: pd.Series = (cumulative_max - equity_curve) / cumulative_max

    max_dd: float = float(drawdown.max())
    if math.isnan(max_dd):
        return 0.0
    return max_dd


def calculate_win_rate(trades: list[dict]) -> float:
    """Fraction of trades with positive P&L.

    Parameters
    ----------
    trades:
        Each dict must contain a ``pnl`` key (float).

    Returns
    -------
    float
        Win rate in [0, 1].  Returns 0.0 when *trades* is empty.
    """
    if not trades:
        return 0.0

    winners: int = sum(1 for t in trades if t["pnl"] > 0)
    return winners / len(trades)


def calculate_pnl(trades: list[dict]) -> dict:
    """Aggregate P&L statistics across a list of trades.

    Parameters
    ----------
    trades:
        Each dict must contain a ``pnl`` key (float).

    Returns
    -------
    dict
        Keys: ``total_pnl``, ``avg_pnl``, ``best_trade``, ``worst_trade``,
        ``num_trades``.  All values are 0 / 0.0 when *trades* is empty.
    """
    if not trades:
        return {
            "total_pnl": 0.0,
            "avg_pnl": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "num_trades": 0,
        }

    pnls: list[float] = [t["pnl"] for t in trades]
    total: float = sum(pnls)
    return {
        "total_pnl": total,
        "avg_pnl": total / len(pnls),
        "best_trade": max(pnls),
        "worst_trade": min(pnls),
        "num_trades": len(pnls),
    }


# ---------------------------------------------------------------------------
# Convenience aggregator
# ---------------------------------------------------------------------------


def generate_summary(
    equity_curve: pd.Series,
    trades: list[dict],
) -> PerformanceSummary:
    """Compute all performance metrics and return a ``PerformanceSummary``.

    Parameters
    ----------
    equity_curve:
        Cumulative portfolio value over time.
    trades:
        List of trade dicts, each containing at least a ``pnl`` key.

    Returns
    -------
    PerformanceSummary
    """
    # Derive daily simple returns from the equity curve.
    if len(equity_curve) >= 2:
        daily_returns: pd.Series = equity_curve.pct_change().dropna()
    else:
        daily_returns = pd.Series(dtype=float)

    pnl_stats: dict = calculate_pnl(trades)

    return PerformanceSummary(
        sharpe_ratio=calculate_sharpe(daily_returns),
        max_drawdown=calculate_max_drawdown(equity_curve),
        win_rate=calculate_win_rate(trades),
        total_pnl=pnl_stats["total_pnl"],
        avg_pnl=pnl_stats["avg_pnl"],
        best_trade=pnl_stats["best_trade"],
        worst_trade=pnl_stats["worst_trade"],
        num_trades=pnl_stats["num_trades"],
    )
