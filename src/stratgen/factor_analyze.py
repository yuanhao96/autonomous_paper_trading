"""Cross-sectional factor analysis loop: parse docs, codegen, rank, evaluate."""

import sys
import traceback
from pathlib import Path

import pandas as pd

from stratgen.core import (
    generate_xs_factor_code,
    load_xs_alpha,
)
from stratgen.cross_section import (
    compute_information_coefficient,
    compute_monotonicity,
    evaluate_cross_sectional,
    form_portfolios,
    rank_cross_sectionally,
)
from stratgen.factor_discover import (
    load_results,
    parse_factor_doc,
    save_results,
)
from stratgen.paths import RESULTS_FACTORS_XS, XS_FACTORS_DIR
from stratgen.universe import build_panel, download_universe, SECTOR_ETFS


# ---------------------------------------------------------------------------
# Collect cross-sectional factor docs
# ---------------------------------------------------------------------------


def collect_xs_factors() -> list[Path]:
    """Find all factor .md files under XS_FACTORS_DIR."""
    if not XS_FACTORS_DIR.exists():
        return []
    factors = []
    for md in sorted(XS_FACTORS_DIR.rglob("*.md")):
        if md.name.lower() in {"readme.md", "template.md"}:
            continue
        factors.append(md)
    return factors


# ---------------------------------------------------------------------------
# Run one cross-sectional factor
# ---------------------------------------------------------------------------


def run_one_xs_factor(
    factor_path: Path,
    universe_data: dict,
    returns_df: "pd.DataFrame",
    provider: str,
    n_groups: int = 3,
) -> dict:
    """Run cross-sectional analysis for one factor doc. Returns result dict."""

    result: dict = {
        "factor_ref": str(factor_path),
        "name": None,
        "category": None,
        "formula": None,
        "verdict": None,
        "reasons": [],
        "error": None,
        "metrics": None,
    }

    try:
        # Step 1: Parse factor doc
        spec = parse_factor_doc(factor_path)
        result["name"] = spec.name
        result["category"] = spec.category
        result["formula"] = spec.formula
        result["params"] = spec.params
        result["param_ranges"] = spec.param_ranges

        if not spec.formula:
            result["verdict"] = "ERROR"
            result["error"] = "empty_formula"
            result["reasons"] = ["No formula found in factor doc"]
            print(f"  ** ERROR: No formula in {factor_path.name}")
            return result

        print(f"\n--- Factor: {spec.name} ---")
        print(f"  Formula: {spec.formula[:80]}...")
        print(f"  Category: {spec.category}")
        print()

        # Step 2: Generate code via LLM
        code = generate_xs_factor_code(spec, provider=provider)
        result["code"] = code

        # Step 3: Load compute_alpha function
        compute_alpha = load_xs_alpha(code)

        # Step 4: Compute alpha values
        alpha_df: pd.DataFrame = compute_alpha(universe_data, **spec.params)
        print(f"  Alpha shape: {alpha_df.shape} "
              f"({alpha_df.notna().sum().sum()} non-NaN values)")

        # Step 5: Rank cross-sectionally
        alpha_ranks = rank_cross_sectionally(alpha_df)

        # Step 6: Form portfolios and compute group returns
        group_series = form_portfolios(alpha_ranks, returns_df, n_groups=n_groups)
        group_means = {g: float(s.mean()) if len(s) > 0 else 0.0
                       for g, s in group_series.items()}

        # Long-short spread: top group minus bottom group
        top_group = max(group_means.keys())
        bottom_group = min(group_means.keys())
        long_short_spread = group_means[top_group] - group_means[bottom_group]

        # Step 7: Compute IC
        mean_ic, ic_t_stat = compute_information_coefficient(alpha_df, returns_df)

        # Step 8: Compute monotonicity
        monotonicity = compute_monotonicity(group_means)

        # Store metrics
        result["metrics"] = {
            "mean_ic": mean_ic,
            "ic_t_stat": ic_t_stat,
            "monotonicity": monotonicity,
            "long_short_spread": long_short_spread,
            "group_mean_returns": {str(k): v for k, v in group_means.items()},
            "n_groups": n_groups,
        }

        # Print results
        print(f"  IC: {mean_ic:.4f}  t-stat: {ic_t_stat:.2f}  "
              f"Mono: {monotonicity:.2f}  L/S: {long_short_spread:.6f}")
        for g in sorted(group_means.keys()):
            label = {1: "Bottom", n_groups: "Top"}.get(g, f"Mid-{g}")
            print(f"    Group {g} ({label}): {group_means[g]:.6f}")

        # Step 9: Evaluate
        verdict, reasons = evaluate_cross_sectional(
            mean_ic, ic_t_stat, monotonicity, long_short_spread,
        )
        result["verdict"] = verdict
        result["reasons"] = reasons

        marker = {"PASS": "+", "MARGINAL": "~", "FAIL": "-"}[verdict]
        print(f"  [{marker}] {verdict}: {'; '.join(reasons)}\n")

    except Exception as e:
        result["verdict"] = "ERROR"
        result["error"] = str(e)
        result["reasons"] = [f"Exception: {e}"]
        print(f"\n  ** ERROR: {e}")
        traceback.print_exc()
        print()

    return result


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


