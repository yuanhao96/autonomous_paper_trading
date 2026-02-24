# SAFETY CRITICAL — DO NOT MODIFY VIA EVOLUTION LOOP
# This module enforces hard risk limits regardless of strategy signals.

"""Risk management module.

Enforces position sizing limits, drawdown guards, sector concentration caps,
and basic sanity checks on every order before execution. The hard limits are
derived from the human-controlled ``config/preferences.yaml`` and cannot be
overridden by any agent or evolution loop.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.preferences import Preferences

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class OrderRequest:
    """Describes a proposed order to be risk-checked before execution."""

    ticker: str
    side: str  # "buy" or "sell"
    quantity: int
    order_type: str  # "market" or "limit"
    limit_price: float | None = None


@dataclass
class RiskCheckResult:
    """Outcome of a risk check on a proposed order."""

    approved: bool
    reason: str


@dataclass
class PortfolioState:
    """Current snapshot of the portfolio used for risk calculations.

    ``positions`` is a dict mapping ticker -> position info dict with keys:
        - quantity (int): number of shares held
        - market_value (float): current market value of the position
        - avg_cost (float): average cost basis per share
        - sector (str): GICS sector or equivalent classification
    """

    total_equity: float
    cash: float
    positions: dict[str, dict]
    daily_pnl: float


# ---------------------------------------------------------------------------
# Risk Manager
# ---------------------------------------------------------------------------

# Threshold at which a warning is emitted (80 % of any hard limit).
_WARNING_THRESHOLD = 0.80


class RiskManager:
    """Enforces hard risk limits derived from human-controlled preferences.

    Every order must pass *all* checks to be approved.  The checks are:

    1. **Max position size** — the order's estimated market value must not
       cause any single position to exceed ``max_position_pct`` of total equity.
    2. **Max daily loss** — if the portfolio's daily P&L has already breached
       ``max_daily_loss_pct`` of total equity, new *buy* orders are rejected.
    3. **Max sector concentration** — the order must not cause total exposure
       to a single sector to exceed ``max_sector_concentration_pct`` of equity.
    4. **Basic sanity** — quantity must be positive, total equity must be
       positive, and side / order_type must be valid.
    """

    def __init__(self, preferences: Preferences) -> None:
        self._preferences = preferences

    # -- public API ---------------------------------------------------------

    def check_order(
        self, order: OrderRequest, portfolio: PortfolioState
    ) -> RiskCheckResult:
        """Run all risk checks on *order* given the current *portfolio*.

        Returns ``RiskCheckResult(approved=True, ...)`` only when every check
        passes; otherwise returns ``approved=False`` with a description of the
        first failing check.
        """

        # 4. Basic sanity (checked first so downstream math is safe).
        sanity = self._check_sanity(order, portfolio)
        if not sanity.approved:
            return sanity

        # For sell orders we only need sanity — the remaining checks guard
        # against *increasing* risk, which sells do not do.
        if order.side == "sell":
            return RiskCheckResult(approved=True, reason="All checks passed")

        # Estimate the market value of this order.  For limit orders we use
        # the limit price; for market orders we fall back to the position's
        # average cost (best available proxy) or 0 if the ticker is new.
        price_estimate = self._estimate_price(order, portfolio)
        order_value = price_estimate * order.quantity

        # 1. Max position size.
        pos_check = self._check_position_size(order, portfolio, order_value)
        if not pos_check.approved:
            return pos_check

        # 2. Max daily loss (drawdown guard).
        dd_check = self._check_daily_loss(portfolio)
        if not dd_check.approved:
            return dd_check

        # 3. Max sector concentration.
        sector_check = self._check_sector_concentration(
            order, portfolio, order_value
        )
        if not sector_check.approved:
            return sector_check

        return RiskCheckResult(approved=True, reason="All checks passed")

    def check_portfolio_health(self, portfolio: PortfolioState) -> list[str]:
        """Return non-blocking warning messages when the portfolio is
        approaching any hard limit (>80 % of the limit).
        """

        warnings: list[str] = []

        if portfolio.total_equity <= 0:
            warnings.append("Portfolio total equity is zero or negative.")
            return warnings

        prefs = self._preferences

        # -- position size warnings ----------------------------------------
        max_pos_frac = prefs.max_position_pct / 100.0
        for ticker, pos in portfolio.positions.items():
            pos_frac = pos["market_value"] / portfolio.total_equity
            if pos_frac >= _WARNING_THRESHOLD * max_pos_frac:
                warnings.append(
                    f"Position {ticker} is at {pos_frac * 100:.1f}% of equity "
                    f"(limit {prefs.max_position_pct}%)."
                )

        # -- daily loss warning --------------------------------------------
        max_loss_frac = prefs.max_daily_loss_pct / 100.0
        daily_loss_frac = -portfolio.daily_pnl / portfolio.total_equity
        if daily_loss_frac >= _WARNING_THRESHOLD * max_loss_frac:
            warnings.append(
                f"Daily loss is {daily_loss_frac * 100:.1f}% of equity "
                f"(limit {prefs.max_daily_loss_pct}%)."
            )

        # -- sector concentration warnings ---------------------------------
        max_sector_frac = prefs.max_sector_concentration_pct / 100.0
        sector_exposure: dict[str, float] = {}
        for _ticker, pos in portfolio.positions.items():
            sector = pos.get("sector", "Unknown")
            sector_exposure[sector] = (
                sector_exposure.get(sector, 0.0) + pos["market_value"]
            )
        for sector, exposure in sector_exposure.items():
            sector_frac = exposure / portfolio.total_equity
            if sector_frac >= _WARNING_THRESHOLD * max_sector_frac:
                warnings.append(
                    f"Sector '{sector}' concentration is at "
                    f"{sector_frac * 100:.1f}% of equity "
                    f"(limit {prefs.max_sector_concentration_pct}%)."
                )

        return warnings

    # -- private helpers ----------------------------------------------------

    @staticmethod
    def _estimate_price(
        order: OrderRequest, portfolio: PortfolioState
    ) -> float:
        """Best-effort price estimate for an order."""
        if order.order_type == "limit" and order.limit_price is not None:
            return order.limit_price
        # Fall back to avg_cost of existing position, or 0.
        pos = portfolio.positions.get(order.ticker)
        if pos is not None:
            return float(pos.get("avg_cost", 0.0))
        return 0.0

    def _check_sanity(
        self, order: OrderRequest, portfolio: PortfolioState
    ) -> RiskCheckResult:
        if order.quantity <= 0:
            return RiskCheckResult(
                approved=False,
                reason="Failed: basic sanity — quantity must be > 0.",
            )
        if portfolio.total_equity <= 0:
            return RiskCheckResult(
                approved=False,
                reason="Failed: basic sanity — total equity must be > 0.",
            )
        if order.side not in ("buy", "sell"):
            return RiskCheckResult(
                approved=False,
                reason=(
                    f"Failed: basic sanity — side must be 'buy' or 'sell', "
                    f"got '{order.side}'."
                ),
            )
        if order.order_type not in ("market", "limit"):
            return RiskCheckResult(
                approved=False,
                reason=(
                    f"Failed: basic sanity — order_type must be 'market' or "
                    f"'limit', got '{order.order_type}'."
                ),
            )
        if order.order_type == "limit" and order.limit_price is None:
            return RiskCheckResult(
                approved=False,
                reason="Failed: basic sanity — limit order requires a limit_price.",
            )
        return RiskCheckResult(approved=True, reason="Sanity OK")

    def _check_position_size(
        self,
        order: OrderRequest,
        portfolio: PortfolioState,
        order_value: float,
    ) -> RiskCheckResult:
        existing_value = 0.0
        pos = portfolio.positions.get(order.ticker)
        if pos is not None:
            existing_value = float(pos.get("market_value", 0.0))

        new_position_value = existing_value + order_value
        max_allowed = (self._preferences.max_position_pct / 100.0) * portfolio.total_equity

        if new_position_value > max_allowed:
            return RiskCheckResult(
                approved=False,
                reason=(
                    f"Failed: max position size — {order.ticker} would be "
                    f"{new_position_value / portfolio.total_equity * 100:.1f}% "
                    f"of equity (limit {self._preferences.max_position_pct}%)."
                ),
            )
        return RiskCheckResult(approved=True, reason="Position size OK")

    def _check_daily_loss(
        self, portfolio: PortfolioState
    ) -> RiskCheckResult:
        max_loss_frac = self._preferences.max_daily_loss_pct / 100.0
        daily_loss_frac = -portfolio.daily_pnl / portfolio.total_equity

        if daily_loss_frac >= max_loss_frac:
            return RiskCheckResult(
                approved=False,
                reason=(
                    f"Failed: max daily loss — daily loss is "
                    f"{daily_loss_frac * 100:.1f}% of equity "
                    f"(limit {self._preferences.max_daily_loss_pct}%). "
                    f"New buy orders are blocked."
                ),
            )
        return RiskCheckResult(approved=True, reason="Daily loss OK")

    def _check_sector_concentration(
        self,
        order: OrderRequest,
        portfolio: PortfolioState,
        order_value: float,
    ) -> RiskCheckResult:
        # Determine the sector for this order.  If the ticker already exists
        # in the portfolio we use its sector; otherwise we label it "Unknown".
        pos = portfolio.positions.get(order.ticker)
        order_sector: str = pos["sector"] if pos is not None else "Unknown"

        # Compute current sector exposure.
        sector_exposure: dict[str, float] = {}
        for _ticker, p in portfolio.positions.items():
            sector = p.get("sector", "Unknown")
            sector_exposure[sector] = (
                sector_exposure.get(sector, 0.0) + float(p["market_value"])
            )

        # Add the proposed order value.
        new_sector_value = sector_exposure.get(order_sector, 0.0) + order_value
        max_allowed = (
            self._preferences.max_sector_concentration_pct / 100.0
        ) * portfolio.total_equity

        if new_sector_value > max_allowed:
            return RiskCheckResult(
                approved=False,
                reason=(
                    f"Failed: max sector concentration — sector "
                    f"'{order_sector}' would be "
                    f"{new_sector_value / portfolio.total_equity * 100:.1f}% "
                    f"of equity "
                    f"(limit {self._preferences.max_sector_concentration_pct}%)."
                ),
            )
        return RiskCheckResult(approved=True, reason="Sector concentration OK")
