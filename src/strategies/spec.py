"""Core strategy data models — the single source of truth for all pipelines."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.universe.spec import UniverseSpec


@dataclass(frozen=True)
class RiskParams:
    """Risk parameters for a strategy. Bounded by preferences.yaml limits."""

    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    trailing_stop_pct: float | None = None
    max_position_pct: float = 0.10
    max_positions: int = 10
    position_size_method: str = "equal_weight"  # equal_weight | volatility_target | kelly

    def __post_init__(self) -> None:
        if self.stop_loss_pct is not None and not 0 < self.stop_loss_pct < 1:
            raise ValueError(f"stop_loss_pct must be between 0 and 1, got {self.stop_loss_pct}")
        if self.take_profit_pct is not None and not 0 < self.take_profit_pct < 5:
            raise ValueError(f"take_profit_pct must be between 0 and 5, got {self.take_profit_pct}")
        if self.max_positions < 1:
            raise ValueError(f"max_positions must be >= 1, got {self.max_positions}")
        valid_methods = ("equal_weight", "volatility_target", "kelly")
        if self.position_size_method not in valid_methods:
            raise ValueError(
                f"position_size_method must be one of {valid_methods}, "
                f"got {self.position_size_method}"
            )


@dataclass
class StrategySpec:
    """A constrained strategy specification derived from the knowledge base.

    The LLM generates these by selecting a template from the 87 documented
    strategies and setting parameters within documented bounds.
    """

    # Identity
    template: str  # Knowledge base reference: "momentum/momentum-effect-in-stocks"
    parameters: dict[str, Any]  # Strategy-specific params: {"lookback": 12, "hold_period": 1}
    universe_id: str  # Reference to a UniverseSpec id
    risk: RiskParams = field(default_factory=RiskParams)

    # Resolved universe (populated when available, not serialized)
    universe_spec: UniverseSpec | None = None

    # Multi-strategy composition
    combination: list[str] = field(default_factory=list)
    combination_method: str = "equal_weight"  # equal_weight | score_rank | intersection

    # Auto-populated
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    version: int = 1
    parent_id: str | None = None
    generation: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "human"  # human | llm_explore | llm_exploit

    def __post_init__(self) -> None:
        if not self.name:
            slug = self.template.split("/")[-1] if "/" in self.template else self.template
            self.name = f"{slug}_v{self.version}"


@dataclass
class RegimeResult:
    """Performance in a specific market regime."""

    regime: str  # bull | bear | high_vol | sideways
    period_start: str
    period_end: str
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int


@dataclass
class StrategyResult:
    """Rich diagnostics from backtesting — fed back to LLM for evolution."""

    spec_id: str
    phase: str  # screen | validate | live

    # Core metrics
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration_days: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0

    # Regime performance
    regime_results: list[RegimeResult] = field(default_factory=list)

    # Series data (for visualization / deeper analysis)
    equity_curve: list[float] = field(default_factory=list)
    drawdown_series: list[float] = field(default_factory=list)

    # Failure analysis
    passed: bool = False
    failure_reason: str | None = None
    failure_details: str | None = None

    # Costs (populated by NautilusTrader phase)
    total_fees: float = 0.0
    total_slippage: float = 0.0

    # Optimized parameters (populated by screening phase)
    optimized_parameters: dict[str, Any] = field(default_factory=dict)

    # Walk-forward analysis (populated when optimize=True in screening)
    in_sample_sharpe: float = 0.0

    # Survivorship tracking (populated by screener)
    symbols_requested: int = 0
    symbols_with_data: int = 0

    # Meta
    backtest_start: str = ""
    backtest_end: str = ""
    run_duration_seconds: float = 0.0
