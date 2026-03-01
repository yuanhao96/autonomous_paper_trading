"""v5: Parameter evolution — optimize strategy params via grid search.

What's new vs v4:
- Takes PASS/MARGINAL strategies from v4 results
- LLM extracts param ranges from knowledge docs (knowledge-constrained)
- Grid search optimization on train split (2020–2023H1)
- Out-of-sample evaluation on test split (2023H2–2025)
- Resume support: saves after each strategy

Usage:
    python v5.py                          # optimize all v4 PASS/MARGINAL (auto-resume)
    python v5.py --reset                  # start fresh
    python v5.py --provider anthropic     # use Anthropic instead of OpenAI
    python v5.py --v4-results path.json   # custom v4 results file
    python v5.py --max-tries 500          # increase grid search budget (default: 200)
"""

import argparse
import json
import math
import sys
import traceback
from pathlib import Path
from textwrap import dedent

from v2 import StrategySpec, download_data, generate_strategy_code, load_strategy
from v3 import evaluate

RESULTS_FILE = Path(__file__).parent / "results_v5.json"
DEFAULT_V4_RESULTS = Path(__file__).parent / "results_v4.json"
TRAIN_END = "2023-06-30"


# ---------------------------------------------------------------------------
# LLM: Extract param ranges from knowledge doc
# ---------------------------------------------------------------------------

PARAM_RANGES_SYSTEM_PROMPT = dedent("""\
    You are a trading strategy parameter analyst. Given a strategy knowledge document
    and its current default parameters, extract reasonable parameter ranges for
    grid search optimization.

    OUTPUT FORMAT — respond with ONLY a JSON object, no markdown, no explanation:
    {
        "param_ranges": {
            "param_name": [value1, value2, value3, ...]
        },
        "constraints": "lambda params: params['fast_period'] < params['slow_period']",
        "reasoning": "Brief explanation of range choices"
    }

    RULES:
    1. Only include NUMERIC parameters (int or float). Skip strings, booleans,
       calendar constants (month numbers, weekday numbers), and non-tunable params.
    2. Each parameter should have 3–7 discrete values to test.
    3. Ground ranges in the knowledge document when possible:
       - If the doc mentions "typically 10-30 day lookback", use [10, 15, 20, 25, 30]
       - If the doc tests multiple values, use those values
    4. If no range is documented for a param, use ±50% of the default with 5-7 steps:
       - Default 20 → [10, 14, 17, 20, 23, 26, 30]
       - Default 0.05 → [0.025, 0.035, 0.05, 0.065, 0.075]
    5. Integer params must have integer values. Float params can have float values.
    6. If a constraint exists between params (e.g., fast < slow), provide a
       constraint lambda string. Otherwise set constraints to null.
    7. If there are NO tunable numeric parameters, return:
       {"param_ranges": {}, "constraints": null, "reasoning": "..."}
    8. Do NOT include params like 'trade_month', 'exit_month', 'rebalance_weekday',
       'rebalance_frequency', 'rebalance_schedule', 'rebalance_day_rule',
       'rebalance_timing', etc. — these are structural, not tunable.
    9. Do NOT include boolean params like 'use_cash_when_bearish',
       'use_inverse_volatility_position_sizing', 'use_log_returns', etc.
""")


def _build_param_ranges_prompt(knowledge_text: str, spec_params: dict) -> str:
    return dedent(f"""\
        Extract parameter ranges for grid search optimization.

        Current default parameters:
        {json.dumps(spec_params, indent=2)}

        Strategy knowledge document:
        {knowledge_text}
    """)


def _extract_ranges_openai(knowledge_text: str, spec_params: dict) -> dict:
    import openai

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-5.2",
        max_completion_tokens=1500,
        temperature=0,
        messages=[
            {"role": "system", "content": PARAM_RANGES_SYSTEM_PROMPT},
            {"role": "user", "content": _build_param_ranges_prompt(knowledge_text, spec_params)},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    return _parse_ranges_json(raw)


def _extract_ranges_anthropic(knowledge_text: str, spec_params: dict) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        temperature=0,
        system=PARAM_RANGES_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": _build_param_ranges_prompt(knowledge_text, spec_params)},
        ],
    )
    raw = response.content[0].text
    return _parse_ranges_json(raw)


