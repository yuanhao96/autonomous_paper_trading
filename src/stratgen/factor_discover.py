"""Factor discovery loop: parse factor docs, generate code, backtest, evaluate."""

import json
import re
import sys
import traceback
from pathlib import Path

import pandas as pd
from backtesting import Backtest

from stratgen.core import (
    FactorSpec,
    download_data,
    evaluate,
    generate_factor_code,
    load_strategy,
)
from stratgen.paths import FACTORS_DIR, RESULTS_FACTORS


# ---------------------------------------------------------------------------
# Parse factor docs
# ---------------------------------------------------------------------------


def parse_factor_doc(path: Path) -> FactorSpec:
    """Parse a standardized factor .md file into a FactorSpec.

    No LLM needed — the format is deterministic.
    """
    text = path.read_text()

    # Name: from the H1 header "# WQ-NNN: Description"
    m = re.search(r"^# (.+)$", text, re.MULTILINE)
    name = m.group(1).strip() if m else path.stem

    # Formula: content between "## Formula" and next "##"
    m = re.search(r"## Formula\n(.+?)(?=\n## )", text, re.DOTALL)
    formula = m.group(1).strip() if m else ""

    # Interpretation
    m = re.search(r"## Interpretation\n(.+?)(?=\n## )", text, re.DOTALL)
    interpretation = m.group(1).strip() if m else ""

    # Parameters: parse the markdown table
    params: dict = {}
    param_ranges: dict = {}
    m = re.search(r"## Parameters\n(.+?)(?=\n## )", text, re.DOTALL)
    if m:
        param_text = m.group(1).strip()
        if param_text != "None":
            # Parse markdown table rows: | name | default | range |
            for row in re.finditer(
                r"\|\s*(\w+)\s*\|\s*([^|]+)\s*\|\s*\[([^\]]+)\]\s*\|", param_text
            ):
                pname = row.group(1).strip()
                default_str = row.group(2).strip()
                range_str = row.group(3).strip()

                # Parse default value
                try:
                    default: int | float | str = _parse_number(default_str)
                except ValueError:
                    default = default_str

                params[pname] = default

                # Parse range [low, high]
                range_parts = [r.strip() for r in range_str.split(",")]
                try:
                    param_ranges[pname] = [_parse_number(r) for r in range_parts]
                except ValueError:
                    param_ranges[pname] = range_parts

    # Category
    m = re.search(r"## Category\n(\w+)", text)
    category = m.group(1).strip() if m else ""

    # Source
    m = re.search(r"## Source\n(.+?)(?=\n## |\Z)", text, re.DOTALL)
    source = m.group(1).strip() if m else ""

    return FactorSpec(
        name=name,
        formula=formula,
        interpretation=interpretation,
        params=params,
        param_ranges=param_ranges,
        category=category,
        source=source,
        factor_ref=str(path),
    )


def _parse_number(s: str) -> int | float:
    """Parse a string as int or float."""
    s = s.strip()
    try:
        val = int(s)
        return val
    except ValueError:
        return float(s)


# ---------------------------------------------------------------------------
# Collect all factor docs
# ---------------------------------------------------------------------------


def collect_all_factors() -> list[Path]:
    """Find all factor .md files under FACTORS_DIR, excluding README."""
    if not FACTORS_DIR.exists():
        return []
    factors = []
    for md in sorted(FACTORS_DIR.rglob("*.md")):
        if md.name.lower() in {"readme.md", "template.md"}:
            continue
        factors.append(md)
    return factors


# ---------------------------------------------------------------------------
# Run one factor end-to-end
# ---------------------------------------------------------------------------


def run_one_factor(
    factor_path: Path, df: pd.DataFrame, provider: str,
) -> dict:
    """Run the full pipeline for one factor doc. Returns a result dict."""
    result: dict = {
        "factor_ref": str(factor_path),
        "name": None,
        "category": None,
        "formula": None,
        "verdict": None,
        "reasons": [],
        "error": None,
        "stats": None,
    }

    try:
        # Step 1: Parse factor doc (deterministic, no LLM)
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
        code = generate_factor_code(spec, provider=provider)
        result["code"] = code

        # Step 3: Load strategy
        strategy_cls = load_strategy(code)

        # Step 4: Backtest
        bt = Backtest(
            df, strategy_cls,
            cash=100_000, commission=0.001, exclusive_orders=True,
        )
        stats = bt.run()
        stats_dict = dict(stats)
        result["stats"] = {
            k: v for k, v in stats_dict.items() if _is_serializable(v)
        }

        # Print results
        n_trades = stats["# Trades"]
        if n_trades == 0:
            print("  ** ZERO TRADES — factor never triggered **")
        else:
            print(f"  Return: {stats['Return [%]']:.2f}%  "
                  f"Sharpe: {stats['Sharpe Ratio']:.2f}  "
                  f"MaxDD: {stats['Max. Drawdown [%]']:.2f}%  "
                  f"Trades: {n_trades}")

        # Step 5: Evaluate
        verdict, reasons = evaluate(stats_dict)
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


