"""v3: Automated evaluation with pass/fail thresholds.

What's new vs v2:
- Evaluate backtest results against thresholds (PASS / MARGINAL / FAIL)
- Accept multiple knowledge docs or a directory
- Summary table at the end
- Results saved to JSON

What's still manual: you pick which docs to feed it.

Usage:
    python v3.py knowledge/strategies/momentum/momentum-effect-in-stocks.md
    python v3.py knowledge/strategies/technical-and-other/          # all docs in dir
    python v3.py knowledge/strategies/momentum/ knowledge/strategies/calendar-anomalies/
    python v3.py knowledge/strategies/momentum/ --provider anthropic
"""

import argparse
import json
import sys
import traceback
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from core import (
    StrategySpec,
    download_data,
    evaluate,
    generate_strategy_code,
    load_strategy,
)
from v2 import extract_spec, run_backtest, validate_spec


# ---------------------------------------------------------------------------
# Run one strategy end-to-end
# ---------------------------------------------------------------------------


def run_one(knowledge_path: str, provider: str) -> dict:
    """Run the full pipeline for one knowledge doc. Returns a result dict."""
    result = {
        "knowledge_doc": knowledge_path,
        "name": None,
        "verdict": None,
        "reasons": [],
        "skipped": None,
        "error": None,
        "stats": None,
        "spec": None,
        "adaptations": [],
    }

    try:
        # Step 1: Extract spec
        spec = extract_spec(knowledge_path, provider=provider)
        result["name"] = spec.name
        result["spec"] = asdict(spec)
        result["adaptations"] = spec.adaptations

        if spec.skipped:
            result["verdict"] = "SKIPPED"
            result["skipped"] = spec.skipped
            print(f"\n** SKIPPED: {spec.name} — {spec.skipped}\n")
            return result

        # Print spec
        print(f"\n--- Spec: {spec.name} ---")
        print(f"  Ticker: {spec.universe}  Entry: {spec.entry_signal[:60]}...")
        if spec.adaptations:
            print(f"  Adaptations: {len(spec.adaptations)}")
        print()

        # Step 2: Validate spec
        errors = validate_spec(spec)
        if errors:
            result["verdict"] = "FAIL"
            result["reasons"] = [f"Validation: {e}" for e in errors]
            result["error"] = "spec_validation_failed"
            print(f"** Spec validation failed: {errors}\n")
            return result

        # Step 3: Generate code
        code = generate_strategy_code(spec, provider=provider)

        # Step 4: Load strategy
        strategy_cls = load_strategy(code)

        # Step 5: Backtest
        df = download_data(spec.universe[0])
        stats = run_backtest(strategy_cls, df, spec)
        result["stats"] = {k: v for k, v in stats.items() if _is_serializable(v)}

        # Step 6: Evaluate
        verdict, reasons = evaluate(stats)
        result["verdict"] = verdict
        result["reasons"] = reasons

        # Print verdict
        marker = {"PASS": "+", "MARGINAL": "~", "FAIL": "-"}[verdict]
        print(f"\n  [{marker}] {verdict}: {'; '.join(reasons)}\n")

    except Exception as e:
        result["verdict"] = "ERROR"
        result["error"] = str(e)
        result["reasons"] = [f"Exception: {e}"]
        print(f"\n** ERROR: {e}")
        traceback.print_exc()
        print()

    return result


def _is_serializable(v):
    """Check if a value is JSON-serializable."""
    try:
        json.dumps(v)
        return True
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Collect knowledge docs from args
# ---------------------------------------------------------------------------


def collect_docs(paths: list[str]) -> list[str]:
    """Expand directories into individual .md files, skip READMEs."""
    docs = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            for md in sorted(path.glob("*.md")):
                if md.name.lower() != "readme.md":
                    docs.append(str(md))
        elif path.is_file() and path.suffix == ".md":
            docs.append(str(path))
        else:
            print(f"Warning: skipping {p} (not a .md file or directory)")
    return docs


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def print_summary(results: list[dict]):
    """Print a summary table of all results."""
    print("\n")
    print("=" * 75)
    print("  SUMMARY")
    print("=" * 75)

    # Count by verdict
    counts = {}
    for r in results:
        v = r["verdict"] or "UNKNOWN"
        counts[v] = counts.get(v, 0) + 1

    for v in ["PASS", "MARGINAL", "FAIL", "SKIPPED", "ERROR"]:
        if v in counts:
            print(f"  {v}: {counts[v]}")

    print("-" * 75)
    print(f"  {'Strategy':<40} {'Verdict':<10} {'Sharpe':>7} {'Return':>8} {'Trades':>7}")
    print("-" * 75)

    for r in results:
        name = (r["name"] or r["knowledge_doc"])[:39]
        verdict = r["verdict"] or "?"
        stats = r.get("stats") or {}
        sharpe = stats.get("Sharpe Ratio")
        ret = stats.get("Return [%]")
        trades = stats.get("# Trades")

        sharpe_str = f"{sharpe:>7.2f}" if sharpe is not None else "    n/a"
        ret_str = f"{ret:>7.1f}%" if ret is not None else "     n/a"
        trades_str = f"{trades:>7}" if trades is not None else "    n/a"

        print(f"  {name:<40} {verdict:<10} {sharpe_str} {ret_str} {trades_str}")

    print("=" * 75)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="v3: knowledge doc → spec → code → backtest → evaluate"
    )
    parser.add_argument(
        "knowledge_docs",
        nargs="+",
        help="Knowledge doc path(s) or director(ies)",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic"],
        default="openai",
        help="LLM provider (default: openai)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Save results to JSON file (default: results_YYYYMMDD_HHMMSS.json)",
    )
    args = parser.parse_args()

    docs = collect_docs(args.knowledge_docs)
    if not docs:
        print("No knowledge docs found.")
        sys.exit(1)

    print(f"Found {len(docs)} knowledge doc(s) to process.\n")

    results = []
    for i, doc in enumerate(docs, 1):
        print(f"\n{'#' * 75}")
        print(f"# [{i}/{len(docs)}] {doc}")
        print(f"{'#' * 75}")
        result = run_one(doc, provider=args.provider)
        results.append(result)

    # Summary
    print_summary(results)

    # Save results
    output_path = args.output or f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