def _parse_ranges_json(raw: str) -> dict:
    """Parse LLM JSON output into param ranges dict."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()
    return json.loads(cleaned)


def extract_param_ranges(
    knowledge_path: str, spec_params: dict, provider: str = "openai",
) -> dict:
    """Extract param ranges from knowledge doc via LLM."""
    path = Path(knowledge_path)
    if not path.exists():
        raise FileNotFoundError(f"Knowledge doc not found: {knowledge_path}")

    knowledge_text = path.read_text()
    print(f"  Extracting param ranges via {provider}...")

    if provider == "openai":
        return _extract_ranges_openai(knowledge_text, spec_params)
    elif provider == "anthropic":
        return _extract_ranges_anthropic(knowledge_text, spec_params)
    else:
        raise ValueError(f"Unknown provider: {provider}")


# ---------------------------------------------------------------------------
# Filter ranges to class-level attrs
# ---------------------------------------------------------------------------


def filter_ranges_to_strategy(
    ranges: dict[str, list], strategy_cls: type,
) -> dict[str, list]:
    """Keep only params that exist as class-level attrs on the strategy."""
    filtered = {}
    for name, values in ranges.items():
        if hasattr(strategy_cls, name):
            if len(values) > 1:
                filtered[name] = values
            else:
                print(f"    Skipping {name}: single value {values}")
        else:
            print(f"    Skipping {name}: not a class-level attr")
    return filtered


# ---------------------------------------------------------------------------
# Parse constraint
# ---------------------------------------------------------------------------


def parse_constraint(constraint_str: str | None):
    """Safely parse a constraint lambda string from LLM. Returns callable or None."""
    if not constraint_str:
        return None
    try:
        fn = eval(constraint_str)  # noqa: S307
        if callable(fn):
            return fn
    except Exception as e:
        print(f"    Warning: invalid constraint '{constraint_str}': {e}")
    return None


# ---------------------------------------------------------------------------
# Reconstruct StrategySpec from v4 result dict
# ---------------------------------------------------------------------------


def spec_from_dict(d: dict) -> StrategySpec:
    """Reconstruct a StrategySpec from a serialized dict."""
    return StrategySpec(
        name=d["name"],
        knowledge_ref=d["knowledge_ref"],
        universe=d["universe"],
        timeframe=d.get("timeframe", "1d"),
        entry_signal=d["entry_signal"],
        exit_signal=d["exit_signal"],
        stop_loss_pct=d.get("stop_loss_pct", 0.02),
        position_size_pct=d.get("position_size_pct", 0.95),
        params=d.get("params", {}),
        adaptations=d.get("adaptations", []),
        skipped=d.get("skipped"),
    )


# ---------------------------------------------------------------------------
# Resume support
# ---------------------------------------------------------------------------


def load_results(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def _sanitize_for_json(obj):
    """Recursively replace NaN/Infinity with None for valid JSON."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    return obj


def save_results(results: list[dict], path: Path) -> None:
    with open(path, "w") as f:
        json.dump(_sanitize_for_json(results), f, indent=2, default=str)


def already_processed(results: list[dict]) -> set[str]:
    return {r["knowledge_doc"] for r in results}


# ---------------------------------------------------------------------------
# Serialize stats
# ---------------------------------------------------------------------------


def _to_native(val):
    """Convert numpy scalars to native Python types."""
    if hasattr(val, "item"):
        return val.item()
    return val


def _safe_sharpe(stats_dict: dict) -> float:
    """Extract Sharpe Ratio, returning 0.0 for NaN/None."""
    s = stats_dict.get("Sharpe Ratio", 0)
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return 0.0
    return float(s)


def _serialize_stats(stats) -> dict:
    """Convert backtesting stats to a JSON-serializable dict, NaN → None."""
    out = {}
    for k, v in dict(stats).items():
        v = _to_native(v)
        if isinstance(v, float) and math.isnan(v):
            v = None
        try:
            json.dumps(v)
            out[k] = v
        except (TypeError, ValueError):
            pass
    return out


# ---------------------------------------------------------------------------
# Core: optimize one strategy
# ---------------------------------------------------------------------------


