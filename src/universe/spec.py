"""Universe selection data models — defines what securities a strategy trades."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


VALID_ASSET_CLASSES = ("us_equity", "etf", "forex", "crypto", "futures")
VALID_OPERATORS = (
    "greater_than",
    "less_than",
    "top_n",
    "bottom_n",
    "in_set",
    "between",
    "equals",
)
VALID_FIELDS = (
    "market_cap",
    "avg_daily_volume",
    "price",
    "sector",
    "industry",
    "momentum_1m",
    "momentum_3m",
    "momentum_6m",
    "momentum_12m",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield",
    "volatility_30d",
    "beta",
    "rsi_14",
    "country",
    "exchange",
)
VALID_REBALANCE = ("daily", "weekly", "monthly", "quarterly")


@dataclass(frozen=True)
class Filter:
    """Single filtering criterion for universe selection."""

    field: str
    operator: str
    value: Any

    def __post_init__(self) -> None:
        if self.field not in VALID_FIELDS:
            raise ValueError(f"Unknown filter field: {self.field}. Valid: {VALID_FIELDS}")
        if self.operator not in VALID_OPERATORS:
            raise ValueError(
                f"Unknown operator: {self.operator}. Valid: {VALID_OPERATORS}"
            )


@dataclass
class UniverseSpec:
    """Defines which securities a strategy operates on.

    Three levels:
    - Static: fixed list of symbols (static_symbols is set)
    - Filtered: broad pool + filter chain
    - Computed: statistical computation (e.g., cointegration pairs)
    """

    asset_class: str
    filters: list[Filter] = field(default_factory=list)
    max_securities: int = 50
    min_securities: int = 1
    rebalance_frequency: str = "monthly"
    static_symbols: list[str] | None = None

    # For computed universes (Level 3)
    computation: str | None = None  # e.g., "cointegration_pairs"
    computation_params: dict[str, Any] = field(default_factory=dict)

    # Auto-populated
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""

    def __post_init__(self) -> None:
        if self.asset_class not in VALID_ASSET_CLASSES:
            raise ValueError(
                f"Unknown asset_class: {self.asset_class}. Valid: {VALID_ASSET_CLASSES}"
            )
        if self.rebalance_frequency not in VALID_REBALANCE:
            raise ValueError(
                f"Unknown rebalance_frequency: {self.rebalance_frequency}. "
                f"Valid: {VALID_REBALANCE}"
            )
        if not self.name:
            if self.static_symbols:
                self.name = f"static_{self.asset_class}_{len(self.static_symbols)}"
            elif self.computation:
                self.name = f"computed_{self.computation}"
            else:
                self.name = f"filtered_{self.asset_class}_{self.max_securities}"

    @property
    def is_static(self) -> bool:
        return self.static_symbols is not None

    @property
    def is_computed(self) -> bool:
        return self.computation is not None
