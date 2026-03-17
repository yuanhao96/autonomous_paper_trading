"""AutoScreen: autonomous stock screening research loop.

Uses Claude Code CLI (`claude -p`) to propose screens. Claude Code has full
access to project files (CLAUDE.md, program.md, knowledge/, factors/) and
can reason about what screens to try based on the full project context.
"""
import json
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

PROGRAM_PATH = Path("program.md")
RESULTS_PATH = Path("results.jsonl")
ANALYSIS_PATH = Path("analysis.md")
DETAILS_DIR = Path("data/details")

# Graceful shutdown flag
_shutdown = False


def _handle_sigint(signum, frame):
    global _shutdown
    if _shutdown:
        # Second Ctrl+C — force exit
        raise SystemExit(1)
    _shutdown = True
    print("\n\nShutting down after current iteration... (Ctrl+C again to force)")


signal.signal(signal.SIGINT, _handle_sigint)


def _claude_call(prompt: str, timeout: int = 120,
                  allowed_tools: list[str] | None = None) -> str:
    """Call Claude Code CLI and return stdout."""
    env = dict(__import__("os").environ)
    env.pop("CLAUDECODE", None)

    cmd = ["claude", "-p", prompt, "--output-format", "text"]
    if allowed_tools is not None:
        cmd.extend(["--allowedTools", ",".join(allowed_tools) if allowed_tools else ""])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude Code failed: {result.stderr[:500]}")

    return result.stdout


def parse_screen_json(text: str) -> dict:
    """Extract screen JSON from LLM response. Handles markdown code blocks."""
    # Try to find JSON in code block first
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # Fallback: try to parse the entire text as JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    raise ValueError(f"Could not parse screen JSON from LLM response:\n{text[:500]}")


