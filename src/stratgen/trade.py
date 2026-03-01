"""Alpaca account status."""

import sys


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


def show_status(client) -> None:
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
# Command (called from cli.py)
# ---------------------------------------------------------------------------


def cmd_status() -> None:
    """Show Alpaca account status."""
    client = get_alpaca_client()
    show_status(client)
