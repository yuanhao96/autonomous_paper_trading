"""Data models for live trading — deployments, positions, snapshots, reports."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Position:
    """A single position held in the broker account."""

    symbol: str
    quantity: int
    avg_cost: float
    market_value: float
    unrealized_pnl: float

    @property
    def current_price(self) -> float:
        if self.quantity == 0:
            return 0.0
        return self.market_value / self.quantity


@dataclass
class TradeRecord:
    """A single executed trade."""

    symbol: str
    side: str  # "buy" | "sell"
    quantity: int
    price: float
    timestamp: datetime
    commission: float = 0.0
    order_id: str = ""

    @property
    def notional(self) -> float:
        return self.quantity * self.price


@dataclass
class LiveSnapshot:
    """Point-in-time snapshot of a live deployment's state."""

    deployment_id: str
    timestamp: datetime
    equity: float
    cash: float
    positions: list[Position] = field(default_factory=list)
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    total_trades: int = 0
    total_fees: float = 0.0

    @property
    def position_count(self) -> int:
        return len(self.positions)

    @property
    def invested_pct(self) -> float:
        if self.equity <= 0:
            return 0.0
        total_market_value = sum(p.market_value for p in self.positions)
        return total_market_value / self.equity


@dataclass
class Deployment:
    """A deployed strategy running on a broker account."""

    spec_id: str
    account_id: str
    mode: str  # "paper" | "ibkr_paper" | "live"
    symbols: list[str]

    # Auto-populated
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = "pending"  # pending | active | paused | stopped | promoted
    started_at: datetime = field(default_factory=datetime.utcnow)
    stopped_at: datetime | None = None
    initial_cash: float = 100_000.0
    config: dict[str, Any] = field(default_factory=dict)

    # Accumulated snapshots (in-memory; also persisted to DB)
    snapshots: list[LiveSnapshot] = field(default_factory=list)
    trades: list[TradeRecord] = field(default_factory=list)

    @property
    def days_elapsed(self) -> int:
        end = self.stopped_at or datetime.utcnow()
        return (end - self.started_at).days

    @property
    def is_active(self) -> bool:
        return self.status == "active"


@dataclass
class ComparisonReport:
    """Comparison of live performance vs validation backtest expectations."""

    deployment_id: str
    days_elapsed: int

    # Returns
    live_return: float = 0.0
    expected_annual_return: float = 0.0
    return_drift: float = 0.0  # |live - expected|

    # Risk-adjusted
    live_sharpe: float = 0.0
    expected_sharpe: float = 0.0
    sharpe_drift: float = 0.0

    # Drawdown
    live_max_drawdown: float = 0.0
    expected_max_drawdown: float = 0.0

    # Verdict
    within_tolerance: bool = True
    alerts: list[str] = field(default_factory=list)

    def summary(self) -> str:
        status = "OK" if self.within_tolerance else "DRIFT DETECTED"
        lines = [
            f"Comparison [{status}] — {self.days_elapsed} days",
            f"  Return: live={self.live_return:+.2%} expected_annual={self.expected_annual_return:+.2%}",
            f"  Sharpe: live={self.live_sharpe:.2f} expected={self.expected_sharpe:.2f} drift={self.sharpe_drift:.2f}",
            f"  MaxDD:  live={self.live_max_drawdown:.2%} expected={self.expected_max_drawdown:.2%}",
        ]
        if self.alerts:
            lines.append(f"  Alerts: {', '.join(self.alerts)}")
        return "\n".join(lines)


@dataclass
class PromotionReport:
    """Evaluation of whether a paper-traded strategy should go live."""

    deployment_id: str
    spec_id: str
    days_elapsed: int
    min_days_required: int

    # Checks
    meets_time_requirement: bool = False
    comparison: ComparisonReport | None = None
    risk_violations: list[str] = field(default_factory=list)

    # Decision
    decision: str = "needs_review"  # approved | rejected | needs_review
    reasoning: str = ""

    def summary(self) -> str:
        lines = [
            f"Promotion Report [{self.decision.upper()}]",
            f"  Deployment: {self.deployment_id}",
            f"  Strategy:   {self.spec_id}",
            f"  Days:       {self.days_elapsed}/{self.min_days_required}",
            f"  Time req:   {'MET' if self.meets_time_requirement else 'NOT MET'}",
            f"  Risk:       {len(self.risk_violations)} violations",
        ]
        if self.comparison:
            lines.append(f"  Drift:      {'OK' if self.comparison.within_tolerance else 'EXCEEDED'}")
        lines.append(f"  Reasoning:  {self.reasoning}")
        return "\n".join(lines)
