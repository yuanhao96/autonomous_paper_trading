"""Broker interface — abstract API + IBKR implementation via ib_insync.

The broker handles order execution, position tracking, and account queries.
IBKRBroker requires TWS or IB Gateway running locally.
PaperBroker provides a local simulation for testing.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from src.live.models import Position, TradeRecord

logger = logging.getLogger(__name__)


def is_ibkr_available() -> bool:
    """Check if ib_insync is installed."""
    try:
        import ib_insync  # noqa: F401
        return True
    except ImportError:
        return False


class BrokerAPI(ABC):
    """Abstract broker interface."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the broker."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close broker connection."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if broker connection is active."""

    @abstractmethod
    def get_account_summary(self) -> dict[str, float]:
        """Get account summary: equity, cash, buying_power, etc."""

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Get all current positions."""

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        limit_price: float | None = None,
    ) -> TradeRecord | None:
        """Place an order and return the fill record (or None if rejected)."""

    @abstractmethod
    def cancel_all_orders(self) -> int:
        """Cancel all open orders. Returns count of cancelled orders."""

    @abstractmethod
    def get_recent_trades(self, since: datetime | None = None) -> list[TradeRecord]:
        """Get recent trade executions."""


class IBKRBroker(BrokerAPI):
    """Interactive Brokers implementation via ib_insync.

    Requires TWS or IB Gateway running locally:
    - Paper: port 7497 (TWS) or 4002 (Gateway)
    - Live: port 7496 (TWS) or 4001 (Gateway)
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
    ) -> None:
        self._host = host
        self._port = port
        self._client_id = client_id
        self._ib = None

    def connect(self) -> None:
        if not is_ibkr_available():
            raise RuntimeError(
                "ib_insync not installed. Install with: pip install ib_insync"
            )
        from ib_insync import IB
        self._ib = IB()
        self._ib.connect(self._host, self._port, clientId=self._client_id)
        logger.info(
            "Connected to IBKR at %s:%d (client_id=%d)",
            self._host, self._port, self._client_id,
        )

    def disconnect(self) -> None:
        if self._ib and self._ib.isConnected():
            self._ib.disconnect()
            logger.info("Disconnected from IBKR")

    def is_connected(self) -> bool:
        return self._ib is not None and self._ib.isConnected()

    def get_account_summary(self) -> dict[str, float]:
        self._ensure_connected()
        summary: dict[str, float] = {}
        for item in self._ib.accountSummary():
            if item.tag in ("NetLiquidation", "TotalCashValue", "BuyingPower",
                            "GrossPositionValue", "MaintMarginReq"):
                try:
                    summary[item.tag] = float(item.value)
                except ValueError:
                    pass
        return {
            "equity": summary.get("NetLiquidation", 0.0),
            "cash": summary.get("TotalCashValue", 0.0),
            "buying_power": summary.get("BuyingPower", 0.0),
            "gross_position_value": summary.get("GrossPositionValue", 0.0),
        }

    def get_positions(self) -> list[Position]:
        self._ensure_connected()
        positions: list[Position] = []
        for pos in self._ib.positions():
            contract = pos.contract
            positions.append(Position(
                symbol=contract.symbol,
                quantity=int(pos.position),
                avg_cost=pos.avgCost,
                market_value=float(pos.position) * pos.avgCost,
                unrealized_pnl=0.0,  # Updated via portfolio updates
            ))
        # Update market values from portfolio
        for pf in self._ib.portfolio():
            for p in positions:
                if p.symbol == pf.contract.symbol:
                    p.market_value = pf.marketValue
                    p.unrealized_pnl = pf.unrealizedPNL
        return positions

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        limit_price: float | None = None,
    ) -> TradeRecord | None:
        self._ensure_connected()
        from ib_insync import MarketOrder, LimitOrder, Stock

        contract = Stock(symbol, "SMART", "USD")
        self._ib.qualifyContracts(contract)

        action = "BUY" if side == "buy" else "SELL"
        if order_type == "limit" and limit_price is not None:
            order = LimitOrder(action, quantity, limit_price)
        else:
            order = MarketOrder(action, quantity)

        trade = self._ib.placeOrder(contract, order)
        # Wait for fill (with timeout)
        self._ib.sleep(2)

        if trade.orderStatus.status in ("Filled", "Inactive"):
            fill_price = trade.orderStatus.avgFillPrice or 0.0
            commission = sum(f.commissionReport.commission for f in trade.fills if f.commissionReport)
            return TradeRecord(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=fill_price,
                timestamp=datetime.utcnow(),
                commission=commission,
                order_id=str(trade.order.orderId),
            )

        logger.warning("Order not filled: %s %s %d — status: %s", side, symbol, quantity, trade.orderStatus.status)
        return None

    def cancel_all_orders(self) -> int:
        self._ensure_connected()
        open_orders = self._ib.openOrders()
        for order in open_orders:
            self._ib.cancelOrder(order)
        return len(open_orders)

    def get_recent_trades(self, since: datetime | None = None) -> list[TradeRecord]:
        self._ensure_connected()
        trades: list[TradeRecord] = []
        for fill in self._ib.fills():
            ts = fill.time if hasattr(fill, "time") else datetime.utcnow()
            if since and ts < since:
                continue
            trades.append(TradeRecord(
                symbol=fill.contract.symbol,
                side="buy" if fill.execution.side == "BOT" else "sell",
                quantity=int(fill.execution.shares),
                price=fill.execution.price,
                timestamp=ts,
                commission=fill.commissionReport.commission if fill.commissionReport else 0.0,
                order_id=str(fill.execution.orderId),
            ))
        return trades

    def _ensure_connected(self) -> None:
        if not self.is_connected():
            raise RuntimeError("Not connected to IBKR. Call connect() first.")


