"""Alpaca paper trading wrapper with mock mode.

In mock mode, all state is stored locally in SQLite (data/paper_trades.db)
and market prices are fetched via yfinance. In real mode, orders are routed
to the Alpaca paper-trading API.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
_DEFAULT_DB_PATH: Path = _PROJECT_ROOT / "data" / "paper_trades.db"

_INITIAL_CASH: float = 100_000.0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Order:
    id: str
    ticker: str
    side: str  # "buy" or "sell"
    quantity: int
    order_type: str  # "market" or "limit"
    limit_price: float | None
    status: str  # "pending", "filled", "cancelled"
    filled_price: float | None
    filled_at: str | None
    created_at: str


@dataclass
class Position:
    ticker: str
    quantity: int
    avg_cost: float
    market_value: float
    unrealized_pnl: float
    sector: str = "unknown"


@dataclass
class Portfolio:
    total_equity: float
    cash: float
    positions: list[Position] = field(default_factory=list)
    timestamp: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _current_price(ticker: str) -> float:
    """Fetch the latest closing price for *ticker* via yfinance."""
    yf_ticker = yf.Ticker(ticker)
    hist = yf_ticker.history(period="5d", interval="1d")
    if hist.empty:
        raise ValueError(f"No price data available for {ticker}")
    return float(hist["Close"].iloc[-1])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# PaperBroker
# ---------------------------------------------------------------------------


class PaperBroker:
    """Unified interface for paper trading via Alpaca or a local mock."""

    def __init__(self, mock: bool = True, db_path: Path | None = None) -> None:
        self.mock = mock

        if self.mock:
            self._db_path = db_path or _DEFAULT_DB_PATH
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_db()
        else:
            self._init_alpaca()

    # -- Initialisation -----------------------------------------------------

    def _init_db(self) -> None:
        """Create SQLite tables if they do not exist and seed cash."""
        con = self._connect()
        try:
            cur = con.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id           TEXT PRIMARY KEY,
                    ticker       TEXT    NOT NULL,
                    side         TEXT    NOT NULL,
                    quantity     INTEGER NOT NULL,
                    order_type   TEXT    NOT NULL,
                    limit_price  REAL,
                    status       TEXT    NOT NULL,
                    filled_price REAL,
                    filled_at    TEXT,
                    created_at   TEXT    NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS positions (
                    ticker   TEXT PRIMARY KEY,
                    quantity INTEGER NOT NULL,
                    avg_cost REAL    NOT NULL,
                    sector   TEXT    NOT NULL DEFAULT 'unknown'
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS account (
                    id   INTEGER PRIMARY KEY CHECK (id = 1),
                    cash REAL NOT NULL
                )
                """
            )
            # Seed with initial cash when the account table is empty.
            row = cur.execute("SELECT cash FROM account WHERE id = 1").fetchone()
            if row is None:
                cur.execute(
                    "INSERT INTO account (id, cash) VALUES (1, ?)",
                    (_INITIAL_CASH,),
                )
                logger.info("Initialised mock account with $%.2f cash", _INITIAL_CASH)
            con.commit()
        finally:
            con.close()

    def _init_alpaca(self) -> None:
        """Initialise the Alpaca REST client from environment variables."""
        import alpaca_trade_api as tradeapi  # type: ignore[import-untyped]

        api_key = os.environ.get("ALPACA_API_KEY", "")
        secret_key = os.environ.get("ALPACA_SECRET_KEY", "")
        base_url = os.environ.get(
            "ALPACA_BASE_URL", "https://paper-api.alpaca.markets"
        )
        if not api_key or not secret_key:
            raise RuntimeError(
                "ALPACA_API_KEY and ALPACA_SECRET_KEY must be set for real mode"
            )
        self._api = tradeapi.REST(api_key, secret_key, base_url, api_version="v2")
        logger.info("Connected to Alpaca paper trading at %s", base_url)

    # -- SQLite helpers -----------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path))

    def _get_cash(self) -> float:
        con = self._connect()
        try:
            row = con.execute("SELECT cash FROM account WHERE id = 1").fetchone()
            return float(row[0]) if row else _INITIAL_CASH
        finally:
            con.close()

    def _set_cash(self, cash: float) -> None:
        con = self._connect()
        try:
            con.execute("UPDATE account SET cash = ? WHERE id = 1", (cash,))
            con.commit()
        finally:
            con.close()

    # -- Public API ---------------------------------------------------------

    def submit_order(
        self,
        ticker: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        limit_price: float | None = None,
    ) -> Order:
        """Submit a buy or sell order.

        In mock mode the order is filled immediately at the latest close price
        obtained from yfinance. In real mode the order is forwarded to Alpaca.
        """
        if side not in ("buy", "sell"):
            raise ValueError(f"side must be 'buy' or 'sell', got '{side}'")
        if quantity <= 0:
            raise ValueError("quantity must be positive")

        if self.mock:
            return self._mock_submit_order(ticker, side, quantity, order_type, limit_price)
        else:
            return self._alpaca_submit_order(ticker, side, quantity, order_type, limit_price)

    def get_positions(self) -> list[Position]:
        """Return all open positions with current market values."""
        if self.mock:
            return self._mock_get_positions()
        else:
            return self._alpaca_get_positions()

    def get_portfolio(self) -> Portfolio:
        """Return the current portfolio snapshot."""
        if self.mock:
            return self._mock_get_portfolio()
        else:
            return self._alpaca_get_portfolio()

    def get_order_history(self, limit: int = 50) -> list[Order]:
        """Return recent orders, newest first."""
        if self.mock:
            return self._mock_get_order_history(limit)
        else:
            return self._alpaca_get_order_history(limit)

    # -- Mock implementations -----------------------------------------------

    def _mock_submit_order(
        self,
        ticker: str,
        side: str,
        quantity: int,
        order_type: str,
        limit_price: float | None,
    ) -> Order:
        price = _current_price(ticker)

        # For limit orders check feasibility; if the limit is not met, cancel.
        if order_type == "limit" and limit_price is not None:
            if side == "buy" and price > limit_price:
                order = Order(
                    id=str(uuid4()),
                    ticker=ticker,
                    side=side,
                    quantity=quantity,
                    order_type=order_type,
                    limit_price=limit_price,
                    status="cancelled",
                    filled_price=None,
                    filled_at=None,
                    created_at=_now_iso(),
                )
                self._persist_order(order)
                logger.info("Limit buy cancelled: price %.2f > limit %.2f", price, limit_price)
                return order
            if side == "sell" and price < limit_price:
                order = Order(
                    id=str(uuid4()),
                    ticker=ticker,
                    side=side,
                    quantity=quantity,
                    order_type=order_type,
                    limit_price=limit_price,
                    status="cancelled",
                    filled_price=None,
                    filled_at=None,
                    created_at=_now_iso(),
                )
                self._persist_order(order)
                logger.info("Limit sell cancelled: price %.2f < limit %.2f", price, limit_price)
                return order

        cost = price * quantity
        cash = self._get_cash()

        if side == "buy":
            if cost > cash:
                raise ValueError(
                    f"Insufficient cash: need ${cost:,.2f} but only ${cash:,.2f} available"
                )
            self._set_cash(cash - cost)
            self._update_position_on_buy(ticker, quantity, price)
        else:
            self._update_position_on_sell(ticker, quantity, price)
            self._set_cash(cash + cost)

        now = _now_iso()
        order = Order(
            id=str(uuid4()),
            ticker=ticker,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            status="filled",
            filled_price=price,
            filled_at=now,
            created_at=now,
        )
        self._persist_order(order)
        logger.info(
            "Mock %s %d %s @ $%.2f (order %s)",
            side, quantity, ticker, price, order.id,
        )
        return order

    def _persist_order(self, order: Order) -> None:
        con = self._connect()
        try:
            con.execute(
                """
                INSERT INTO orders (id, ticker, side, quantity, order_type,
                                    limit_price, status, filled_price,
                                    filled_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.id,
                    order.ticker,
                    order.side,
                    order.quantity,
                    order.order_type,
                    order.limit_price,
                    order.status,
                    order.filled_price,
                    order.filled_at,
                    order.created_at,
                ),
            )
            con.commit()
        finally:
            con.close()

    def _update_position_on_buy(
        self, ticker: str, quantity: int, price: float
    ) -> None:
        con = self._connect()
        try:
            row = con.execute(
                "SELECT quantity, avg_cost FROM positions WHERE ticker = ?",
                (ticker,),
            ).fetchone()
            if row is None:
                con.execute(
                    "INSERT INTO positions (ticker, quantity, avg_cost) VALUES (?, ?, ?)",
                    (ticker, quantity, price),
                )
            else:
                existing_qty, existing_avg = row
                new_qty = existing_qty + quantity
                new_avg = (existing_avg * existing_qty + price * quantity) / new_qty
                con.execute(
                    "UPDATE positions SET quantity = ?, avg_cost = ? WHERE ticker = ?",
                    (new_qty, new_avg, ticker),
                )
            con.commit()
        finally:
            con.close()

    def _update_position_on_sell(
        self, ticker: str, quantity: int, price: float  # noqa: ARG002
    ) -> None:
        con = self._connect()
        try:
            row = con.execute(
                "SELECT quantity FROM positions WHERE ticker = ?", (ticker,)
            ).fetchone()
            if row is None or row[0] < quantity:
                raise ValueError(
                    f"Cannot sell {quantity} shares of {ticker}: "
                    f"only {row[0] if row else 0} held"
                )
            new_qty = row[0] - quantity
            if new_qty == 0:
                con.execute("DELETE FROM positions WHERE ticker = ?", (ticker,))
            else:
                con.execute(
                    "UPDATE positions SET quantity = ? WHERE ticker = ?",
                    (new_qty, ticker),
                )
            con.commit()
        finally:
            con.close()

    def _mock_get_positions(self) -> list[Position]:
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT ticker, quantity, avg_cost, sector FROM positions"
            ).fetchall()
        finally:
            con.close()

        positions: list[Position] = []
        for ticker, quantity, avg_cost, sector in rows:
            try:
                price = _current_price(ticker)
            except Exception:
                logger.warning("Could not fetch price for %s; using avg_cost", ticker)
                price = avg_cost
            market_value = price * quantity
            unrealized_pnl = (price - avg_cost) * quantity
            positions.append(
                Position(
                    ticker=ticker,
                    quantity=quantity,
                    avg_cost=avg_cost,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    sector=sector,
                )
            )
        return positions

    def _mock_get_portfolio(self) -> Portfolio:
        cash = self._get_cash()
        positions = self._mock_get_positions()
        total_equity = cash + sum(p.market_value for p in positions)
        return Portfolio(
            total_equity=total_equity,
            cash=cash,
            positions=positions,
            timestamp=_now_iso(),
        )

    def _mock_get_order_history(self, limit: int) -> list[Order]:
        con = self._connect()
        try:
            rows = con.execute(
                """
                SELECT id, ticker, side, quantity, order_type, limit_price,
                       status, filled_price, filled_at, created_at
                FROM orders
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            con.close()

        return [
            Order(
                id=r[0],
                ticker=r[1],
                side=r[2],
                quantity=r[3],
                order_type=r[4],
                limit_price=r[5],
                status=r[6],
                filled_price=r[7],
                filled_at=r[8],
                created_at=r[9],
            )
            for r in rows
        ]

    # -- Alpaca implementations ---------------------------------------------

    def _alpaca_submit_order(
        self,
        ticker: str,
        side: str,
        quantity: int,
        order_type: str,
        limit_price: float | None,
    ) -> Order:
        kwargs: dict[str, object] = {
            "symbol": ticker,
            "qty": quantity,
            "side": side,
            "type": order_type,
            "time_in_force": "day",
        }
        if order_type == "limit" and limit_price is not None:
            kwargs["limit_price"] = limit_price

        alpaca_order = self._api.submit_order(**kwargs)  # type: ignore[arg-type]
        return Order(
            id=str(alpaca_order.id),
            ticker=str(alpaca_order.symbol),
            side=str(alpaca_order.side),
            quantity=int(alpaca_order.qty),
            order_type=str(alpaca_order.type),
            limit_price=float(alpaca_order.limit_price) if alpaca_order.limit_price else None,
            status=str(alpaca_order.status),
            filled_price=(
                float(alpaca_order.filled_avg_price)
                if alpaca_order.filled_avg_price else None
            ),
            filled_at=str(alpaca_order.filled_at) if alpaca_order.filled_at else None,
            created_at=str(alpaca_order.created_at),
        )

    def _alpaca_get_positions(self) -> list[Position]:
        alpaca_positions = self._api.list_positions()
        return [
            Position(
                ticker=str(p.symbol),
                quantity=int(p.qty),
                avg_cost=float(p.avg_entry_price),
                market_value=float(p.market_value),
                unrealized_pnl=float(p.unrealized_pl),
            )
            for p in alpaca_positions
        ]

    def _alpaca_get_portfolio(self) -> Portfolio:
        account = self._api.get_account()
        positions = self._alpaca_get_positions()
        return Portfolio(
            total_equity=float(account.equity),
            cash=float(account.cash),
            positions=positions,
            timestamp=_now_iso(),
        )

    def _alpaca_get_order_history(self, limit: int) -> list[Order]:
        alpaca_orders = self._api.list_orders(status="all", limit=limit)
        return [
            Order(
                id=str(o.id),
                ticker=str(o.symbol),
                side=str(o.side),
                quantity=int(o.qty),
                order_type=str(o.type),
                limit_price=float(o.limit_price) if o.limit_price else None,
                status=str(o.status),
                filled_price=float(o.filled_avg_price) if o.filled_avg_price else None,
                filled_at=str(o.filled_at) if o.filled_at else None,
                created_at=str(o.created_at),
            )
            for o in alpaca_orders
        ]
