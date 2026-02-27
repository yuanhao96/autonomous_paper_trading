"""Universe screener — applies filter chains to build filtered universes."""

from __future__ import annotations

import logging

import pandas as pd

from src.data.manager import DataManager
from src.universe.computed import compute_universe
from src.universe.providers.yfinance_provider import YFinanceUniverseProvider
from src.universe.spec import Filter, UniverseSpec
from src.universe.static import STATIC_UNIVERSES, get_static_universe

logger = logging.getLogger(__name__)


class UniverseScreener:
    """Resolves a UniverseSpec into a concrete list of symbols.

    Three modes:
    1. Static: return the fixed list from static_symbols
    2. Filtered: start from a base pool, apply filter chain
    3. Computed: placeholder for statistical methods (cointegration, etc.)
    """

    def __init__(
        self,
        provider: YFinanceUniverseProvider | None = None,
        data_manager: DataManager | None = None,
    ) -> None:
        self._provider = provider or YFinanceUniverseProvider()
        self._dm = data_manager or DataManager()

    def resolve(self, spec: UniverseSpec) -> list[str]:
        """Resolve a UniverseSpec to a list of symbols."""
        # Level 1: Static
        if spec.is_static:
            return list(spec.static_symbols or [])

        # Level 3: Computed
        if spec.is_computed:
            base_pool = self._get_base_pool(spec.asset_class)
            if not base_pool:
                return []
            return compute_universe(
                name=spec.computation,
                base_symbols=base_pool,
                data_manager=self._dm,
                params=spec.computation_params,
            )

        # Level 2: Filtered
        return self._resolve_filtered(spec)

    def _resolve_filtered(self, spec: UniverseSpec) -> list[str]:
        """Apply filter chain to a base pool of securities."""
        # Determine base pool based on asset class
        base_pool = self._get_base_pool(spec.asset_class)
        if not base_pool:
            return []

        # If no filters, return base pool (capped)
        if not spec.filters:
            return base_pool[: spec.max_securities]

        # Categorize filters
        fundamental_fields = {"market_cap", "avg_daily_volume", "price", "sector",
                              "industry", "pe_ratio", "pb_ratio", "dividend_yield",
                              "beta", "country", "exchange"}
        momentum_fields = {"momentum_1m", "momentum_3m", "momentum_6m", "momentum_12m"}
        volatility_fields = {"volatility_30d"}
        rsi_fields = {"rsi_14"}

        needs_fundamentals = any(f.field in fundamental_fields for f in spec.filters)
        needs_momentum = any(f.field in momentum_fields for f in spec.filters)
        needs_volatility = any(f.field in volatility_fields for f in spec.filters)
        needs_rsi = any(f.field in rsi_fields for f in spec.filters)

        # Build a combined DataFrame with all needed data
        dfs: list[pd.DataFrame] = []

        if needs_fundamentals:
            dfs.append(self._provider.get_fundamentals(base_pool))
        if needs_momentum:
            dfs.append(self._provider.get_momentum(base_pool))
        if needs_volatility:
            dfs.append(self._provider.get_volatility(base_pool))
        if needs_rsi:
            dfs.append(self._provider.get_rsi(base_pool))

        if not dfs:
            return base_pool[: spec.max_securities]

        data = dfs[0]
        for df in dfs[1:]:
            data = data.join(df, how="outer")

        # Apply filters in order
        for filt in spec.filters:
            data = _apply_filter(data, filt)
            if data.empty:
                return []

        # Enforce size constraints
        symbols = list(data.index)
        if len(symbols) < spec.min_securities:
            return []  # Not enough securities to form a viable universe
        return symbols[: spec.max_securities]

    def _get_base_pool(self, asset_class: str) -> list[str]:
        """Get the base pool of symbols for an asset class."""
        pool_map = {
            "us_equity": "sp500",
            "etf": "broad_etfs",
            "forex": "g10_forex",
            "crypto": "crypto_top",
        }
        pool_name = pool_map.get(asset_class)
        if pool_name and pool_name in STATIC_UNIVERSES:
            return get_static_universe(pool_name)
        return []


def _apply_filter(data: pd.DataFrame, filt: Filter) -> pd.DataFrame:
    """Apply a single Filter to a DataFrame."""
    col = filt.field
    if col not in data.columns:
        logger.warning(
            "Filter '%s %s %s' skipped — column '%s' not in data",
            col, filt.operator, filt.value, col,
        )
        return data

    op = filt.operator
    val = filt.value

    if op == "greater_than":
        return data[data[col] > val]
    elif op == "less_than":
        return data[data[col] < val]
    elif op == "equals":
        return data[data[col] == val]
    elif op == "top_n":
        n = int(val)
        if len(data) <= n:
            return data
        return data.nlargest(n, col)
    elif op == "bottom_n":
        n = int(val)
        if len(data) <= n:
            return data
        return data.nsmallest(n, col)
    elif op == "in_set":
        if isinstance(val, (list, tuple)):
            return data[data[col].isin(val)]
        return data
    elif op == "between":
        if isinstance(val, (list, tuple)) and len(val) == 2:
            return data[(data[col] >= val[0]) & (data[col] <= val[1])]
        return data
    else:
        return data
