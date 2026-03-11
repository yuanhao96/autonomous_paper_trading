"""Score command: compute IC-weighted composite alpha per stock."""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from stratgen.paths import RESULTS_FACTORS_OPT, RESULTS_SCORE, RESULTS_SCREEN
from stratgen.scorer import composite_alpha, compute_factor_panel
from stratgen.universe import download_universe


def run_score(
    universe: str = "sp500",
    min_verdict: str = "MARGINAL",
    ic_window: int = 60,
    top_n: int | None = None,
    weight_method: str = "sign",
    min_ic: float = 0.005,
) -> None:
    """Load screened tickers + optimized factors, compute composite alpha, save results."""
    # 1. Load screened tickers
    if not RESULTS_SCREEN.exists():
        print(f"ERROR: {RESULTS_SCREEN} not found. Run 'stratgen screen' first.")
        sys.exit(1)

    with open(RESULTS_SCREEN) as f:
        screen_data = json.load(f)
    tickers = screen_data["passing_tickers"]
    print(f"Screened tickers: {len(tickers)} (from {screen_data['universe']})\n")

    # 2. Load optimized factors
    if not RESULTS_FACTORS_OPT.exists():
        print(f"ERROR: {RESULTS_FACTORS_OPT} not found. Run 'stratgen optimize' first.")
        sys.exit(1)

    with open(RESULTS_FACTORS_OPT) as f:
        all_factors = json.load(f)

    # Filter by verdict
    valid_verdicts = {"PASS"} if min_verdict == "PASS" else {"PASS", "MARGINAL"}
    factors = [
        f for f in all_factors
        if f.get("test_verdict") in valid_verdicts and f.get("code")
    ]
    print(f"Optimized factors: {len(factors)} ({min_verdict}+ from {len(all_factors)} total)")

    if top_n is not None and top_n < len(factors):
        factors = factors[:top_n]
        print(f"Using top {top_n} factors")

    print()

    # 3. Download OHLCV for screened tickers
    print("Downloading universe data (cached Parquet)...")
    universe_data = download_universe(tickers)

    # 4. Compute factor panels
    print(f"\nComputing factor values across {len(universe_data)} tickers...")
    factor_panels: dict[str, pd.DataFrame] = {}
    for i, factor in enumerate(factors, 1):
        name = factor["name"]
        print(f"\n  [{i}/{len(factors)}] {name}")
        try:
            panel = compute_factor_panel(factor, universe_data)
            factor_panels[name] = panel
            n_valid = panel.notna().sum().sum()
            print(f"    OK: {panel.shape[0]} dates x {panel.shape[1]} tickers, "
                  f"{n_valid} valid values")
        except Exception as e:
            print(f"    SKIP: {e}")

    print(f"\n{len(factor_panels)} / {len(factors)} factors computed successfully.\n")

    if not factor_panels:
        print("ERROR: No factors produced valid panels. Cannot compute composite.")
        sys.exit(1)

    # 5. Build returns panel
    returns_panel = pd.DataFrame({
        t: df["Close"].pct_change()
        for t, df in universe_data.items()
    })

    # 6. Compute composite alpha
    print(f"Computing composite alpha (weight={weight_method}, min_ic={min_ic})...")
    composite, ic_summary = composite_alpha(
        factor_panels, returns_panel,
        ic_window=ic_window, min_ic=min_ic, weight_method=weight_method,
    )

    # 7. Rank stocks by latest composite score
    latest_date = composite.index[-1]
    latest_scores = composite.loc[latest_date].dropna().sort_values(ascending=False)

    print(f"\nComposite alpha computed: {composite.shape[0]} dates x {composite.shape[1]} tickers")
    print(f"Latest date: {latest_date.date()}\n")

    # 8. Save results
    results = {
        "universe": universe,
        "n_tickers": len(tickers),
        "n_factors_used": len(factor_panels),
        "n_factors_total": len(factors),
        "ic_window": ic_window,
        "min_verdict": min_verdict,
        "latest_date": str(latest_date.date()),
        "ic_summary": {
            name: round(ic, 6) for name, ic in
            sorted(ic_summary.items(), key=lambda x: abs(x[1]), reverse=True)
        },
        "top_stocks": [
            {"ticker": t, "score": round(float(s), 6)}
            for t, s in latest_scores.head(50).items()
        ],
        "bottom_stocks": [
            {"ticker": t, "score": round(float(s), 6)}
            for t, s in latest_scores.tail(10).items()
        ],
    }

    with open(RESULTS_SCORE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {RESULTS_SCORE}\n")

    # 9. Print summary
    print(f"{'=' * 70}")
    print("  SCORING RESULTS")
    print(f"{'=' * 70}")

    print(f"\n  Factors used: {len(factor_panels)} / {len(factors)}")
    print(f"  IC window: {ic_window} days")
    print(f"  Latest date: {latest_date.date()}")

    # Per-factor IC summary (top 10 by |IC|)
    print("\n  Top factors by |mean IC|:")
    sorted_ic = sorted(ic_summary.items(), key=lambda x: abs(x[1]), reverse=True)
    for name, ic in sorted_ic[:10]:
        direction = "+" if ic > 0 else "-"
        print(f"    {direction} IC={ic:+.4f}  {name}")

    # Overall IC stats
    ic_values = [v for v in ic_summary.values() if not np.isnan(v)]
    if ic_values:
        print(f"\n  Mean |IC| across factors: {np.mean(np.abs(ic_values)):.4f}")
        print(f"  Factors with |IC| > 0.01: "
              f"{sum(1 for v in ic_values if abs(v) > 0.01)} / {len(ic_values)}")

    # Top stocks
    print("\n  Top 20 stocks by composite alpha:")
    for i, (ticker, score) in enumerate(latest_scores.head(20).items(), 1):
        print(f"    {i:2d}. {ticker:6s}  {score:+.4f}")

    # Bottom 5
    print("\n  Bottom 5 stocks:")
    for ticker, score in latest_scores.tail(5).items():
        print(f"      {ticker:6s}  {score:+.4f}")

    print(f"\n{'=' * 70}")