def optimize_one(v4_result: dict, provider: str, max_tries: int) -> dict:
    """Run parameter optimization for one v4 PASS/MARGINAL strategy."""
    from backtesting import Backtest

    knowledge_doc = v4_result["knowledge_doc"]
    spec_dict = v4_result["spec"]
    v4_stats = v4_result.get("stats", {})
    v4_sharpe = _safe_sharpe(v4_stats) if v4_stats else 0.0

    result = {
        "knowledge_doc": knowledge_doc,
        "name": v4_result["name"],
        "v4_verdict": v4_result["verdict"],
        "v4_sharpe": v4_sharpe,
        "v4_params": spec_dict.get("params", {}),
        "param_ranges": {},
        "optimized_params": {},
        "train_stats": None,
        "test_stats": None,
        "test_verdict": None,
        "test_reasons": [],
        "sharpe_improvement": None,
        "error": None,
    }

    try:
        # 1. Reconstruct spec
        spec = spec_from_dict(spec_dict)
        print(f"  Strategy: {spec.name}")
        print(f"  v4 Sharpe: {v4_sharpe:.2f}, verdict: {v4_result['verdict']}")

        # 2. Regenerate strategy code
        code = generate_strategy_code(spec, provider=provider)
        strategy_cls = load_strategy(code)

        # 3. Extract param ranges from knowledge doc
        ranges_data = extract_param_ranges(knowledge_doc, spec.params, provider=provider)
        raw_ranges = ranges_data.get("param_ranges", {})
        constraint_str = ranges_data.get("constraints")
        reasoning = ranges_data.get("reasoning", "")
        print(f"  LLM reasoning: {reasoning[:100]}...")

        # 4. Filter ranges to class-level attrs
        filtered_ranges = filter_ranges_to_strategy(raw_ranges, strategy_cls)
        result["param_ranges"] = filtered_ranges

        # 5. Download data, split train/test
        df = download_data(spec.universe[0])
        train_df = df[df.index <= TRAIN_END]
        test_df = df[df.index > TRAIN_END]

        if len(train_df) < 60:
            result["error"] = "insufficient_train_data"
            result["test_verdict"] = "ERROR"
            return result
        if len(test_df) < 30:
            result["error"] = "insufficient_test_data"
            result["test_verdict"] = "ERROR"
            return result

        print(f"  Train: {len(train_df)} bars "
              f"({train_df.index[0].date()} to {train_df.index[-1].date()})")
        print(f"  Test:  {len(test_df)} bars "
              f"({test_df.index[0].date()} to {test_df.index[-1].date()})")

        if not filtered_ranges:
            print("  No tunable params after filtering — skipping optimization")
            bt_test = Backtest(
                test_df, strategy_cls, cash=100_000,
                commission=0.001, exclusive_orders=True,
            )
            test_stats = bt_test.run()
            result["test_stats"] = _serialize_stats(test_stats)
            verdict, reasons = evaluate(dict(test_stats))
            result["test_verdict"] = verdict
            result["test_reasons"] = reasons
            result["optimized_params"] = spec.params
            test_sharpe = _safe_sharpe(result["test_stats"])
            result["sharpe_improvement"] = test_sharpe - v4_sharpe
            return result

        print(f"  Optimizing {len(filtered_ranges)} params: "
              f"{list(filtered_ranges.keys())}")
        for name, vals in filtered_ranges.items():
            print(f"    {name}: {vals}")

        # 6. Optimize on train split
        bt_train = Backtest(
            train_df, strategy_cls, cash=100_000,
            commission=0.001, exclusive_orders=True,
        )
        constraint_fn = parse_constraint(constraint_str)
        optimize_kwargs: dict = {
            **filtered_ranges,
            "maximize": "Sharpe Ratio",
            "max_tries": max_tries,
        }
        if constraint_fn:
            optimize_kwargs["constraint"] = constraint_fn

        train_stats = bt_train.optimize(**optimize_kwargs)
        result["train_stats"] = _serialize_stats(train_stats)

        # 7. Extract best params
        best_params = {}
        for name in filtered_ranges:
            best_params[name] = _to_native(getattr(train_stats._strategy, name))
        result["optimized_params"] = best_params
        print(f"  Best params: {best_params}")

        train_sharpe = train_stats.get("Sharpe Ratio", 0)
        print(f"  Train Sharpe: {train_sharpe:.2f}")

        # 8. Evaluate on test split with best params
        bt_test = Backtest(
            test_df, strategy_cls, cash=100_000,
            commission=0.001, exclusive_orders=True,
        )
        test_stats = bt_test.run(**best_params)
        result["test_stats"] = _serialize_stats(test_stats)

        # 9. Pass/fail verdict on test set
        verdict, reasons = evaluate(dict(test_stats))
        result["test_verdict"] = verdict
        result["test_reasons"] = reasons

        test_sharpe = _safe_sharpe(result["test_stats"])
        result["sharpe_improvement"] = test_sharpe - v4_sharpe

        print(f"  Test Sharpe: {test_sharpe:.2f} "
              f"(v4: {v4_sharpe:.2f}, Δ: {result['sharpe_improvement']:+.2f})")
        print(f"  Test verdict: {verdict}")

    except Exception as e:
        result["error"] = str(e)
        result["test_verdict"] = "ERROR"
        result["test_reasons"] = [f"Exception: {e}"]
        print(f"  ERROR: {e}")
        traceback.print_exc()

    return result


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


