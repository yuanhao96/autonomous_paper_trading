"""Strategy capacity analysis — estimate how much capital a strategy can handle.

Capacity is limited by:
1. Market impact: large orders move prices against you
2. Liquidity: not enough volume to fill orders at desired prices
3. Slippage: gap between signal price and fill price grows with size

We estimate capacity by analyzing the relationship between strategy
trade sizes and available market liquidity.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class CapacityEstimate:
    """Estimated strategy capacity."""

    max_capital: float  # Maximum recommended capital in dollars
    limiting_factor: str  # What limits capacity: "volume" | "impact" | "concentration"
    avg_daily_volume_usd: float  # Average daily dollar volume of traded securities
    max_participation_rate: float  # Max fraction of daily volume we'd consume
    details: str

    @property
    def is_viable(self) -> bool:
        """Check if capacity meets minimum threshold."""
        return self.max_capital >= 50_000  # $50K minimum for IBKR


def estimate_capacity(
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    avg_position_pct: float = 0.10,
    max_positions: int = 10,
    max_participation: float = 0.01,
    avg_hold_days: int = 21,
) -> CapacityEstimate:
    """Estimate strategy capacity from price and volume data.

    Args:
        prices: DataFrame of close prices (columns = symbols, index = dates).
        volumes: DataFrame of volumes (same shape as prices).
        avg_position_pct: Average position size as fraction of portfolio.
        max_positions: Maximum concurrent positions.
        max_participation: Max fraction of daily volume per trade (1% default).
        avg_hold_days: Average holding period in days.

    Returns:
        CapacityEstimate with maximum recommended capital.
    """
    if prices.empty or volumes.empty:
        return CapacityEstimate(
            max_capital=0,
            limiting_factor="no_data",
            avg_daily_volume_usd=0,
            max_participation_rate=max_participation,
            details="No price/volume data available",
        )

    # Dollar volume per symbol per day
    dollar_volume = prices * volumes

    # Average daily dollar volume across all symbols
    avg_dv_per_symbol = dollar_volume.mean().mean()
    total_avg_dv = dollar_volume.mean().sum()

    # Capacity limited by participation rate
    # If we trade X% of portfolio per day, and can only be Y% of daily volume:
    # max_capital * position_pct <= avg_daily_volume * max_participation
    # max_capital <= avg_daily_volume * max_participation / position_pct

    # Per-position capacity
    min_symbol_dv = dollar_volume.mean().min()
    per_position_capacity = min_symbol_dv * max_participation / max(avg_position_pct, 0.01)

    # Portfolio-level capacity (accounting for turnover)
    # Turnover = max_positions * 2 / avg_hold_days (buy + sell)
    daily_turnover_frac = max_positions * 2 / max(avg_hold_days, 1)
    portfolio_capacity = total_avg_dv * max_participation / max(daily_turnover_frac * avg_position_pct, 0.001)

    # Take the binding constraint
    if per_position_capacity < portfolio_capacity:
        max_capital = per_position_capacity
        limiting_factor = "volume"
        details = (
            f"Limited by least-liquid symbol: avg daily volume "
            f"${min_symbol_dv:,.0f}, max position ${per_position_capacity:,.0f}"
        )
    else:
        max_capital = portfolio_capacity
        limiting_factor = "impact"
        details = (
            f"Limited by portfolio turnover: {daily_turnover_frac:.1f} trades/day, "
            f"max capital ${portfolio_capacity:,.0f}"
        )

    return CapacityEstimate(
        max_capital=max_capital,
        limiting_factor=limiting_factor,
        avg_daily_volume_usd=total_avg_dv,
        max_participation_rate=max_participation,
        details=details,
    )


def quick_capacity_check(
    symbols: list[str],
    data: dict[str, pd.DataFrame],
    position_pct: float = 0.10,
    max_positions: int = 10,
) -> CapacityEstimate:
    """Quick capacity estimate from OHLCV data dict.

    Args:
        symbols: List of symbols in the universe.
        data: Dict of symbol → OHLCV DataFrame.
        position_pct: Position size as fraction of portfolio.
        max_positions: Max concurrent positions.

    Returns:
        CapacityEstimate.
    """
    if not data:
        return CapacityEstimate(
            max_capital=0,
            limiting_factor="no_data",
            avg_daily_volume_usd=0,
            max_participation_rate=0.01,
            details="No data provided",
        )

    prices_dict = {}
    volumes_dict = {}
    for sym in symbols:
        if sym in data and not data[sym].empty:
            prices_dict[sym] = data[sym]["Close"]
            volumes_dict[sym] = data[sym]["Volume"]

    if not prices_dict:
        return CapacityEstimate(
            max_capital=0,
            limiting_factor="no_data",
            avg_daily_volume_usd=0,
            max_participation_rate=0.01,
            details="No valid price data",
        )

    prices_df = pd.DataFrame(prices_dict)
    volumes_df = pd.DataFrame(volumes_dict)

    return estimate_capacity(
        prices=prices_df,
        volumes=volumes_df,
        avg_position_pct=position_pct,
        max_positions=max_positions,
    )
