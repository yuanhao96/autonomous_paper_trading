"""Allocate command: generate portfolio weights from composite alpha scores."""

from __future__ import annotations

import json
import sys

import pandas as pd

from stratgen.allocator import allocate_alpha_proportional
from stratgen.paths import RESULTS_ALLOCATE, RESULTS_FACTORS_OPT, RESULTS_SCREEN
from stratgen.scorer import composite_alpha, compute_factor_panel
from stratgen.universe import download_universe


def run_allocate(
    universe: str = "sp500",
    min_verdict: str = "MARGINAL",
    ic_window: int = 60,
    weight_method: str = "global_sign",
    min_ic: float = 0.01,
    top_n: int = 20,
    max_position: float = 0.05,
) -> None:
    """Compute composite alpha and generate portfolio allocation weights."""
    # 1. Load screened tickers
    if not RESULTS_SCREEN.exists():
        print(f"ERROR: {RESULTS_SCREEN} not found. Run 'stratgen screen' first.")
        sys.exit(1)

    with open(RESULTS_SCREEN) as f:
        screen_data = json.load(f)
    tickers = screen_data["passing_tickers"]
    print(f"Screened tickers: {len(tickers)}\n")

    # 2. Load optimized factors
    if not RESULTS_FACTORS_OPT.exists():
        print(f"ERROR: {RESULTS_FACTORS_OPT} not found. Run 'stratgen optimize' first.")
        sys.exit(1)

    with open(RESULTS_FACTORS_OPT) as f:
        all_factors = json.load(f)

    valid_verdicts = {"PASS"} if min_verdict == "PASS" else {"PASS", "MARGINAL"}
    factors = [
        f for f in all_factors
        if f.get("test_verdict") in valid_verdicts and f.get("code")
    ]
    print(f"Optimized factors: {len(factors)} ({min_verdict}+)\n")

    # 3. Download OHLCV
    print("Downloading universe data (cached Parquet)...")
    universe_data = download_universe(tickers)

    # 4. Compute factor panels
    print(f"\nComputing factor values across {len(universe_data)} tickers...")
    factor_panels: dict[str, pd.DataFrame] = {}
    for i, factor in enumerate(factors, 1):
        name = factor["name"]
        print(f"  [{i}/{len(factors)}] {name}")
        try:
            panel = compute_factor_panel(factor, universe_data)
            factor_panels[name] = panel
        except Exception as e:
            print(f"    SKIP: {e}")

    print(f"\n{len(factor_panels)} / {len(factors)} factors computed.\n")
    if not factor_panels:
        print("ERROR: No factors produced valid panels.")
        sys.exit(1)

    # 5. Build returns panel
    returns_panel = pd.DataFrame({
        t: df["Close"].pct_change()
        for t, df in universe_data.items()
    })

    # 6. Composite alpha
    print(f"Computing composite alpha (weight={weight_method}, min_ic={min_ic})...")
    composite, ic_summary = composite_alpha(
        factor_panels, returns_panel,
        ic_window=ic_window, min_ic=min_ic, weight_method=weight_method,
    )

    # 7. Get latest scores
    latest_date = composite.index[-1]
    latest_scores = composite.loc[latest_date].dropna()
    print(f"Latest date: {latest_date.date()}, {len(latest_scores)} stocks with scores\n")

    # 8. Allocate
    weights = allocate_alpha_proportional(
        latest_scores, top_n=top_n, max_position=max_position,
    )

    if weights.empty:
        print("WARNING: No stocks with positive alpha score. Empty portfolio.")
        weights = pd.Series(dtype=float)

    # 9. Save results
    results = {
        "universe": universe,
        "latest_date": str(latest_date.date()),
        "n_factors_used": len(factor_panels),
        "weight_method": weight_method,
        "min_ic": min_ic,
        "top_n": top_n,
        "max_position": max_position,
        "n_positions": len(weights),
        "total_weight": round(float(weights.sum()), 6),
        "portfolio": [
            {"ticker": t, "weight": round(float(w), 6), "alpha_score": round(float(latest_scores[t]), 6)}
            for t, w in weights.items()
        ],
    }

    with open(RESULTS_ALLOCATE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {RESULTS_ALLOCATE}\n")

    # 10. Print summary
    w = 70
    print(f"{'=' * w}")
    print("  PORTFOLIO ALLOCATION")
    print(f"{'=' * w}")
    print(f"\n  Positions: {len(weights)}")
    print(f"  Total weight: {weights.sum():.2%}")
    print(f"  Max position: {weights.max():.2%}" if not weights.empty else "")
    print(f"  Min position: {weights.min():.2%}" if not weights.empty else "")
    print(f"\n  {'Ticker':8s} {'Weight':>8s}  {'Alpha':>8s}")
    print(f"  {'-' * 30}")
    for ticker, weight in weights.items():
        alpha = latest_scores.get(ticker, 0.0)
        print(f"  {ticker:8s} {weight:>7.2%}  {alpha:>+8.4f}")
    print(f"\n{'=' * w}")
