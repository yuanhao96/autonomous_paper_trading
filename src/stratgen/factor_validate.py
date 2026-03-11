"""Validate command: evaluate composite alpha quality via quintile analysis."""

from __future__ import annotations

import json
import sys

import pandas as pd

from stratgen.paths import RESULTS_FACTORS_OPT, RESULTS_SCREEN, RESULTS_VALIDATE
from stratgen.scorer import composite_alpha, compute_factor_panel
from stratgen.universe import download_universe
from stratgen.validator import (
    compute_composite_ic,
    compute_quintile_stats,
    evaluate_composite,
    form_quintile_returns,
    multi_horizon_ic,
)


def run_validate(
    universe: str = "sp500",
    min_verdict: str = "MARGINAL",
    ic_window: int = 60,
    top_n: int | None = None,
    n_groups: int = 5,
    horizons: str = "1,5,10,20",
    weight_method: str = "sign",
    min_ic: float = 0.005,
) -> None:
    """Compute composite alpha and validate with quintile analysis + multi-horizon IC."""
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
            print(f"    OK: {panel.shape[0]} dates x {panel.shape[1]} tickers")
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
    print(f"Composite: {composite.shape[0]} dates x {composite.shape[1]} tickers\n")

    # 7. Quintile analysis (1-day horizon)
    print("Running quintile analysis...")
    quintile_rets = form_quintile_returns(composite, returns_panel, n_groups=n_groups, horizon=1)
    q_stats = compute_quintile_stats(quintile_rets)

    # 8. Composite IC (1-day)
    print("Computing composite IC...")
    ic_stats = compute_composite_ic(composite, returns_panel, horizon=1)

    # 9. Multi-horizon IC
    horizon_list = [int(h.strip()) for h in horizons.split(",")]
    print(f"Computing multi-horizon IC ({horizon_list})...")
    horizon_ics = multi_horizon_ic(composite, returns_panel, horizons=horizon_list)

    # 10. Evaluate
    verdict, reasons = evaluate_composite(ic_stats, q_stats)

    # 11. Save results
    results = {
        "universe": universe,
        "n_tickers": len(tickers),
        "n_factors_used": len(factor_panels),
        "ic_window": ic_window,
        "min_verdict": min_verdict,
        "composite_ic": ic_stats,
        "quintile_stats": q_stats,
        "multi_horizon_ic": {str(h): stats for h, stats in horizon_ics.items()},
        "per_factor_ic": {
            name: round(ic, 6) for name, ic in
            sorted(ic_summary.items(), key=lambda x: abs(x[1]), reverse=True)
        },
        "verdict": verdict,
        "reasons": reasons,
    }

    with open(RESULTS_VALIDATE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {RESULTS_VALIDATE}\n")

    # 12. Print report
    _print_report(ic_stats, q_stats, horizon_ics, ic_summary, verdict, reasons, n_groups)


def _print_report(
    ic_stats: dict,
    q_stats: dict,
    horizon_ics: dict,
    ic_summary: dict,
    verdict: str,
    reasons: list[str],
    n_groups: int,
) -> None:
    """Print formatted validation report."""
    w = 70
    print(f"{'=' * w}")
    print("  COMPOSITE ALPHA VALIDATION")
    print(f"{'=' * w}")

    # Verdict
    print(f"\n  Verdict: {verdict}")
    for r in reasons:
        print(f"    {r}")

    # Composite IC
    print("\n  Composite IC (1-day forward):")
    print(f"    Mean IC:      {ic_stats['mean_ic']:+.4f}")
    print(f"    IC Std:       {ic_stats['ic_std']:.4f}")
    print(f"    IC t-stat:    {ic_stats['ic_t_stat']:.2f}")
    print(f"    IC IR:        {ic_stats['ic_ir']:.4f}")
    print(f"    % Positive:   {ic_stats['pct_positive']:.1%}")
    print(f"    N days:       {ic_stats['n_days']}")

    # Quintile returns
    print("\n  Quintile returns (annualized):")
    for g in range(1, n_groups + 1):
        key = f"mean_return_q{g}"
        label = "Bottom" if g == 1 else ("Top" if g == n_groups else f"Q{g}")
        ret = q_stats.get(key, 0.0)
        print(f"    {label:8s} (Q{g}): {ret:+.2%}")
    print(f"    L/S spread:   {q_stats['long_short_spread_ann']:+.2%}")
    print(f"    Monotonicity: {q_stats['monotonicity']:.2f}")

    # Multi-horizon IC
    print("\n  Multi-horizon IC:")
    print(f"    {'Horizon':>8s}  {'Mean IC':>8s}  {'t-stat':>7s}  {'IR':>7s}  {'%Pos':>5s}")
    for h, stats in sorted(horizon_ics.items()):
        print(f"    {h:>5d}-day  {stats['mean_ic']:+.4f}  {stats['ic_t_stat']:>7.2f}"
              f"  {stats['ic_ir']:>7.4f}  {stats['pct_positive']:>5.1%}")

    # Top factors by |IC|
    sorted_ic = sorted(ic_summary.items(), key=lambda x: abs(x[1]), reverse=True)
    print("\n  Top 10 factors by |mean IC|:")
    for name, ic in sorted_ic[:10]:
        print(f"    IC={ic:+.4f}  {name}")

    print(f"\n{'=' * w}")
