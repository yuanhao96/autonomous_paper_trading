"""Factor signals: generate LONG/FLAT signals from top optimized factors."""

import json
import sys
import traceback
from pathlib import Path

import pandas as pd
from backtesting import Backtest

from stratgen.core import download_data, load_strategy
from stratgen.paths import RESULTS_FACTORS_OPT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_results(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------


def extract_signal(
    code: str,
    params: dict,
    df: pd.DataFrame,
) -> str:
    """Run backtest on recent data, return 'LONG' or 'FLAT'.

    If the last trade is still open at the end → LONG.
    Otherwise → FLAT.
    """
    strategy_cls = load_strategy(code)
    bt = Backtest(
        df, strategy_cls,
        cash=100_000, commission=0.001, exclusive_orders=True,
    )
    stats = bt.run(**params)
    trades = stats._trades  # noqa: SLF001

    if trades is None or len(trades) == 0:
        return "FLAT"

    last_trade = trades.iloc[-1]
    # backtesting.py: ExitTime is NaT if trade is still open
    if pd.isna(last_trade.get("ExitTime")):
        return "LONG"
    return "FLAT"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_factor_signals(top_n: int = 5) -> None:
    """Generate signals from top optimized factors."""
    # 1. Load optimized results
    opt_results = load_results(RESULTS_FACTORS_OPT)
    if not opt_results:
        print(f"No optimized results found at {RESULTS_FACTORS_OPT}.")
        print("Run 'python -m stratgen optimize' first.")
        sys.exit(1)

    # 2. Filter to PASS, sort by test Sharpe, take top N
    passing = [
        r for r in opt_results
        if r["test_verdict"] == "PASS"
        and r.get("test_stats")
        and r["test_stats"].get("Sharpe Ratio") is not None
        and r.get("code")
    ]
    passing.sort(key=lambda r: r["test_stats"]["Sharpe Ratio"], reverse=True)
    top = passing[:top_n]

    if not top:
        print("No passing factors found in optimized results.")
        sys.exit(0)

    print(f"Generating signals for top {len(top)} factors...\n")

    # 3. Download recent data
    df = download_data("SPY", start="2024-01-01")

    # 4. Generate signals
    signals: list[dict] = []
    for r in top:
        name = r["name"] or "?"
        category = r.get("category", "?")
        params = r.get("optimized_params", {})
        sharpe = r["test_stats"]["Sharpe Ratio"]

        print(f"  {name}...", end=" ", flush=True)

        try:
            signal = extract_signal(r["code"], params, df)
            signals.append({
                "name": name,
                "category": category,
                "signal": signal,
                "test_sharpe": sharpe,
                "optimized_params": params,
            })
            print(signal)
        except Exception as e:
            signals.append({
                "name": name,
                "category": category,
                "signal": "ERROR",
                "test_sharpe": sharpe,
                "optimized_params": params,
            })
            print(f"ERROR: {e}")
            traceback.print_exc()

    # 5. Print summary
    print("\n" + "=" * 70)
    print("  SIGNAL SUMMARY")
    print("=" * 70)
    print(f"  {'Factor':<35} {'Cat':<14} {'Signal':<8} {'Sharpe':>7}")
    print("-" * 70)

    for s in signals:
        name = s["name"][:34]
        cat = s["category"][:13]
        sig = s["signal"]
        sharpe = s["test_sharpe"]
        print(f"  {name:<35} {cat:<14} {sig:<8} {sharpe:>7.2f}")

    print("=" * 70)

    # Consensus
    long_count = sum(1 for s in signals if s["signal"] == "LONG")
    flat_count = sum(1 for s in signals if s["signal"] == "FLAT")
    err_count = sum(1 for s in signals if s["signal"] == "ERROR")
    print(f"\n  LONG: {long_count}  FLAT: {flat_count}  ERROR: {err_count}")

    if long_count > flat_count:
        print("  Consensus: LONG")
    elif flat_count > long_count:
        print("  Consensus: FLAT")
    else:
        print("  Consensus: MIXED")