def _run_analyze_script() -> str:
    """Run analyze.py and return its stdout."""
    result = subprocess.run(
        [sys.executable, "analyze.py", "--section", "all"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"analyze.py failed: {result.stderr[:500]}")
    return result.stdout


def analyze_results() -> str:
    """Analysis pass: run analyze.py for stats, then LLM interprets and writes analysis.md."""
    if not RESULTS_PATH.exists():
        return ""

    # Step 1: Run the deterministic analysis script
    print("Running analyze.py...")
    try:
        stats_output = _run_analyze_script()
    except Exception as e:
        print(f"analyze.py error: {e}")
        stats_output = ""

    if not stats_output:
        return ""

    # Step 2: LLM interprets the computed stats and writes analysis.md
    prompt = (
        "You are a quantitative research analyst. Below are pre-computed statistics "
        "from analyze.py covering all screen backtest results.\n\n"
        f"```\n{stats_output}\n```\n\n"
        "Write a concise research memo covering:\n"
        "1. What works and what fails (with computed evidence)\n"
        "2. RECENCY: which screens are STALE (good full-period but decaying "
        "recently) vs. fresh (strong trailing-12m Sharpe)? Highlight the "
        "trailing-12m Sharpe and alpha trend slope.\n"
        "3. REGIME ROBUSTNESS: which screens work across market regimes "
        "(quiet_bull, volatile_bull, quiet_bear, volatile_bear)? "
        "Flag screens that only work in one regime.\n"
        "4. WALK-FORWARD: if walk-forward data is present, analyze mean OOS "
        "Sharpe across windows and consistency (std). Flag screens with high "
        "variance across windows as unstable.\n"
        "5. Stock concentration and overlap analysis\n"
        "6. Strategies to avoid (already tried, failed, overfit, or STALE)\n"
        "7. Specific promising directions — favor features with high recent "
        "hit rate and positive trend direction, and screens robust across "
        "regimes\n"
        "8. Current best Sharpe to beat (use OOS Sharpe if available)\n\n"
        "Every claim must cite numbers from the stats above. "
        "Output ONLY the memo content in markdown. No preamble. "
        "Do NOT use any tools — just output the text directly."
    )

    print("LLM interpreting stats → analysis.md...")
    memo = _claude_call(prompt, timeout=300, allowed_tools=[])

    if memo.strip():
        ANALYSIS_PATH.write_text(memo)
        return memo
    elif ANALYSIS_PATH.exists():
        return ANALYSIS_PATH.read_text()
    return ""


def propose_screen() -> dict:
    """Use Claude Code CLI to propose a new screen."""
    prompt = (
        "Read program.md to understand the AutoScreen system and available features. "
    )
    if ANALYSIS_PATH.exists():
        prompt += "Read analysis.md for research insights from past screen results. "
    if Path("feature_stats.md").exists():
        prompt += "Read feature_stats.md for per-feature predictive power stats. "
    prompt += (
        "Based on the available features, the analysis insights, "
        "and your knowledge of what predicts stock returns, propose ONE new stock screen.\n"
        "IMPORTANT: Use score-based screens (rank_by='_score' with score weights) as "
        "the default approach. Always include at least 1-2 hard filters to narrow the "
        "universe (e.g., liquidity floor, volatility cap, or quality threshold) — "
        "pure score-only screens with no filters are not allowed.\n"
        "Use _pctrank features in scores for comparable 0-1 scales.\n"
        "Experiment with holding_days: 10, 21, or 42 trading days.\n"
        "Focus on features with proven quintile spread from feature_stats.md.\n"
        "Output ONLY the JSON object in a ```json code block. No other text."
    )

    return parse_screen_json(_claude_call(prompt, allowed_tools=["Read", "Glob"]))


def append_result(result: dict):
    """Append result to results.jsonl, archiving stock_details separately."""
    idx = count_results()

    # Archive per-stock details to a separate file
    stock_details = result.pop("stock_details", None)
    if stock_details:
        DETAILS_DIR.mkdir(parents=True, exist_ok=True)
        with open(DETAILS_DIR / f"{idx}.json", "w") as f:
            json.dump(stock_details, f)

    with open(RESULTS_PATH, "a") as f:
        f.write(json.dumps(result) + "\n")


def count_results() -> int:
    """Count existing results."""
    if not RESULTS_PATH.exists():
        return 0
    with open(RESULTS_PATH) as f:
        return sum(1 for _ in f)


def get_best_sharpe() -> float:
    """Get the best Sharpe from results.jsonl."""
    if not RESULTS_PATH.exists():
        return 0.0
    best = 0.0
    with open(RESULTS_PATH) as f:
        for line in f:
            r = json.loads(line)
            if r["sharpe"] > best:
                best = r["sharpe"]
    return best


def print_summary():
    """Print final summary of all results."""
    import pandas as pd
    print(f"\n{'='*60}")
    print(f"Done. {count_results()} total screens evaluated.")
    if RESULTS_PATH.exists():
        df = pd.read_json(RESULTS_PATH, lines=True)
        kept = df[df["verdict"] == "KEEP"]
        print(f"Keepers: {len(kept)} / {len(df)}")
        if len(kept) > 0:
            print("\nBest screens (by Sharpe):")
            print(kept.sort_values("sharpe", ascending=False)[
                ["name", "sharpe", "alpha_annual", "win_rate"]
            ].head(10).to_string(index=False))


def run_loop(
    n_iterations: int = None,
    hours: float = None,
    patience: int = 20,
    walk_forward: bool = True,
    train_months: int = 18,
    test_months: int = 6,
):
    """Main loop: analyze → propose → evaluate → log.

    Args:
        walk_forward: Use rolling walk-forward evaluation (default: True).
        train_months: Walk-forward train window in months.
        test_months: Walk-forward test window in months.
    """
    from screen import apply_screen, compute_all_features

    print("Computing features from cached data...")
    features = compute_all_features()
    print(f"Features ready: {features.shape}")
    if walk_forward:
        print(f"Walk-forward: {train_months}mo train / {test_months}mo test")

    start_time = time.time()
    deadline = start_time + hours * 3600 if hours else None
    iterations_done = 0
    since_last_keep = 0
    best_sharpe = get_best_sharpe()
    errors_in_a_row = 0

    mode_parts = []
    if n_iterations:
        mode_parts.append(f"{n_iterations} iterations")
    if hours:
        mode_parts.append(f"{hours}h time limit")
    mode_parts.append(f"patience={patience}")
    print(f"Mode: {', '.join(mode_parts)}")
    if best_sharpe > 0:
        print(f"Resuming — best Sharpe so far: {best_sharpe:.3f}")

    while True:
        # Check stopping conditions
        if _shutdown:
            print("\nGraceful shutdown requested.")
            break
        if n_iterations and iterations_done >= n_iterations:
            print(f"\nReached {n_iterations} iterations.")
            break
        if deadline and time.time() >= deadline:
            elapsed_h = (time.time() - start_time) / 3600
            print(f"\nTime limit reached ({elapsed_h:.1f}h).")
            break
        if since_last_keep >= patience:
            print(f"\nPatience exhausted — {patience} iterations with no new KEEP.")
            break

        iteration = count_results() + 1
        elapsed = (time.time() - start_time) / 60
        print(f"\n{'='*60}")
        print(f"Iteration {iteration}  |  {elapsed:.0f}m elapsed  |  "
              f"best Sharpe: {best_sharpe:.3f}  |  "
              f"drought: {since_last_keep}/{patience}")
        print(f"{'='*60}")

        # Step 1: Analysis pass (overwrites analysis.md each time)
        if count_results() > 0:
            try:
                analyze_results()
                errors_in_a_row = 0
            except Exception as e:
                print(f"Analysis error (continuing): {e}")
                errors_in_a_row += 1

        # Step 2: Claude Code proposes screen
        print("Asking Claude Code for screen proposal...")
        try:
            screen_def = propose_screen()
            errors_in_a_row = 0
        except Exception as e:
            print(f"Proposal error: {e}")
            errors_in_a_row += 1
            if errors_in_a_row >= 5:
                print("Too many consecutive errors — stopping.")
                break
            continue

        print(f"Screen: {screen_def.get('name', '?')}")
        print(f"Hypothesis: {screen_def.get('hypothesis', '?')}")
        filters = screen_def.get('filters', [])
        if filters:
            print("Filters:")
            for f in filters:
                val = f['value']
                if isinstance(val, list):
                    val = f"[{val[0]}, {val[1]}]"
                print(f"  {f['feature']:>30} {f['op']} {val}")
        else:
            print("Filters: (none)")
        if screen_def.get('score'):
            print("Score weights:")
            for s in screen_def['score']:
                print(f"  {s['feature']:>30}  w={s['weight']}")
        if screen_def.get('rank_by'):
            print(f"Rank by: {screen_def['rank_by']} ({screen_def.get('rank_order', 'desc')})")
        if screen_def.get('holding_days') and screen_def['holding_days'] != 21:
            print(f"Holding days: {screen_def['holding_days']}")

        # Step 3: Evaluate
        print("Backtesting...")
        result = apply_screen(
            screen_def, features,
            walk_forward=walk_forward,
            train_months=train_months,
            test_months=test_months,
        )

        # Log
        sharpe = result['sharpe']
        verdict = result['verdict']
        print(f"Alpha (monthly): {result['alpha_monthly_mean']:.4f}")
        print(f"Alpha (annual):  {result.get('alpha_annual', 0):.2%}")
        print(f"Sharpe (full):   {sharpe:.3f}")
        if walk_forward and 'wf_oos_sharpe_mean' in result:
            print(f"WF OOS Sharpe:   {result['wf_oos_sharpe_mean']:.3f}"
                  f" +/- {result['wf_oos_sharpe_std']:.3f}")
            print(f"WF windows:      {result['wf_n_windows']}")
        print(f"Win rate:        {result['win_rate']:.1%}")
        print(f"Avg stocks:      {result['n_avg_stocks']}")
        print(f"Verdict:         {verdict}")

        append_result(result)
        iterations_done += 1

        if verdict == "KEEP":
            since_last_keep = 0
            if sharpe > best_sharpe:
                print(f"*** New best Sharpe: {sharpe:.3f} (was {best_sharpe:.3f}) ***")
                best_sharpe = sharpe
        else:
            since_last_keep += 1

        # Progress summary every 10 iterations
        if iterations_done % 10 == 0:
            print(f"\n--- Progress: {iterations_done} iterations, "
                  f"{elapsed:.0f}m elapsed, best Sharpe: {best_sharpe:.3f} ---")

    print_summary()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AutoScreen research loop")

    # Mode selection
    parser.add_argument("--screen", action="store_true",
                        help="Screen mode: run top screens on today's market")
    parser.add_argument("--top-k", type=int, default=3,
                        help="Number of screens to run in screen mode (default: 3)")
    parser.add_argument("--skip-refresh", action="store_true",
                        help="Skip data refresh in screen mode (use cached data)")

    # Research mode options
    parser.add_argument("-n", type=int, default=None,
                        help="Max number of iterations (default: unlimited)")
    parser.add_argument("--hours", type=float, default=None,
                        help="Time limit in hours (e.g. 8 for overnight)")
    parser.add_argument("--patience", type=int, default=20,
                        help="Stop after N iterations with no new KEEP (default: 20)")
    parser.add_argument("--no-walk-forward", dest="walk_forward",
                        action="store_false", default=True,
                        help="Disable walk-forward (use full-period Sharpe)")
    parser.add_argument("--train-months", type=int, default=18,
                        help="Walk-forward train window in months (default: 18)")
    parser.add_argument("--test-months", type=int, default=6,
                        help="Walk-forward test window in months (default: 6)")
    args = parser.parse_args()

    if args.screen:
        from screen_report import run_screen_mode
        run_screen_mode(k=args.top_k, skip_refresh=args.skip_refresh)
    else:
        # Default to 10 iterations if no stopping condition specified
        if args.n is None and args.hours is None:
            args.n = 10
        run_loop(
            n_iterations=args.n,
            hours=args.hours,
            patience=args.patience,
            walk_forward=args.walk_forward,
            train_months=args.train_months,
            test_months=args.test_months,
        )
