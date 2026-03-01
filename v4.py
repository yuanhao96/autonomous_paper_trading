"""v4: Full autonomous loop over all strategy docs.

What's new vs v3:
- Auto-discover all strategy .md files under knowledge/strategies/
- Resume: saves results after each doc, skips already-processed on restart
- Leaderboard: ranks passing strategies by Sharpe ratio
- Default to all strategies: run with no args

Usage:
    python v4.py                          # run all strategy docs (auto-resumes)
    python v4.py --reset                  # start fresh, ignore previous results
    python v4.py --provider anthropic     # use Anthropic instead of OpenAI
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from v3 import evaluate, print_summary, run_one

STRATEGIES_DIR = Path(__file__).parent / "knowledge" / "strategies"
RESULTS_FILE = Path(__file__).parent / "results_v4.json"


# ---------------------------------------------------------------------------
# Discover strategy docs
# ---------------------------------------------------------------------------


def collect_all_strategy_docs() -> list[str]:
    """Recursively find all strategy .md files, excluding READMEs and TEMPLATE."""
    skip = {"readme.md", "template.md"}
    docs = []
    for md in sorted(STRATEGIES_DIR.rglob("*.md")):
        if md.name.lower() not in skip:
            docs.append(str(md))
    return docs


# ---------------------------------------------------------------------------
# Resume support
# ---------------------------------------------------------------------------


def load_results(path: Path) -> list[dict]:
    """Load existing results from JSON file."""
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def save_results(results: list[dict], path: Path) -> None:
    """Save results to JSON file."""
    with open(path, "w") as f:
        json.dump(results, f, indent=2, default=str)


def already_processed(results: list[dict]) -> set[str]:
    """Extract the set of knowledge_doc paths already processed."""
    return {r["knowledge_doc"] for r in results}


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


def print_leaderboard(results: list[dict]) -> None:
    """Print passing strategies ranked by Sharpe ratio."""
    passing = [
        r for r in results
        if r["verdict"] == "PASS" and r.get("stats") and r["stats"].get("Sharpe Ratio") is not None
    ]
    passing.sort(key=lambda r: r["stats"]["Sharpe Ratio"], reverse=True)

    print("\n")
    print("=" * 75)
    print("  LEADERBOARD — Passing Strategies by Sharpe Ratio")
    print("=" * 75)

    if not passing:
        print("  No passing strategies.")
        print("=" * 75)
        return

    print(f"  {'#':<4} {'Strategy':<36} {'Sharpe':>7} {'Return':>8} {'MaxDD':>8} {'Trades':>7}")
    print("-" * 75)

    for i, r in enumerate(passing, 1):
        name = (r["name"] or "?")[:35]
        stats = r["stats"]
        sharpe = stats.get("Sharpe Ratio", 0)
        ret = stats.get("Return [%]", 0)
        max_dd = stats.get("Max. Drawdown [%]", 0)
        trades = stats.get("# Trades", 0)
        print(f"  {i:<4} {name:<36} {sharpe:>7.2f} {ret:>7.1f}% {max_dd:>7.1f}% {trades:>7}")

    print("=" * 75)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="v4: autonomous loop — discover all strategy docs → spec → code → backtest → evaluate"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Start fresh, ignore previous results",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic"],
        default="openai",
        help="LLM provider (default: openai)",
    )
    args = parser.parse_args()

    # 1. Discover all strategy docs
    all_docs = collect_all_strategy_docs()
    print(f"Found {len(all_docs)} strategy docs under {STRATEGIES_DIR}\n")

    if not all_docs:
        print("No strategy docs found.")
        sys.exit(1)

    # 2. Load or reset results
    if args.reset:
        results: list[dict] = []
        print("Starting fresh (--reset).\n")
    else:
        results = load_results(RESULTS_FILE)
        if results:
            print(f"Loaded {len(results)} previous results from {RESULTS_FILE.name}")

    done = already_processed(results)
    remaining = [d for d in all_docs if d not in done]
    total = len(all_docs)

    if not remaining:
        print("All docs already processed. Use --reset to re-run.\n")
    else:
        print(f"{len(remaining)} docs remaining ({total - len(remaining)}/{total} already done).\n")

    # 3. Process remaining docs
    for i, doc in enumerate(remaining, 1):
        idx = total - len(remaining) + i
        print(f"\n{'#' * 75}")
        print(f"# [{idx}/{total}] {doc}")
        print(f"{'#' * 75}")

        result = run_one(doc, provider=args.provider)
        results.append(result)

        # Save after each doc for resume capability
        save_results(results, RESULTS_FILE)

        # Progress line
        verdict = result["verdict"] or "?"
        name = result["name"] or Path(doc).stem
        sharpe = ""
        if result.get("stats") and result["stats"].get("Sharpe Ratio") is not None:
            sharpe = f" (Sharpe {result['stats']['Sharpe Ratio']:.2f})"
        print(f"  >> [{idx}/{total}] {verdict}: {name}{sharpe}")

    # 4. Leaderboard + summary
    print_leaderboard(results)
    print_summary(results)

    # 5. Summary stats
    counts: dict[str, int] = {}
    for r in results:
        v = r["verdict"] or "UNKNOWN"
        counts[v] = counts.get(v, 0) + 1

    print(f"\nTotal: {len(results)} strategies processed")
    for v in ["PASS", "MARGINAL", "FAIL", "SKIPPED", "ERROR", "UNKNOWN"]:
        if v in counts:
            print(f"  {v}: {counts[v]}")

    print(f"\nResults saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
