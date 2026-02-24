"""Signal execution module.

Converts trading signals into broker orders after risk checks.
Signals are processed in descending order of strength so that
the highest-conviction ideas get first access to available capital.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from trading.paper_broker import Order, PaperBroker
from trading.risk import OrderRequest, PortfolioState, RiskCheckResult, RiskManager

logger = logging.getLogger(__name__)

# Conservative default: no single position may exceed 10% of total equity.
_MAX_POSITION_ALLOCATION_PCT: float = 0.10


@dataclass(frozen=True)
class Signal:
    """A directional trading signal produced by a strategy."""

    ticker: str
    action: str  # "buy" or "sell"
    strength: float  # 0.0 – 1.0
    reason: str
    strategy_name: str

    def __post_init__(self) -> None:
        if self.action not in ("buy", "sell"):
            raise ValueError(
                f"Signal action must be 'buy' or 'sell', got '{self.action}'"
            )
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(
                f"Signal strength must be in [0, 1], got {self.strength}"
            )


@dataclass(frozen=True)
class ExecutionResult:
    """Outcome of attempting to execute a single signal."""

    signal: Signal
    executed: bool
    order: Order | None = None
    rejection_reason: str | None = None


def _compute_quantity(
    signal: Signal,
    current_price: float,
    portfolio_state: PortfolioState,
) -> int:
    """Determine the number of shares to trade.

    Quantity = floor(signal.strength * max_position_allocation / current_price)
    where max_position_allocation = total_equity * _MAX_POSITION_ALLOCATION_PCT.
    """
    max_allocation: float = portfolio_state.total_equity * _MAX_POSITION_ALLOCATION_PCT
    dollar_amount: float = signal.strength * max_allocation
    if current_price <= 0:
        return 0
    qty: int = math.floor(dollar_amount / current_price)
    return qty


def execute_signals(
    signals: list[Signal],
    broker: PaperBroker,
    risk_manager: RiskManager,
    portfolio_state: PortfolioState,
) -> list[ExecutionResult]:
    """Execute a list of trading signals through risk checks and the broker.

    Signals are processed in descending order of strength so that the
    highest-conviction trades are evaluated first (and thus have priority
    over available capital and risk budget).

    Parameters
    ----------
    signals:
        Trading signals to execute.
    broker:
        Paper broker instance used to submit orders.
    risk_manager:
        Risk manager that validates each order before submission.
    portfolio_state:
        Current portfolio snapshot (positions, cash, equity).

    Returns
    -------
    list[ExecutionResult]
        One result per input signal, preserving the strength-sorted order.
    """
    results: list[ExecutionResult] = []

    # Process strongest signals first.
    sorted_signals: list[Signal] = sorted(
        signals, key=lambda s: s.strength, reverse=True
    )

    for signal in sorted_signals:
        logger.info(
            "Processing signal: %s %s (strength=%.2f, strategy=%s, reason=%s)",
            signal.action,
            signal.ticker,
            signal.strength,
            signal.strategy_name,
            signal.reason,
        )

        # ---- Fetch current price -------------------------------------------
        try:
            current_price: float = broker.get_current_price(signal.ticker)
        except Exception:
            reason = f"Failed to fetch current price for {signal.ticker}"
            logger.exception(reason)
            results.append(
                ExecutionResult(
                    signal=signal,
                    executed=False,
                    rejection_reason=reason,
                )
            )
            continue

        # ---- Determine quantity --------------------------------------------
        qty: int = _compute_quantity(signal, current_price, portfolio_state)
        if qty <= 0:
            reason = (
                f"Computed quantity is 0 for {signal.ticker} "
                f"(price={current_price:.2f}, strength={signal.strength:.2f}, "
                f"equity={portfolio_state.total_equity:.2f})"
            )
            logger.warning(reason)
            results.append(
                ExecutionResult(
                    signal=signal,
                    executed=False,
                    rejection_reason=reason,
                )
            )
            continue

        # ---- Build order request -------------------------------------------
        order_request = OrderRequest(
            ticker=signal.ticker,
            side=signal.action,
            quantity=qty,
            order_type="market",
        )

        # ---- Risk check ----------------------------------------------------
        risk_result: RiskCheckResult = risk_manager.check_order(
            order_request, portfolio_state
        )

        if not risk_result.approved:
            reason = (
                f"Risk check rejected order for {signal.ticker}: "
                f"{risk_result.reason}"
            )
            logger.warning(reason)
            results.append(
                ExecutionResult(
                    signal=signal,
                    executed=False,
                    rejection_reason=reason,
                )
            )
            continue

        # ---- Submit order --------------------------------------------------
        try:
            order: Order = broker.submit_order(
                ticker=order_request.ticker,
                side=order_request.side,
                quantity=order_request.quantity,
            )
            logger.info(
                "Order submitted: %s %d shares of %s @ %.2f (order_id=%s)",
                signal.action.upper(),
                qty,
                signal.ticker,
                current_price,
                getattr(order, "order_id", "N/A"),
            )
            results.append(
                ExecutionResult(
                    signal=signal,
                    executed=True,
                    order=order,
                )
            )
        except Exception:
            reason = f"Broker rejected or failed to submit order for {signal.ticker}"
            logger.exception(reason)
            results.append(
                ExecutionResult(
                    signal=signal,
                    executed=False,
                    rejection_reason=reason,
                )
            )

    return results