def print_leaderboard(results: list[dict]) -> None:
    """Print optimized strategies ranked by test Sharpe descending."""
    ranked = [
        r for r in results
        if r.get("test_stats")
        and r["test_stats"].get("Sharpe Ratio") is not None
        and not (isinstance(r["test_stats"]["Sharpe Ratio"], float)
                 and math.isnan(r["test_stats"]["Sharpe Ratio"]))
    ]
    ranked.sort(key=lambda r: r["test_stats"]["Sharpe Ratio"], reverse=True)

    print("\n")
    print("=" * 90)
    print("  LEADERBOARD — Optimized Strategies by Test Sharpe")
    print("=" * 90)

    if not ranked:
        print("  No strategies with test results.")
        print("=" * 90)
        return

    print(f"  {'#':<4} {'Strategy':<32} {'v4 Sharpe':>10} {'Test Sharpe':>11} "
          f"{'Δ':>7} {'Verdict':<8}")
    print("-" * 90)

    for i, r in enumerate(ranked, 1):
        name = (r["name"] or "?")[:31]
        v4_s = r.get("v4_sharpe") or 0
        test_s = _safe_sharpe(r["test_stats"])
        delta = r.get("sharpe_improvement") or 0
        if isinstance(delta, float) and math.isnan(delta):
            delta = 0.0
        verdict = r.get("test_verdict", "?")
        print(f"  {i:<4} {name:<32} {v4_s:>10.2f} {test_s:>11.2f} "
              f"{delta:>+7.2f} {verdict:<8}")

    print("=" * 90)

    # Summary stats
    improvements = [
        r["sharpe_improvement"] for r in ranked
        if r.get("sharpe_improvement") is not None
    ]
    if improvements:
        improved = sum(1 for d in improvements if d > 0)
        degraded = sum(1 for d in improvements if d < 0)
        unchanged = len(improvements) - improved - degraded
        avg_imp = sum(improvements) / len(improvements)
        print(f"\n  Improved: {improved} | Degraded: {degraded} | "
              f"Unchanged: {unchanged}")
        print(f"  Avg Sharpe change: {avg_imp:+.3f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="v5: parameter evolution — optimize v4 PASS/MARGINAL strategies",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Start fresh, ignore previous results",
    )
    parser.add_argument(
        "--provider", choices=["openai", "anthropic"], default="openai",
        help="LLM provider (default: openai)",
    )
    parser.add_argument(
        "--v4-results", default=str(DEFAULT_V4_RESULTS),
        help="Path to v4 results JSON (default: results_v4.json)",
    )
    parser.add_argument(
        "--max-tries", type=int, default=200,
        help="Max grid search combinations to try (default: 200)",
    )
    args = parser.parse_args()

    # 1. Load v4 results, filter to PASS/MARGINAL
    v4_path = Path(args.v4_results)
    if not v4_path.exists():
        print(f"v4 results not found: {v4_path}")
        sys.exit(1)

    with open(v4_path) as f:
        v4_results = json.load(f)

    candidates = [
        r for r in v4_results
        if r["verdict"] in ("PASS", "MARGINAL")
        and r.get("spec")
        and r.get("stats")
    ]
    print(f"Found {len(candidates)} PASS/MARGINAL strategies from v4\n")

    if not candidates:
        print("No candidates to optimize.")
        sys.exit(0)

    # 2. Load or reset v5 results
    if args.reset:
        results: list[dict] = []
        print("Starting fresh (--reset).\n")
    else:
        results = load_results(RESULTS_FILE)
        if results:
            print(f"Loaded {len(results)} previous results from {RESULTS_FILE.name}")

    done = already_processed(results)
    remaining = [c for c in candidates if c["knowledge_doc"] not in done]
    total = len(candidates)

    if not remaining:
        print("All candidates already processed. Use --reset to re-run.\n")
    else:
        print(f"{len(remaining)} remaining "
              f"({total - len(remaining)}/{total} already done).\n")

    # 3. Process remaining
    for i, v4_res in enumerate(remaining, 1):
        idx = total - len(remaining) + i
        print(f"\n{'#' * 75}")
        print(f"# [{idx}/{total}] {v4_res['name']}")
        print(f"{'#' * 75}")

        result = optimize_one(v4_res, provider=args.provider, max_tries=args.max_tries)
        results.append(result)

        # Save after each for resume
        save_results(results, RESULTS_FILE)

        verdict = result.get("test_verdict", "?")
        name = result["name"] or "?"
        delta = result.get("sharpe_improvement")
        delta_str = f" (Δ {delta:+.2f})" if delta is not None else ""
        print(f"  >> [{idx}/{total}] {verdict}: {name}{delta_str}")

    # 4. Leaderboard
    print_leaderboard(results)

    # 5. Summary counts
    counts: dict[str, int] = {}
    for r in results:
        v = r.get("test_verdict") or "UNKNOWN"
        counts[v] = counts.get(v, 0) + 1

    print(f"\nTotal: {len(results)} strategies optimized")
    for v in ["PASS", "MARGINAL", "FAIL", "ERROR", "UNKNOWN"]:
        if v in counts:
            print(f"  {v}: {counts[v]}")

    print(f"\nResults saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
