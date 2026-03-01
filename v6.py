"""v6: Paper trading — deploy winning strategies to Alpaca.

What's new vs v5:
- Takes top N PASS strategies from v5 (by test Sharpe)
- Runs backtest on recent data to extract current signal (LONG / FLAT)
- Reconciles positions in Alpaca paper account
- Submits market orders to reach desired allocation

Usage:
    python v6.py run                      # generate signals + submit orders
    python v6.py signals                  # show signals only, no trading
    python v6.py status                   # show Alpaca account + positions
    python v6.py run --top-n 3            # override strategy count
    python v6.py run --provider anthropic
    python v6.py run --v5-results path.json
"""

import argparse
import json
import math
import sys
import traceback
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from core import (
    download_data,
    generate_strategy_code,
    load_strategy,
    spec_from_dict,
)

load_dotenv()

DEFAULT_V5_RESULTS = Path(__file__).parent / "results_v5.json"
DEFAULT_V4_RESULTS = Path(__file__).parent / "results_v4.json"
RUNS_FILE = Path(__file__).parent / "runs_v6.json"
SIGNAL_DATA_START = "2024-01-01"
DEFAULT_TOP_N = 5


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
# Load top strategies from v5 + v4
# ---------------------------------------------------------------------------


def load_top_strategies(
    v5_path: str, v4_path: str, top_n: int,
) -> list[dict]:
    """Load top N PASS strategies from v5, cross-ref v4 for specs.

    Returns list of dicts with keys: name, knowledge_doc, spec (dict),
    optimized_params, test_sharpe.
    """
    # Load v5 results
    v5_results = json.loads(Path(v5_path).read_text())
    pass_strats = [
        r for r in v5_results
        if r.get("test_verdict") == "PASS"
        and r.get("test_stats")
        and r["test_stats"].get("Sharpe Ratio") is not None
    ]

    if not pass_strats:
        print("No PASS strategies found in v5 results.")
        return []

    # Sort by test Sharpe descending
    pass_strats.sort(
        key=lambda r: r["test_stats"]["Sharpe Ratio"], reverse=True,
    )

    # Load v4 results and index by knowledge_doc
    v4_results = json.loads(Path(v4_path).read_text())
    v4_by_doc = {r["knowledge_doc"]: r for r in v4_results if r.get("spec")}

    # Merge top N
    selected = []
    for r in pass_strats:
        doc = r["knowledge_doc"]
        v4 = v4_by_doc.get(doc)
        if v4 is None:
            print(f"  Warning: v5 strategy '{r['name']}' not found in v4 results, skipping")
            continue

        selected.append({
            "name": r["name"],
            "knowledge_doc": doc,
            "spec": v4["spec"],
            "optimized_params": r.get("optimized_params", {}),
            "test_sharpe": r["test_stats"]["Sharpe Ratio"],
        })
        if len(selected) >= top_n:
            break

    if len(selected) < top_n:
        print(f"  Warning: only {len(selected)} PASS strategies available (requested {top_n})")

    return selected


# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------


def extract_signal(
    spec_dict: dict, optimized_params: dict, provider: str,
) -> dict:
    """Backtest recent data with optimized params → LONG or FLAT signal.

    Returns dict with keys: ticker, signal, error, n_trades.
    """
    from backtesting import Backtest

    spec = spec_from_dict(spec_dict)
    # Override params with optimized values
    spec.params.update(optimized_params)
    ticker = spec.universe[0]

    result = {"ticker": ticker, "signal": "FLAT", "error": None, "n_trades": 0}

    try:
        # Generate and load strategy code
        code = generate_strategy_code(spec, provider=provider)
        strategy_cls = load_strategy(code)

        # Download recent data
        today = datetime.now().strftime("%Y-%m-%d")
        df = download_data(ticker, start=SIGNAL_DATA_START, end=today)

        if len(df) < 30:
            result["error"] = "insufficient_data"
            return result

        # Run backtest with optimized params
        bt = Backtest(
            df, strategy_cls, cash=100_000,
            commission=0.001, exclusive_orders=True,
        )
        stats = bt.run(**optimized_params)

        # Extract signal from trades
        trades = stats._trades
        result["n_trades"] = len(trades)

        if len(trades) == 0:
            result["signal"] = "FLAT"
        elif trades.iloc[-1]["ExitTime"] is None or (
            hasattr(trades.iloc[-1]["ExitTime"], "isoformat")
            and str(trades.iloc[-1]["ExitTime"]) == "NaT"
        ):
            # Last trade still open → LONG
            result["signal"] = "LONG"
        else:
            import pandas as pd
            exit_time = trades.iloc[-1]["ExitTime"]
            if pd.isna(exit_time):
                result["signal"] = "LONG"
            else:
                result["signal"] = "FLAT"

    except Exception as e:
        result["error"] = str(e)
        print(f"    Signal extraction error: {e}")
        traceback.print_exc()

    return result


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate_signals(
    signals: list[dict], equity: float, n_strategies: int,
) -> dict[str, float]:
    """Sum allocations per ticker. Returns {ticker: desired_dollars}."""
    per_strategy = equity / n_strategies
    desired: dict[str, float] = {}

    for s in signals:
        if s["signal"] == "LONG" and not s.get("error"):
            ticker = s["ticker"]
            desired[ticker] = desired.get(ticker, 0.0) + per_strategy

    return desired


