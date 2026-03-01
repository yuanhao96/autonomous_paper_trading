"""Factor optimization: grid search params on train/test split."""

import itertools
import json
import sys
import traceback
from pathlib import Path

import pandas as pd
from backtesting import Backtest

from stratgen.core import download_data, evaluate, load_strategy
from stratgen.paths import RESULTS_FACTORS, RESULTS_FACTORS_OPT


# ---------------------------------------------------------------------------
# Param grid helpers
# ---------------------------------------------------------------------------


def build_param_grid(
    param_ranges: dict[str, list], max_tries: int = 200,
) -> list[dict]:
    """Build a grid of param combos from param_ranges.

    Each key maps to [low, high]. We generate integer steps between
    low and high, then take the cartesian product. If total combos
    exceed max_tries, we widen the step size until it fits.
    """
    if not param_ranges:
        return [{}]

    # Build per-param value lists
    axes: dict[str, list] = {}
    for name, bounds in param_ranges.items():
        if len(bounds) < 2:
            axes[name] = bounds
            continue
        low, high = bounds[0], bounds[1]
        if isinstance(low, int) and isinstance(high, int):
            axes[name] = list(range(low, high + 1))
        else:
            # Float params: 10 steps
            step = (high - low) / 10
            axes[name] = [low + step * i for i in range(11)]

    # Check total combos and coarsen if needed
    total = 1
    for vals in axes.values():
        total *= len(vals)

    if total > max_tries:
        # Iteratively thin each axis until under budget
        while total > max_tries:
            # Thin the longest axis by taking every other element
            longest_name = max(axes, key=lambda k: len(axes[k]))
            vals = axes[longest_name]
            if len(vals) <= 2:
                break
            axes[longest_name] = vals[::2]
            total = 1
            for v in axes.values():
                total *= len(v)

    # Cartesian product
    names = list(axes.keys())
    combos = []
    for combo_vals in itertools.product(*[axes[n] for n in names]):
        combos.append(dict(zip(names, combo_vals)))
    return combos[:max_tries]


# ---------------------------------------------------------------------------
# Resume helpers
# ---------------------------------------------------------------------------


def load_results(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)  # type: ignore[no-any-return]


def save_results(results: list[dict], path: Path) -> None:
    with open(path, "w") as f:
        json.dump(results, f, indent=2, default=str)


def _is_serializable(v: object) -> bool:
    try:
        json.dumps(v)
        return True
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Optimize one factor
# ---------------------------------------------------------------------------


def optimize_one_factor(
    factor: dict,
    df_train: pd.DataFrame,
    df_test: pd.DataFrame,
    max_tries: int = 200,
) -> dict:
    """Grid search one factor's params on train, evaluate on test."""
    result: dict = {
        "factor_ref": factor["factor_ref"],
        "name": factor["name"],
        "category": factor.get("category"),
        "formula": factor.get("formula"),
        "code": factor.get("code"),
        "original_params": factor.get("params", {}),
        "param_ranges": factor.get("param_ranges", {}),
        "optimized_params": None,
        "train_stats": None,
        "test_stats": None,
        "test_verdict": None,
        "test_reasons": [],
        "error": None,
    }

    try:
        code = factor["code"]
        param_ranges = factor.get("param_ranges", {})

        strategy_cls = load_strategy(code)

        # Build param grid
        grid = build_param_grid(param_ranges, max_tries)
        print(f"  Grid: {len(grid)} combos from {len(param_ranges)} params")

        # Grid search on train split
        best_sharpe = float("-inf")
        best_params: dict = {}
        best_train_stats: dict = {}

        for combo in grid:
            try:
                bt = Backtest(
                    df_train, strategy_cls,
                    cash=100_000, commission=0.001, exclusive_orders=True,
                )
                stats = bt.run(**combo)
                stats_dict = dict(stats)
                sharpe = stats_dict.get("Sharpe Ratio", float("-inf"))
                if sharpe is None or pd.isna(sharpe):
                    sharpe = float("-inf")
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_params = combo
                    best_train_stats = {
                        k: v for k, v in stats_dict.items() if _is_serializable(v)
                    }
            except Exception:
                continue

        if not best_train_stats:
            result["error"] = "all_combos_failed"
            result["test_verdict"] = "ERROR"
            result["test_reasons"] = ["All param combos failed on train set"]
            return result

        result["optimized_params"] = best_params
        result["train_stats"] = best_train_stats
        print(f"  Best train: Sharpe {best_sharpe:.2f}, params {best_params}")

        # Evaluate best params on test split
        bt_test = Backtest(
            df_test, strategy_cls,
            cash=100_000, commission=0.001, exclusive_orders=True,
        )
        test_stats = bt_test.run(**best_params)
        test_stats_dict = dict(test_stats)
        result["test_stats"] = {
            k: v for k, v in test_stats_dict.items() if _is_serializable(v)
        }

        # Evaluate
        verdict, reasons = evaluate(test_stats_dict)
        result["test_verdict"] = verdict
        result["test_reasons"] = reasons

        test_sharpe = test_stats_dict.get("Sharpe Ratio", 0)
        test_return = test_stats_dict.get("Return [%]", 0)
        n_trades = test_stats_dict.get("# Trades", 0)
        print(f"  Test: Sharpe {test_sharpe:.2f}, "
              f"Return {test_return:.1f}%, Trades {n_trades}")

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


