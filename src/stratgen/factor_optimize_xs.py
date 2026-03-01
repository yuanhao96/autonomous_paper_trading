"""Cross-sectional factor optimization: grid search params, score by |IC| on train."""

import sys
import traceback

import pandas as pd

from stratgen.core import load_xs_alpha
from stratgen.cross_section import (
    compute_information_coefficient,
    compute_monotonicity,
    evaluate_cross_sectional,
    form_portfolios,
    rank_cross_sectionally,
)
from stratgen.factor_discover import load_results, save_results
from stratgen.factor_optimize import build_param_grid
from stratgen.paths import RESULTS_FACTORS_XS, RESULTS_FACTORS_XS_OPT
from stratgen.universe import build_panel, download_universe, get_universe_tickers


# ---------------------------------------------------------------------------
# Score one param combo
# ---------------------------------------------------------------------------


def score_xs_factor(
    code: str,
    params: dict,
    universe_data: dict,
    returns_df: pd.DataFrame,
    n_groups: int,
) -> tuple[float, dict]:
    """Score one param combo. Returns (|mean_ic|, metrics_dict)."""
    compute_alpha = load_xs_alpha(code)
    alpha_df: pd.DataFrame = compute_alpha(universe_data, **params)

    # Rank and form portfolios
    alpha_ranks = rank_cross_sectionally(alpha_df)
    group_series = form_portfolios(alpha_ranks, returns_df, n_groups=n_groups)
    group_means = {
        g: float(s.mean()) if len(s) > 0 else 0.0
        for g, s in group_series.items()
    }

    # Long-short spread
    top_group = max(group_means.keys())
    bottom_group = min(group_means.keys())
    long_short_spread = group_means[top_group] - group_means[bottom_group]

    # IC
    mean_ic, ic_t_stat = compute_information_coefficient(alpha_df, returns_df)

    # Monotonicity
    monotonicity = compute_monotonicity(group_means)

    metrics = {
        "mean_ic": mean_ic,
        "ic_t_stat": ic_t_stat,
        "monotonicity": monotonicity,
        "long_short_spread": long_short_spread,
        "group_mean_returns": {str(k): v for k, v in group_means.items()},
        "n_groups": n_groups,
    }

    return abs(mean_ic), metrics


# ---------------------------------------------------------------------------
# Optimize one XS factor
# ---------------------------------------------------------------------------


def optimize_one_xs_factor(
    factor: dict,
    universe_data_train: dict,
    universe_data_test: dict,
    returns_train: pd.DataFrame,
    returns_test: pd.DataFrame,
    max_tries: int = 200,
    n_groups: int = 5,
) -> dict:
    """Grid search one XS factor's params on train, evaluate on test."""
    result: dict = {
        "factor_ref": factor["factor_ref"],
        "name": factor["name"],
        "category": factor.get("category"),
        "formula": factor.get("formula"),
        "code": factor.get("code"),
        "original_params": factor.get("params", {}),
        "param_ranges": factor.get("param_ranges", {}),
        "optimized_params": None,
        "train_metrics": None,
        "test_metrics": None,
        "test_verdict": None,
        "test_reasons": [],
        "error": None,
    }

    try:
        code = factor["code"]
        param_ranges = factor.get("param_ranges", {})

        # Build param grid
        grid = build_param_grid(param_ranges, max_tries)
        print(f"  Grid: {len(grid)} combos from {len(param_ranges)} params")

        # Grid search on train split — score by |IC|
        best_score = -1.0
        best_params: dict = {}
        best_train_metrics: dict = {}

        for combo in grid:
            try:
                score, metrics = score_xs_factor(
                    code, combo, universe_data_train, returns_train, n_groups,
                )
                if score > best_score:
                    best_score = score
                    best_params = combo
                    best_train_metrics = metrics
            except Exception:
                continue

        if not best_train_metrics:
            result["error"] = "all_combos_failed"
            result["test_verdict"] = "ERROR"
            result["test_reasons"] = ["All param combos failed on train set"]
            return result

        result["optimized_params"] = best_params
        result["train_metrics"] = best_train_metrics
        print(f"  Best train: |IC| {best_score:.4f}, params {best_params}")
        print(f"    IC {best_train_metrics['mean_ic']:.4f}, "
              f"t={best_train_metrics['ic_t_stat']:.2f}, "
              f"mono={best_train_metrics['monotonicity']:.2f}, "
              f"L/S={best_train_metrics['long_short_spread']:.6f}")

        # Evaluate best params on test split
        _, test_metrics = score_xs_factor(
            code, best_params, universe_data_test, returns_test, n_groups,
        )
        result["test_metrics"] = test_metrics

        # Verdict from test metrics
        verdict, reasons = evaluate_cross_sectional(
            test_metrics["mean_ic"],
            test_metrics["ic_t_stat"],
            test_metrics["monotonicity"],
            test_metrics["long_short_spread"],
        )
        result["test_verdict"] = verdict
        result["test_reasons"] = reasons

        print(f"  Test: IC {test_metrics['mean_ic']:.4f}, "
              f"t={test_metrics['ic_t_stat']:.2f}, "
              f"mono={test_metrics['monotonicity']:.2f}, "
              f"L/S={test_metrics['long_short_spread']:.6f}")

        marker = {"PASS": "+", "MARGINAL": "~", "FAIL": "-"}.get(verdict, "?")
        print(f"  [{marker}] {verdict}: {'; '.join(reasons)}")

    except Exception as e:
        result["test_verdict"] = "ERROR"
        result["error"] = str(e)
        result["test_reasons"] = [f"Exception: {e}"]
        print(f"  ** ERROR: {e}")
        traceback.print_exc()

    return result