# ---------------------------------------------------------------------------
# Position reconciliation
# ---------------------------------------------------------------------------


def get_current_positions(client) -> dict[str, dict]:
    """Get current Alpaca positions. Returns {symbol: {qty, market_value, current_price}}."""
    positions = client.get_all_positions()
    return {
        p.symbol: {
            "qty": float(p.qty),
            "market_value": float(p.market_value),
            "current_price": float(p.current_price),
        }
        for p in positions
    }


def reconcile_positions(
    desired: dict[str, float],
    current: dict[str, dict],
    client,
) -> list[dict]:
    """Compute orders to reach desired allocation.

    Returns list of order dicts: {symbol, side, qty, notional}.
    """
    import yfinance as yf

    orders = []

    # All tickers we care about (desired + currently held)
    all_tickers = set(desired.keys()) | set(current.keys())

    for symbol in sorted(all_tickers):
        desired_dollars = desired.get(symbol, 0.0)

        # Get current price
        if symbol in current:
            price = current[symbol]["current_price"]
            current_qty = current[symbol]["qty"]
        else:
            # Need to look up price for new positions
            try:
                ticker_info = yf.Ticker(symbol).fast_info
                price = ticker_info.get("lastPrice", 0)
            except Exception:
                print(f"    Warning: could not get price for {symbol}, skipping")
                continue
            current_qty = 0.0

        if price <= 0:
            print(f"    Warning: invalid price for {symbol}, skipping")
            continue

        desired_qty = math.floor(desired_dollars / price)
        delta = desired_qty - int(current_qty)

        if delta == 0:
            continue

        orders.append({
            "symbol": symbol,
            "side": "buy" if delta > 0 else "sell",
            "qty": abs(delta),
            "notional": abs(delta) * price,
        })

    return orders


# ---------------------------------------------------------------------------
# Order execution
# ---------------------------------------------------------------------------


def execute_orders(orders: list[dict], client) -> list[dict]:
    """Submit market orders to Alpaca. Returns list of order results."""
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest

    results = []
    for order in orders:
        try:
            req = MarketOrderRequest(
                symbol=order["symbol"],
                qty=order["qty"],
                side=OrderSide.BUY if order["side"] == "buy" else OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )
            resp = client.submit_order(req)
            results.append({
                "symbol": order["symbol"],
                "side": order["side"],
                "qty": order["qty"],
                "status": resp.status.value if resp.status else "submitted",
                "order_id": str(resp.id),
            })
            print(f"    {order['side'].upper()} {order['qty']} {order['symbol']}"
                  f" — {resp.status.value if resp.status else 'submitted'}")
        except Exception as e:
            results.append({
                "symbol": order["symbol"],
                "side": order["side"],
                "qty": order["qty"],
                "status": "error",
                "error": str(e),
            })
            print(f"    ERROR: {order['side']} {order['qty']} {order['symbol']} — {e}")

    return results


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
# Run log
# ---------------------------------------------------------------------------


def save_run_log(run: dict) -> None:
    """Append run to runs_v6.json."""
    runs = []
    if RUNS_FILE.exists():
        try:
            runs = json.loads(RUNS_FILE.read_text())
        except (json.JSONDecodeError, ValueError):
            runs = []
    runs.append(run)
    RUNS_FILE.write_text(json.dumps(runs, indent=2, default=str))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_status(args) -> None:
    """Show Alpaca account status."""
    client = get_alpaca_client()
    show_status(client)


def cmd_signals(args) -> None:
    """Generate signals only, no trading."""
    strategies = load_top_strategies(args.v5_results, args.v4_results, args.top_n)
    if not strategies:
        sys.exit(1)

    print(f"\nGenerating signals for top {len(strategies)} strategies...\n")

    signals = []
    for i, strat in enumerate(strategies, 1):
        print(f"[{i}/{len(strategies)}] {strat['name']} "
              f"(test Sharpe: {strat['test_sharpe']:.2f})")
        sig = extract_signal(strat["spec"], strat["optimized_params"], args.provider)
        sig["strategy"] = strat["name"]
        signals.append(sig)
        marker = "LONG" if sig["signal"] == "LONG" else "flat"
        err = f" (error: {sig['error']})" if sig.get("error") else ""
        print(f"    → {sig['ticker']}: {marker} ({sig['n_trades']} trades){err}\n")

    # Summary
    print("=" * 55)
    print("  SIGNAL SUMMARY")
    print("=" * 55)
    print(f"  {'Strategy':<35} {'Ticker':<8} {'Signal':<8}")
    print("-" * 55)
    for s in signals:
        name = (s.get("strategy") or "?")[:34]
        print(f"  {name:<35} {s['ticker']:<8} {s['signal']:<8}")
    n_long = sum(1 for s in signals if s["signal"] == "LONG")
    print("-" * 55)
    print(f"  LONG: {n_long} / {len(signals)}")
    print("=" * 55)