def passthrough_factor(factor: dict) -> dict:
    """For factors with no params — carry forward discover stats as-is."""
    return {
        "factor_ref": factor["factor_ref"],
        "name": factor["name"],
        "category": factor.get("category"),
        "formula": factor.get("formula"),
        "code": factor.get("code"),
        "original_params": factor.get("params", {}),
        "param_ranges": {},
        "optimized_params": factor.get("params", {}),
        "train_stats": None,
        "test_stats": factor.get("stats"),
        "test_verdict": factor["verdict"],
        "test_reasons": factor.get("reasons", []) + ["(no params — passthrough)"],
        "error": None,
    }


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


def print_leaderboard(results: list[dict]) -> None:
    """Print optimized factors ranked by test Sharpe ratio."""
    passing = [
        r for r in results
        if r["test_verdict"] == "PASS"
        and r.get("test_stats")
        and r["test_stats"].get("Sharpe Ratio") is not None
    ]
    passing.sort(key=lambda r: r["test_stats"]["Sharpe Ratio"], reverse=True)

    print("\n" + "=" * 80)
    print("  OPTIMIZED FACTOR LEADERBOARD — Test Set Results by Sharpe")
    print("=" * 80)

    if not passing:
        print("  No passing factors on test set.")
        print("=" * 80)
        return

    header = (f"  {'#':<4} {'Factor':<35} {'Cat':<14} "
              f"{'Sharpe':>7} {'Return':>8} {'Trades':>7} {'Params'}")
    print(header)
    print("-" * 80)

    for i, r in enumerate(passing, 1):
        name = (r["name"] or "?")[:34]
        cat = (r.get("category") or "?")[:13]
        s = r["test_stats"]
        sharpe = s.get("Sharpe Ratio", 0)
        ret = s.get("Return [%]", 0)
        trades = s.get("# Trades", 0)
        params_str = str(r.get("optimized_params", {}))
        if len(params_str) > 30:
            params_str = params_str[:27] + "..."
        print(f"  {i:<4} {name:<35} {cat:<14} "
              f"{sharpe:>7.2f} {ret:>7.1f}% {trades:>7} {params_str}")

    print("=" * 80)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_factor_optimize(
    provider: str = "openai",
    reset: bool = False,
    max_tries: int = 200,
) -> None:
    """Run factor optimization over all passing discover results."""
    # 1. Load discover results
    discover_results = load_results(RESULTS_FACTORS)
    if not discover_results:
        print(f"No discover results found at {RESULTS_FACTORS}.")
        print("Run 'python -m stratgen discover' first.")
        sys.exit(1)

    # 2. Filter to qualifying factors
    qualifying = []
    passthrough = []
    for r in discover_results:
        if r["verdict"] not in ("PASS", "MARGINAL"):
            continue
        if not r.get("code"):
            continue
        if r.get("param_ranges"):
            qualifying.append(r)
        else:
            passthrough.append(r)

    print(f"Discover results: {len(discover_results)} total")
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
        opt_results = load_results(RESULTS_FACTORS_OPT)
        if opt_results:
            print(f"Loaded {len(opt_results)} previous opt results.")

    done = {r["factor_ref"] for r in opt_results}

    # 4. Add passthrough factors (skip if already done)
    for r in passthrough:
        if r["factor_ref"] not in done:
            pt = passthrough_factor(r)
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

    # 5. Download data + split
    if remaining:
        df = download_data("SPY", start="2020-01-01")
        train_end = "2023-12-31"
        df_train = df.loc[:train_end]  # type: ignore[misc]
        df_test = df.loc["2024-01-01":]  # type: ignore[misc]
        print(f"Train: {len(df_train)} bars "
              f"({df_train.index[0].date()} to {df_train.index[-1].date()})")
        print(f"Test:  {len(df_test)} bars "
              f"({df_test.index[0].date()} to {df_test.index[-1].date()})\n")

    # 6. Optimize remaining factors
    for i, factor in enumerate(remaining, 1):
        idx = total - len(remaining) + i
        print(f"\n{'#' * 70}")
        print(f"# [{idx}/{total}] Optimizing: {factor['name']}")
        print(f"{'#' * 70}")

        result = optimize_one_factor(factor, df_train, df_test, max_tries)
        opt_results.append(result)
        save_results(opt_results, RESULTS_FACTORS_OPT)

    # 7. Leaderboard + summary
    print_leaderboard(opt_results)

    counts: dict[str, int] = {}
    for r in opt_results:
        v = r["test_verdict"] or "UNKNOWN"
        counts[v] = counts.get(v, 0) + 1

    print(f"\nTotal: {len(opt_results)} factors optimized")
    for v in ["PASS", "MARGINAL", "FAIL", "ERROR", "UNKNOWN"]:
        if v in counts:
            print(f"  {v}: {counts[v]}")

    print(f"\nResults saved to {RESULTS_FACTORS_OPT}")
