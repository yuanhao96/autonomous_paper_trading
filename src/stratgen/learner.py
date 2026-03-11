"""Autonomous learning loop: chain screen → score → allocate, log runs, tune params."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from stratgen.paths import (
    RESULTS_ALLOCATE,
    RESULTS_FACTORS_OPT,
    RESULTS_SCORE,
    RESULTS_SCREEN,
    RUNS_DIR,
)


# ---------------------------------------------------------------------------
# Run logging
# ---------------------------------------------------------------------------


def log_run(summary: dict, run_dir: Path | None = None) -> Path:
    """Save current result files + summary to a timestamped run directory.

    Returns the path to the run directory.
    """
    if run_dir is None:
        ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        run_dir = RUNS_DIR / ts

    run_dir.mkdir(parents=True, exist_ok=True)

    # Copy result files
    for src in [RESULTS_SCREEN, RESULTS_SCORE, RESULTS_ALLOCATE]:
        if src.exists():
            shutil.copy2(src, run_dir / src.name)

    # Write summary
    with open(run_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return run_dir


def load_previous_runs() -> list[dict]:
    """Load summaries from all previous runs, sorted oldest-first."""
    if not RUNS_DIR.exists():
        return []

    runs = []
    for summary_path in sorted(RUNS_DIR.glob("*/summary.json")):
        with open(summary_path) as f:
            runs.append(json.load(f))
    return runs


# ---------------------------------------------------------------------------
# Quick scoring (for tune_screen — no file I/O, minimal printing)
# ---------------------------------------------------------------------------


def _quick_composite_ic(
    tickers: list[str],
    universe_data: dict[str, pd.DataFrame],
    factors: list[dict],
    weight_method: str = "global_sign",
    min_ic: float = 0.01,
    ic_window: int = 60,
) -> float:
    """Compute mean |IC| of composite alpha for a given ticker set.

    Returns mean absolute IC across factors, or 0.0 if computation fails.
    """
    from stratgen.scorer import composite_alpha, compute_factor_panel

    # Filter universe to these tickers
    subset = {t: df for t, df in universe_data.items() if t in tickers}
    if len(subset) < 20:
        return 0.0

    # Compute factor panels
    factor_panels: dict[str, pd.DataFrame] = {}
    for factor in factors:
        try:
            panel = compute_factor_panel(factor, subset)
            factor_panels[factor["name"]] = panel
        except Exception:
            continue

    if not factor_panels:
        return 0.0

    # Build returns panel
    returns_panel = pd.DataFrame({
        t: df["Close"].pct_change() for t, df in subset.items()
    })

    # Composite alpha
    try:
        _, ic_summary = composite_alpha(
            factor_panels, returns_panel,
            ic_window=ic_window, min_ic=min_ic, weight_method=weight_method,
        )
    except Exception:
        return 0.0

    ic_values = [v for v in ic_summary.values() if not np.isnan(v)]
    return float(np.mean(np.abs(ic_values))) if ic_values else 0.0


def tune_screen(
    universe_data: dict[str, pd.DataFrame],
    factors: list[dict],
    min_adv_grid: list[float] | None = None,
    weight_method: str = "global_sign",
    min_ic: float = 0.01,
    ic_window: int = 60,
    min_price: float = 10.0,
    min_completeness: float = 0.95,
    min_history_days: int = 504,
) -> dict:
    """Try multiple min_adv values, return the one with best composite |IC|.

    Returns dict with best_min_adv, results per grid point, and best IC.
    """
    from stratgen.screener import screen_universe

    if min_adv_grid is None:
        min_adv_grid = [1_000_000, 5_000_000, 10_000_000]

    results = []
    for min_adv in min_adv_grid:
        passing, _ = screen_universe(
            universe_data,
            min_adv=min_adv,
            min_price=min_price,
            min_completeness=min_completeness,
            min_history_days=min_history_days,
        )
        print(f"  min_adv=${min_adv:,.0f}: {len(passing)} tickers pass", end="")

        if len(passing) < 20:
            print(" — too few, skipping")
            results.append({"min_adv": min_adv, "n_pass": len(passing), "mean_ic": 0.0})
            continue

        mean_ic = _quick_composite_ic(
            passing, universe_data, factors,
            weight_method=weight_method, min_ic=min_ic, ic_window=ic_window,
        )
        print(f", mean |IC|={mean_ic:.4f}")
        results.append({"min_adv": min_adv, "n_pass": len(passing), "mean_ic": mean_ic})

    # Pick best by mean |IC|
    best = max(results, key=lambda x: x["mean_ic"])
    return {
        "grid_results": results,
        "best_min_adv": best["min_adv"],
        "best_mean_ic": best["mean_ic"],
        "best_n_pass": best["n_pass"],
    }


# ---------------------------------------------------------------------------
# Main learn command
# ---------------------------------------------------------------------------


def run_learn(
    universe: str = "sp500",
    weight_method: str = "global_sign",
    min_ic: float = 0.01,
    ic_window: int = 60,
    min_verdict: str = "MARGINAL",
    top_n: int = 20,
    max_position: float = 0.05,
    tune_screen_flag: bool = False,
    do_trade: bool = False,
    dry_run: bool = False,
) -> dict:
    """Run the full learning pipeline: screen → score → allocate, log results."""
    from stratgen.factor_allocate import run_allocate
    from stratgen.factor_screen import run_screen
    from stratgen.factor_score import run_score

    print("=" * 70)
    print("  AUTONOMOUS LEARNING LOOP")
    print("=" * 70)

    summary: dict = {
        "timestamp": datetime.now().isoformat(),
        "universe": universe,
        "weight_method": weight_method,
        "min_ic": min_ic,
        "ic_window": ic_window,
    }

    # --- Optional: tune screening params ---
    screen_min_adv = 5_000_000  # default

    if tune_screen_flag:
        print("\n--- Tuning screening parameters ---\n")

        # Load factors for quick scoring
        if not RESULTS_FACTORS_OPT.exists():
            print(f"WARNING: {RESULTS_FACTORS_OPT} not found. Skipping tune.")
        else:
            with open(RESULTS_FACTORS_OPT) as f:
                all_factors = json.load(f)
            valid_verdicts = {"PASS"} if min_verdict == "PASS" else {"PASS", "MARGINAL"}
            factors = [
                f for f in all_factors
                if f.get("test_verdict") in valid_verdicts and f.get("code")
            ]

            # Download universe data once
            from stratgen.universe import download_universe, get_universe_tickers
            tickers = get_universe_tickers(universe)
            print(f"Downloading {universe} data ({len(tickers)} tickers)...")
            universe_data = download_universe(tickers)

            tune_result = tune_screen(
                universe_data, factors,
                weight_method=weight_method, min_ic=min_ic, ic_window=ic_window,
            )
            screen_min_adv = tune_result["best_min_adv"]
            summary["tune_screen"] = tune_result
            print(f"\n  Best: min_adv=${screen_min_adv:,.0f} "
                  f"(IC={tune_result['best_mean_ic']:.4f}, "
                  f"{tune_result['best_n_pass']} stocks)\n")

    # --- Step 1: Screen ---
    print("\n--- Step 1: Screen ---\n")
    run_screen(universe=universe, min_adv=screen_min_adv)

    # Read screen results for summary
    if RESULTS_SCREEN.exists():
        with open(RESULTS_SCREEN) as f:
            screen_data = json.load(f)
        summary["n_screened"] = screen_data["n_passed"]
        summary["screen_min_adv"] = screen_min_adv

    # --- Step 2: Score ---
    print("\n--- Step 2: Score (IC-weighted composite alpha) ---\n")
    run_score(
        universe=universe, min_verdict=min_verdict,
        ic_window=ic_window, weight_method=weight_method, min_ic=min_ic,
    )

    # Read score results for summary
    if RESULTS_SCORE.exists():
        with open(RESULTS_SCORE) as f:
            score_data = json.load(f)
        ic_values = list(score_data.get("ic_summary", {}).values())
        summary["n_factors_used"] = score_data.get("n_factors_used", 0)
        summary["mean_abs_ic"] = round(float(np.mean(np.abs(ic_values))), 6) if ic_values else 0.0
        summary["latest_date"] = score_data.get("latest_date", "")

    # --- Step 3: Allocate ---
    print("\n--- Step 3: Allocate ---\n")
    run_allocate(
        universe=universe, min_verdict=min_verdict,
        ic_window=ic_window, weight_method=weight_method, min_ic=min_ic,
        top_n=top_n, max_position=max_position,
    )

    # Read allocate results for summary
    if RESULTS_ALLOCATE.exists():
        with open(RESULTS_ALLOCATE) as f:
            alloc_data = json.load(f)
        summary["n_positions"] = alloc_data.get("n_positions", 0)
        summary["total_weight"] = alloc_data.get("total_weight", 0.0)

    # --- Optional: Trade ---
    if do_trade:
        print("\n--- Step 4: Trade ---\n")
        from stratgen.trade import cmd_trade
        cmd_trade(dry_run=dry_run)
        summary["traded"] = True
        summary["trade_dry_run"] = dry_run

    # --- Log run ---
    run_dir = log_run(summary)
    print(f"\nRun logged to {run_dir}\n")

    # --- Compare with previous runs ---
    previous = load_previous_runs()
    if len(previous) > 1:
        prev = previous[-2]  # second-to-last (current is last)
        prev_ic = prev.get("mean_abs_ic", 0)
        curr_ic = summary.get("mean_abs_ic", 0)
        delta = curr_ic - prev_ic
        direction = "improved" if delta > 0 else "degraded" if delta < 0 else "unchanged"
        print(f"  IC vs previous run: {prev_ic:.4f} → {curr_ic:.4f} ({direction}, {delta:+.4f})")

    print(f"\n{'=' * 70}")
    print("  LEARNING LOOP COMPLETE")
    print(f"{'=' * 70}")

    return summary
