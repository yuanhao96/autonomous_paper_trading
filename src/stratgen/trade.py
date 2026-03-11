"""Alpaca paper trading: account status, rebalancing, order execution."""

from __future__ import annotations

import json
import math
import sys
from typing import Any


# ---------------------------------------------------------------------------
# Alpaca client
# ---------------------------------------------------------------------------


def get_alpaca_client():
    """Init Alpaca TradingClient from .env vars."""
    import os

    from alpaca.trading.client import TradingClient

    api_key = os.environ.get("ALPACA_API_KEY")
    secret_key = os.environ.get("ALPACA_SECRET_KEY")
    if not api_key or not secret_key:
        print("Error: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env")
        sys.exit(1)
    return TradingClient(api_key, secret_key, paper=True)


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------


def show_status(client: Any) -> None:
    """Print Alpaca account info and positions."""
    account = client.get_account()
    clock = client.get_clock()

    print("\n" + "=" * 55)
    print("  ALPACA ACCOUNT STATUS")
    print("=" * 55)
    print(f"  Equity:         ${float(account.equity):>12,.2f}")
    print(f"  Buying Power:   ${float(account.buying_power):>12,.2f}")
    print(f"  Cash:           ${float(account.cash):>12,.2f}")
    print(f"  Portfolio Value: ${float(account.portfolio_value):>12,.2f}")
    print(f"  Market Open:    {clock.is_open}")
    if not clock.is_open:
        print(f"  Next Open:      {clock.next_open}")

    positions = client.get_all_positions()
    if positions:
        print("-" * 55)
        print(f"  {'Symbol':<8} {'Qty':>8} {'Price':>10} {'Value':>12} {'P&L':>10}")
        print("-" * 55)
        for p in positions:
            print(f"  {p.symbol:<8} {float(p.qty):>8.0f} "
                  f"${float(p.current_price):>9.2f} "
                  f"${float(p.market_value):>11.2f} "
                  f"${float(p.unrealized_pl):>9.2f}")
    else:
        print("  No positions.")
    print("=" * 55)


# ---------------------------------------------------------------------------
# Rebalance computation (pure logic, no API calls)
# ---------------------------------------------------------------------------


def compute_rebalance_orders(
    target_weights: dict[str, float],
    equity: float,
    current_positions: dict[str, float],
    prices: dict[str, float],
    min_trade_value: float = 100.0,
) -> list[dict[str, Any]]:
    """Compute orders needed to rebalance from current to target weights.

    Args:
        target_weights: {ticker: weight} where weight is 0.0-1.0.
        equity: Total account equity in dollars.
        current_positions: {ticker: qty} of current holdings.
        prices: {ticker: current_price} for all relevant tickers.
        min_trade_value: Minimum trade value to bother executing.

    Returns:
        List of order dicts: [{"ticker": str, "side": "buy"|"sell", "qty": int}]
    """
    orders: list[dict[str, Any]] = []

    # All tickers involved (targets + current holdings)
    all_tickers = set(target_weights.keys()) | set(current_positions.keys())

    for ticker in sorted(all_tickers):
        target_weight = target_weights.get(ticker, 0.0)
        current_qty = current_positions.get(ticker, 0.0)
        price = prices.get(ticker)

        if price is None or price <= 0:
            continue

        # Target shares (round down for buys)
        target_value = target_weight * equity
        target_qty = math.floor(target_value / price)

        # Delta
        delta = target_qty - current_qty

        # Skip small trades
        trade_value = abs(delta * price)
        if trade_value < min_trade_value:
            continue

        if delta > 0:
            orders.append({"ticker": ticker, "side": "buy", "qty": int(delta)})
        elif delta < 0:
            orders.append({"ticker": ticker, "side": "sell", "qty": int(abs(delta))})

    return orders


# ---------------------------------------------------------------------------
# Order execution
# ---------------------------------------------------------------------------