# ---------------------------------------------------------------------------
# Pass-through for no-param factors
# ---------------------------------------------------------------------------


def passthrough_xs_factor(factor: dict) -> dict:
    """For factors with no param_ranges — carry forward analyze metrics as-is."""
    return {
        "factor_ref": factor["factor_ref"],
        "name": factor["name"],
        "category": factor.get("category"),
        "formula": factor.get("formula"),
        "code": factor.get("code"),
        "original_params": factor.get("params", {}),
        "param_ranges": {},
        "optimized_params": factor.get("params", {}),
        "train_metrics": None,
        "test_metrics": factor.get("metrics"),
        "test_verdict": factor["verdict"],
        "test_reasons": factor.get("reasons", []) + ["(no params — passthrough)"],
        "error": None,
    }


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


def print_xs_opt_leaderboard(results: list[dict]) -> None:
    """Print optimized XS factors ranked by test |IC|."""
    scored = [
        r for r in results
        if r.get("test_metrics")
        and r["test_metrics"].get("mean_ic") is not None
        and r["test_verdict"] != "ERROR"
    ]
    scored.sort(key=lambda r: abs(r["test_metrics"]["mean_ic"]), reverse=True)

    print("\n" + "=" * 90)
    print("  XS OPTIMIZED LEADERBOARD — Test Set Results by |IC|")
    print("=" * 90)

    if not scored:
        print("  No scored factors.")
        print("=" * 90)
        return

    print(f"  {'#':<4} {'Factor':<35} {'Verdict':<9} {'IC':>8} {'t-stat':>8} "
          f"{'Mono':>6} {'L/S':>10}")
    print("-" * 90)

    for i, r in enumerate(scored, 1):
        name = (r["name"] or "?")[:34]
        v = r["test_verdict"] or "?"
        m = r["test_metrics"]
        print(f"  {i:<4} {name:<35} {v:<9} {m['mean_ic']:>8.4f} "
              f"{m['ic_t_stat']:>8.2f} {m['monotonicity']:>6.2f} "
              f"{m['long_short_spread']:>10.6f}")

    print("=" * 90)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_factor_optimize_xs(
    reset: bool = False,
    max_tries: int = 200,
    n_groups: int = 5,
    universe: str = "sp100",
    train_end: str = "2022-12-31",
    test_start: str = "2023-01-01",
) -> None:
    """Run XS factor optimization. No LLM needed — uses cached code from analyze."""
    # 1. Load analyze results
    analyze_results = load_results(RESULTS_FACTORS_XS)
    if not analyze_results:
        print(f"No analyze results found at {RESULTS_FACTORS_XS}.")
        print("Run 'python -m stratgen analyze' first.")
        sys.exit(1)

    # 2. Filter to qualifying factors (PASS/MARGINAL with code)
    qualifying = []
    passthrough = []
    for r in analyze_results:
        if r.get("verdict") not in ("PASS", "MARGINAL"):
            continue
        if not r.get("code"):
            continue
        if r.get("param_ranges"):
            qualifying.append(r)
        else:
            passthrough.append(r)

    print(f"Analyze results: {len(analyze_results)} total")
    print(f"  Qualifying for optimization: {len(qualifying)} "
          f"(have params + PASS/MARGINAL)")
    print(f"  Passthrough (no params): {len(passthrough)}\n")

    if not qualifying and not passthrough:
        print("No factors to optimize.")
        sys.exit(0)

    # 3. Load or reset opt results
    if reset:
        opt_results: list[dict] = []
        print("Starting fresh (--reset).\n")
    else:
        opt_results = load_results(RESULTS_FACTORS_XS_OPT)
        if opt_results:
            print(f"Loaded {len(opt_results)} previous XS opt results.")

    done = {r["factor_ref"] for r in opt_results}

    # 4. Add passthrough factors (skip if already done)
    for r in passthrough:
        if r["factor_ref"] not in done:
            pt = passthrough_xs_factor(r)
            opt_results.append(pt)
            done.add(r["factor_ref"])
            print(f"  Passthrough: {r['name']}")

    remaining = [r for r in qualifying if r["factor_ref"] not in done]
    total = len(qualifying)

    if not remaining:
        print(f"\nAll {total} qualifying factors already optimized. "
              "Use --reset to re-run.\n")
    else:
        print(f"\n{len(remaining)} factors remaining "
              f"({total - len(remaining)}/{total} already done).\n")

    # 5. Download universe + split into train/test
    if remaining:
        tickers = get_universe_tickers(universe)
        print(f"Downloading universe data ({universe}: {len(tickers)} tickers)...")
        universe_data = download_universe(tickers)

        # Build returns panel and split by date
        returns_df = build_panel(universe_data, "Close").pct_change()

        returns_train = returns_df.loc[:train_end]  # type: ignore[misc]
        returns_test = returns_df.loc[test_start:]  # type: ignore[misc]

        # Split universe_data by date too
        universe_data_train: dict[str, pd.DataFrame] = {}
        universe_data_test: dict[str, pd.DataFrame] = {}
        for ticker, df in universe_data.items():
            universe_data_train[ticker] = df.loc[:train_end]  # type: ignore[misc]
            universe_data_test[ticker] = df.loc[test_start:]  # type: ignore[misc]

        print(f"Train: {len(returns_train)} bars "
              f"({returns_train.index[0].date()} to {returns_train.index[-1].date()})")
        print(f"Test:  {len(returns_test)} bars "
              f"({returns_test.index[0].date()} to {returns_test.index[-1].date()})\n")

    # 6. Optimize remaining factors
    for i, factor in enumerate(remaining, 1):
        idx = total - len(remaining) + i
        print(f"\n{'#' * 70}")
        print(f"# [{idx}/{total}] Optimizing XS: {factor['name']}")
        print(f"{'#' * 70}")

        result = optimize_one_xs_factor(
            factor, universe_data_train, universe_data_test,
            returns_train, returns_test,
            max_tries=max_tries, n_groups=n_groups,
        )
        opt_results.append(result)
        save_results(opt_results, RESULTS_FACTORS_XS_OPT)

    # 7. Leaderboard + summary
    print_xs_opt_leaderboard(opt_results)

    counts: dict[str, int] = {}
    for r in opt_results:
        v = r["test_verdict"] or "UNKNOWN"
        counts[v] = counts.get(v, 0) + 1

    print(f"\nTotal: {len(opt_results)} factors optimized")
    for v in ["PASS", "MARGINAL", "FAIL", "ERROR", "UNKNOWN"]:
        if v in counts:
            print(f"  {v}: {counts[v]}")

    print(f"\nResults saved to {RESULTS_FACTORS_XS_OPT}")
