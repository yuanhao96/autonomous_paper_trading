"""Screen command: filter universe by liquidity, price, and data quality."""

from __future__ import annotations

import json
from dataclasses import asdict

from stratgen.paths import RESULTS_SCREEN
from stratgen.screener import screen_universe
from stratgen.universe import download_universe, get_universe_tickers


def run_screen(
    universe: str = "sp500",
    min_adv: float = 5_000_000,
    min_price: float = 10.0,
    min_completeness: float = 0.95,
    min_history_days: int = 504,
) -> None:
    """Download universe data, run screener, save results."""
    # 1. Get tickers
    tickers = get_universe_tickers(universe)
    print(f"Universe: {universe} ({len(tickers)} tickers)\n")

    # 2. Download data
    print("Downloading universe data (cached Parquet)...")
    universe_data = download_universe(tickers)

    # 3. Screen
    print("Screening...")
    passing, all_results = screen_universe(
        universe_data,
        min_adv=min_adv,
        min_price=min_price,
        min_completeness=min_completeness,
        min_history_days=min_history_days,
    )

    # 4. Save results
    results_dicts = [asdict(r) for r in all_results]
    with open(RESULTS_SCREEN, "w") as f:
        json.dump(
            {
                "universe": universe,
                "n_tickers": len(tickers),
                "n_downloaded": len(universe_data),
                "n_passed": len(passing),
                "filters": {
                    "min_adv": min_adv,
                    "min_price": min_price,
                    "min_completeness": min_completeness,
                    "min_history_days": min_history_days,
                },
                "passing_tickers": passing,
                "results": results_dicts,
            },
            f,
            indent=2,
        )
    print(f"\nResults saved to {RESULTS_SCREEN}\n")

    # 5. Print summary
    n_fail = len(all_results) - len(passing)
    print(f"{'=' * 60}")
    print(f"  SCREEN RESULTS: {len(passing)} passed, {n_fail} failed")
    print(f"{'=' * 60}")

    # Failure breakdown
    if n_fail > 0:
        reason_counts: dict[str, int] = {}
        for r in all_results:
            for reason in r.fail_reasons:
                # Extract reason type (first word before space)
                key = reason.split()[0]
                reason_counts[key] = reason_counts.get(key, 0) + 1

        print("\n  Failure reasons:")
        for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
            print(f"    {reason}: {count}")

    # Passing tickers (truncated if many)
    print(f"\n  Passing tickers ({len(passing)}):")
    for i in range(0, len(passing), 15):
        chunk = passing[i : i + 15]
        print(f"    {', '.join(chunk)}")

    print(f"\n{'=' * 60}")