def print_xs_leaderboard(results: list[dict]) -> None:
    """Print factors ranked by |IC|."""
    scored = [
        r for r in results
        if r.get("metrics")
        and r["metrics"].get("mean_ic") is not None
        and r["verdict"] != "ERROR"
    ]
    scored.sort(key=lambda r: abs(r["metrics"]["mean_ic"]), reverse=True)

    print("\n" + "=" * 90)
    print("  CROSS-SECTIONAL FACTOR LEADERBOARD — Ranked by |IC|")
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
        v = r["verdict"] or "?"
        m = r["metrics"]
        print(f"  {i:<4} {name:<35} {v:<9} {m['mean_ic']:>8.4f} "
              f"{m['ic_t_stat']:>8.2f} {m['monotonicity']:>6.2f} "
              f"{m['long_short_spread']:>10.6f}")

    print("=" * 90)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_factor_analyze(
    provider: str = "openai",
    reset: bool = False,
    n_groups: int = 3,
) -> None:
    """Run cross-sectional factor analysis over all XS factor docs."""
    # 1. Collect factor docs
    all_factors = collect_xs_factors()
    print(f"Found {len(all_factors)} cross-sectional factor docs under {XS_FACTORS_DIR}\n")

    if not all_factors:
        print("No cross-sectional factor docs found.")
        print(f"Create docs in {XS_FACTORS_DIR}/ first.")
        sys.exit(1)

    # 2. Load or reset results
    if reset:
        results: list[dict] = []
        print("Starting fresh (--reset).\n")
    else:
        results = load_results(RESULTS_FACTORS_XS)
        if results:
            print(f"Loaded {len(results)} previous results from {RESULTS_FACTORS_XS.name}")

    done = {r["factor_ref"] for r in results}
    remaining = [f for f in all_factors if str(f) not in done]
    total = len(all_factors)

    if not remaining:
        print("All factors already processed. Use --reset to re-run.\n")
    else:
        print(f"{len(remaining)} factors remaining "
              f"({total - len(remaining)}/{total} already done).\n")

    # 3. Download universe data (cached Parquet)
    if remaining:
        print("Downloading universe data...")
        universe_data = download_universe(SECTOR_ETFS)

        # Build returns panel
        returns_df = build_panel(universe_data, "Close").pct_change()

    # 4. Process remaining factors
    for i, factor_path in enumerate(remaining, 1):
        idx = total - len(remaining) + i
        print(f"\n{'#' * 80}")
        print(f"# [{idx}/{total}] {factor_path.name}")
        print(f"{'#' * 80}")

        result = run_one_xs_factor(
            factor_path, universe_data, returns_df,
            provider=provider, n_groups=n_groups,
        )
        results.append(result)

        # Save after each factor for resume
        save_results(results, RESULTS_FACTORS_XS)

        # Progress line
        verdict = result["verdict"] or "?"
        name = result["name"] or factor_path.stem
        ic_str = ""
        if result.get("metrics") and result["metrics"].get("mean_ic") is not None:
            ic_str = f" (IC {result['metrics']['mean_ic']:.4f})"
        print(f"  >> [{idx}/{total}] {verdict}: {name}{ic_str}")

    # 5. Leaderboard + summary
    print_xs_leaderboard(results)

    # Summary stats
    counts: dict[str, int] = {}
    for r in results:
        v = r["verdict"] or "UNKNOWN"
        counts[v] = counts.get(v, 0) + 1

    print(f"\nTotal: {len(results)} factors processed")
    for v in ["PASS", "MARGINAL", "FAIL", "ERROR", "UNKNOWN"]:
        if v in counts:
            print(f"  {v}: {counts[v]}")

    print(f"\nResults saved to {RESULTS_FACTORS_XS}")