def _is_serializable(v: object) -> bool:
    try:
        json.dumps(v)
        return True
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Resume support
# ---------------------------------------------------------------------------


def load_results(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)  # type: ignore[no-any-return]


def save_results(results: list[dict], path: Path) -> None:
    with open(path, "w") as f:
        json.dump(results, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


def print_leaderboard(results: list[dict]) -> None:
    """Print passing factors ranked by Sharpe ratio."""
    passing = [
        r for r in results
        if r["verdict"] == "PASS"
        and r.get("stats")
        and r["stats"].get("Sharpe Ratio") is not None
    ]
    passing.sort(key=lambda r: r["stats"]["Sharpe Ratio"], reverse=True)

    print("\n" + "=" * 80)
    print("  FACTOR LEADERBOARD — Passing Factors by Sharpe Ratio")
    print("=" * 80)

    if not passing:
        print("  No passing factors.")
        print("=" * 80)
        return

    print(f"  {'#':<4} {'Factor':<40} {'Cat':<14} {'Sharpe':>7} {'Return':>8} {'Trades':>7}")
    print("-" * 80)

    for i, r in enumerate(passing, 1):
        name = (r["name"] or "?")[:39]
        cat = (r.get("category") or "?")[:13]
        s = r["stats"]
        sharpe = s.get("Sharpe Ratio", 0)
        ret = s.get("Return [%]", 0)
        trades = s.get("# Trades", 0)
        print(f"  {i:<4} {name:<40} {cat:<14} {sharpe:>7.2f} {ret:>7.1f}% {trades:>7}")

    print("=" * 80)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_factor_discover(provider: str = "openai", reset: bool = False) -> None:
    """Run the factor discovery loop over all factor docs."""
    # 1. Collect all factor docs
    all_factors = collect_all_factors()
    print(f"Found {len(all_factors)} factor docs under {FACTORS_DIR}\n")

    if not all_factors:
        print("No factor docs found. Create factors/ with .md files first.")
        sys.exit(1)

    # 2. Load or reset results
    if reset:
        results: list[dict] = []
        print("Starting fresh (--reset).\n")
    else:
        results = load_results(RESULTS_FACTORS)
        if results:
            print(f"Loaded {len(results)} previous results from {RESULTS_FACTORS.name}")

    done = {r["factor_ref"] for r in results}
    remaining = [f for f in all_factors if str(f) not in done]
    total = len(all_factors)

    if not remaining:
        print("All factors already processed. Use --reset to re-run.\n")
    else:
        print(f"{len(remaining)} factors remaining "
              f"({total - len(remaining)}/{total} already done).\n")

    # 3. Download data once (all factors use SPY daily)
    if remaining:
        df = download_data("SPY")

    # 4. Process remaining factors
    for i, factor_path in enumerate(remaining, 1):
        idx = total - len(remaining) + i
        print(f"\n{'#' * 80}")
        print(f"# [{idx}/{total}] {factor_path.name}")
        print(f"{'#' * 80}")

        result = run_one_factor(factor_path, df, provider=provider)
        results.append(result)

        # Save after each factor for resume
        save_results(results, RESULTS_FACTORS)

        # Progress line
        verdict = result["verdict"] or "?"
        name = result["name"] or factor_path.stem
        sharpe = ""
        if result.get("stats") and result["stats"].get("Sharpe Ratio") is not None:
            sharpe = f" (Sharpe {result['stats']['Sharpe Ratio']:.2f})"
        print(f"  >> [{idx}/{total}] {verdict}: {name}{sharpe}")

    # 5. Leaderboard + summary
    print_leaderboard(results)

    # Summary stats
    counts: dict[str, int] = {}
    for r in results:
        v = r["verdict"] or "UNKNOWN"
        counts[v] = counts.get(v, 0) + 1

    print(f"\nTotal: {len(results)} factors processed")
    for v in ["PASS", "MARGINAL", "FAIL", "ERROR", "UNKNOWN"]:
        if v in counts:
            print(f"  {v}: {counts[v]}")

    print(f"\nResults saved to {RESULTS_FACTORS}")