class PaperBroker(BrokerAPI):
    """Local paper trading simulator for testing without IBKR.

    Tracks positions and trades in-memory. Does not simulate market impact,
    slippage, or partial fills — all orders fill at the given price.
    """

    def __init__(self, initial_cash: float = 100_000.0, commission_rate: float = 0.002) -> None:
        self._initial_cash = initial_cash
        self._cash = initial_cash
        self._commission_rate = commission_rate
        self._positions: dict[str, Position] = {}
        self._trades: list[TradeRecord] = []
        self._connected = False
        self._current_prices: dict[str, float] = {}

    def set_prices(self, prices: dict[str, float]) -> None:
        """Set current market prices for simulation."""
        self._current_prices = prices

    def connect(self) -> None:
        self._connected = True
        logger.info("PaperBroker connected (simulated)")

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_account_summary(self) -> dict[str, float]:
        equity = self._cash + sum(p.market_value for p in self._positions.values())
        return {
            "equity": equity,
            "cash": self._cash,
            "buying_power": self._cash,
            "gross_position_value": sum(p.market_value for p in self._positions.values()),
        }

    def get_positions(self) -> list[Position]:
        # Update market values with current prices
        for symbol, pos in self._positions.items():
            if symbol in self._current_prices:
                price = self._current_prices[symbol]
                pos.market_value = pos.quantity * price
                pos.unrealized_pnl = (price - pos.avg_cost) * pos.quantity
        return list(self._positions.values())

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        limit_price: float | None = None,
    ) -> TradeRecord | None:
        price = limit_price or self._current_prices.get(symbol, 0.0)
        if price <= 0:
            logger.warning("No price available for %s", symbol)
            return None

        commission = price * quantity * self._commission_rate
        notional = price * quantity

        if side == "buy":
            if notional + commission > self._cash:
                logger.warning("Insufficient cash for %s: need %.2f, have %.2f", symbol, notional + commission, self._cash)
                return None
            self._cash -= notional + commission
            if symbol in self._positions:
                pos = self._positions[symbol]
                total_cost = pos.avg_cost * pos.quantity + price * quantity
                total_qty = pos.quantity + quantity
                pos.avg_cost = total_cost / total_qty if total_qty > 0 else 0
                pos.quantity = total_qty
                pos.market_value = total_qty * price
            else:
                self._positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_cost=price,
                    market_value=quantity * price,
                    unrealized_pnl=0.0,
                )
        elif side == "sell":
            if symbol not in self._positions or self._positions[symbol].quantity < quantity:
                logger.warning("Insufficient shares for %s sell", symbol)
                return None
            self._cash += notional - commission
            pos = self._positions[symbol]
            pos.quantity -= quantity
            pos.market_value = pos.quantity * price
            pos.unrealized_pnl = (price - pos.avg_cost) * pos.quantity
            if pos.quantity == 0:
                del self._positions[symbol]

        trade = TradeRecord(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            timestamp=datetime.utcnow(),
            commission=commission,
        )
        self._trades.append(trade)
        return trade

    def cancel_all_orders(self) -> int:
        return 0  # No pending orders in simulation

    def get_recent_trades(self, since: datetime | None = None) -> list[TradeRecord]:
        if since is None:
            return list(self._trades)
        return [t for t in self._trades if t.timestamp >= since]