def execute_orders(client: Any, orders: list[dict[str, Any]], dry_run: bool = False) -> None:
    """Submit orders to Alpaca.

    Args:
        client: Alpaca TradingClient.
        orders: List from compute_rebalance_orders().
        dry_run: If True, print orders without submitting.
    """
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest

    if not orders:
        print("  No orders to execute.")
        return

    # Execute sells first (free up cash), then buys
    sells = [o for o in orders if o["side"] == "sell"]
    buys = [o for o in orders if o["side"] == "buy"]

    for order in sells + buys:
        side = OrderSide.BUY if order["side"] == "buy" else OrderSide.SELL
        label = "BUY" if order["side"] == "buy" else "SELL"

        if dry_run:
            print(f"  [DRY RUN] {label:4s} {order['qty']:>5d} {order['ticker']}")
            continue

        try:
            req = MarketOrderRequest(
                symbol=order["ticker"],
                qty=order["qty"],
                side=side,
                time_in_force=TimeInForce.DAY,
            )
            result = client.submit_order(req)
            print(f"  {label:4s} {order['qty']:>5d} {order['ticker']} — "
                  f"order {result.id} ({result.status})")
        except Exception as e:
            print(f"  ERROR {label} {order['ticker']}: {e}")


# ---------------------------------------------------------------------------
# Trade command
# ---------------------------------------------------------------------------


def cmd_trade(dry_run: bool = False) -> None:
    """Load allocation weights and rebalance Alpaca paper account."""
    from stratgen.paths import RESULTS_ALLOCATE

    # 1. Load allocation
    if not RESULTS_ALLOCATE.exists():
        print(f"ERROR: {RESULTS_ALLOCATE} not found. Run 'stratgen allocate' first.")
        sys.exit(1)

    with open(RESULTS_ALLOCATE) as f:
        alloc_data = json.load(f)

    target_weights = {p["ticker"]: p["weight"] for p in alloc_data["portfolio"]}
    print(f"Allocation: {len(target_weights)} positions from {alloc_data['latest_date']}")
    print(f"Total weight: {alloc_data['total_weight']:.2%}\n")

    # 2. Connect to Alpaca
    client = get_alpaca_client()
    account = client.get_account()
    equity = float(account.equity)
    print(f"Account equity: ${equity:,.2f}")

    # 3. Get current positions
    positions = client.get_all_positions()
    current_pos = {p.symbol: float(p.qty) for p in positions}
    print(f"Current positions: {len(current_pos)}\n")

    # 4. Get current prices for target tickers
    # Use latest trade prices from Alpaca
    all_tickers = set(target_weights.keys()) | set(current_pos.keys())

    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockLatestTradeRequest

    import os
    data_client = StockHistoricalDataClient(
        os.environ["ALPACA_API_KEY"], os.environ["ALPACA_SECRET_KEY"],
    )
    trades = data_client.get_stock_latest_trade(
        StockLatestTradeRequest(symbol_or_symbols=list(all_tickers)),
    )
    prices = {symbol: float(trade.price) for symbol, trade in trades.items()}

    # 5. Compute orders
    orders = compute_rebalance_orders(
        target_weights, equity, current_pos, prices,
    )

    # 6. Print order plan
    print(f"{'=' * 55}")
    print(f"  REBALANCE {'(DRY RUN)' if dry_run else 'ORDERS'}")
    print(f"{'=' * 55}")
    print(f"\n  Sells: {sum(1 for o in orders if o['side'] == 'sell')}")
    print(f"  Buys:  {sum(1 for o in orders if o['side'] == 'buy')}")
    print()

    # 7. Execute
    execute_orders(client, orders, dry_run=dry_run)

    # 8. Show updated status
    if not dry_run and orders:
        print("\nUpdated status:")
        show_status(client)


# ---------------------------------------------------------------------------
# Commands (called from cli.py)
# ---------------------------------------------------------------------------


def cmd_status() -> None:
    """Show Alpaca account status."""
    client = get_alpaca_client()
    show_status(client)