def cmd_run(args) -> None:
    """Generate signals and submit orders."""
    # 1. Init Alpaca
    client = get_alpaca_client()

    # 2. Check market clock
    clock = client.get_clock()
    if not clock.is_open:
        print(f"Warning: market is CLOSED. Orders will queue for next open "
              f"({clock.next_open}).\n")

    # 3. Get account equity
    account = client.get_account()
    equity = float(account.equity)
    print(f"Account equity: ${equity:,.2f}\n")

    # 4. Load top strategies
    strategies = load_top_strategies(args.v5_results, args.v4_results, args.top_n)
    if not strategies:
        sys.exit(1)

    n_strategies = len(strategies)
    per_strategy = equity / n_strategies
    print(f"Deploying {n_strategies} strategies, ${per_strategy:,.2f} each\n")

    # 5. Generate signals
    signals = []
    for i, strat in enumerate(strategies, 1):
        print(f"[{i}/{n_strategies}] {strat['name']} "
              f"(test Sharpe: {strat['test_sharpe']:.2f})")
        sig = extract_signal(strat["spec"], strat["optimized_params"], args.provider)
        sig["strategy"] = strat["name"]
        signals.append(sig)
        marker = "LONG" if sig["signal"] == "LONG" else "flat"
        err = f" (error: {sig['error']})" if sig.get("error") else ""
        print(f"    → {sig['ticker']}: {marker} ({sig['n_trades']} trades){err}\n")

    # 6. Aggregate
    desired = aggregate_signals(signals, equity, n_strategies)
    print("Desired allocations:")
    if desired:
        for ticker, dollars in sorted(desired.items()):
            print(f"  {ticker}: ${dollars:,.2f}")
    else:
        print("  (none — all signals FLAT)")
    print()

    # 7. Current positions
    current = get_current_positions(client)
    if current:
        print("Current positions:")
        for sym, pos in sorted(current.items()):
            print(f"  {sym}: {pos['qty']:.0f} shares @ ${pos['current_price']:.2f}")
        print()

    # 8. Reconcile
    orders = reconcile_positions(desired, current, client)
    if not orders:
        print("No orders needed — positions already aligned.\n")
    else:
        print(f"Orders to submit ({len(orders)}):")
        for o in orders:
            print(f"  {o['side'].upper()} {o['qty']} {o['symbol']} (~${o['notional']:,.2f})")
        print()

    # 9. Execute
    order_results = []
    if orders:
        print("Submitting orders...")
        order_results = execute_orders(orders, client)
        print()

    # 10. Summary + log
    run_log = {
        "timestamp": datetime.now().isoformat(),
        "strategies": [s["name"] for s in strategies],
        "signals": [
            {"ticker": s["ticker"], "strategy": s.get("strategy"), "signal": s["signal"]}
            for s in signals
        ],
        "orders": order_results,
        "account_equity": equity,
    }
    save_run_log(run_log)
    print(f"Run log saved to {RUNS_FILE}")

    # Final summary
    print("\n" + "=" * 55)
    print("  RUN SUMMARY")
    print("=" * 55)
    n_long = sum(1 for s in signals if s["signal"] == "LONG")
    n_flat = sum(1 for s in signals if s["signal"] == "FLAT")
    print(f"  Strategies: {n_strategies}")
    print(f"  Signals:    {n_long} LONG, {n_flat} FLAT")
    print(f"  Orders:     {len(order_results)} submitted")
    print(f"  Equity:     ${equity:,.2f}")
    print("=" * 55)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="v6: paper trading — deploy winning strategies to Alpaca",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="signals",
        choices=["run", "signals", "status"],
        help="Command to run (default: signals)",
    )
    parser.add_argument(
        "--top-n", type=int, default=DEFAULT_TOP_N,
        help=f"Number of top strategies to deploy (default: {DEFAULT_TOP_N})",
    )
    parser.add_argument(
        "--provider", choices=["openai", "anthropic"], default="openai",
        help="LLM provider for code generation (default: openai)",
    )
    parser.add_argument(
        "--v5-results", default=str(DEFAULT_V5_RESULTS),
        help="Path to v5 results JSON",
    )
    parser.add_argument(
        "--v4-results", default=str(DEFAULT_V4_RESULTS),
        help="Path to v4 results JSON",
    )
    args = parser.parse_args()

    if args.command == "status":
        cmd_status(args)
    elif args.command == "signals":
        cmd_signals(args)
    elif args.command == "run":
        cmd_run(args)


if __name__ == "__main__":
    main()
