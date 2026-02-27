"""Signal engine — compute target positions from StrategySpec + current prices.

Delegates all signal logic to src.core.signals (single source of truth).
Each symbol gets a signal: "long" (hold), or "flat" (no position).
"""

from __future__ import annotations

import logging

import pandas as pd

from src.core.signals import compute_signal
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
        prices: {symbol: OHLCV DataFrame} with DatetimeIndex.
        lookback_bars: Minimum bars of history needed.

    Returns:
        {symbol: "long" | "flat"} for each symbol.
    """
    template = spec.template.split("/")[-1] if "/" in spec.template else spec.template
    params = spec.parameters

    signals: dict[str, str] = {}
    for symbol, df in prices.items():
        if len(df) < lookback_bars:
            logger.warning(
                "Insufficient data for %s: %d bars (need %d)",
                symbol, len(df), lookback_bars,
            )
            signals[symbol] = "flat"
            continue
        signals[symbol] = compute_signal(template, df, params)

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

    max_pos = spec.risk.max_position_pct
    max_positions = spec.risk.max_positions

    # Limit number of positions
    if len(long_symbols) > max_positions:
        long_symbols = long_symbols[:max_positions]

    weight = min(max_pos, 1.0 / len(long_symbols))
    return {s: (weight if s in long_symbols else 0.0) for s in signals}
