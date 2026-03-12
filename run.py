"""AutoScreen: autonomous stock screening research loop.

Uses Claude Code CLI (`claude -p`) to propose screens. Claude Code has full
access to project files (CLAUDE.md, program.md, knowledge/, factors/) and
can reason about what screens to try based on the full project context.
"""
import json
import re
import signal
import subprocess
import time
from pathlib import Path

PROGRAM_PATH = Path("program.md")
RESULTS_PATH = Path("results.jsonl")
ANALYSIS_PATH = Path("analysis.md")

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


def _claude_call(prompt: str, timeout: int = 120) -> str:
    """Call Claude Code CLI and return stdout."""
    env = dict(__import__("os").environ)
    env.pop("CLAUDECODE", None)

    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
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


def analyze_results() -> str:
    """Dedicated analysis pass: read all results, write analysis.md."""
    if not RESULTS_PATH.exists():
        return ""

    prompt = (
        "You are a quantitative research analyst. Your job is to analyze stock screen "
        "backtest results in results.jsonl and write a research memo to analysis.md.\n\n"
        "results.jsonl contains one JSON object per line. Each has:\n"
        "- name, hypothesis, filters, sharpe, alpha_monthly_mean, alpha_annual, win_rate\n"
        "- monthly_details: array of {month, stocks: {ticker: return}, port_return, spy_return, alpha}\n\n"
        "USE PYTHON AND PANDAS to compute statistics — do NOT eyeball raw JSON. "
        "Write and run Python scripts to answer questions like:\n"
        "- Which features/thresholds appear in KEEP (Sharpe >= 0.3) vs DISCARD screens?\n"
        "- Stock-level analysis: most frequent picks, best/worst alpha contributors, overlap between screens\n"
        "- Regime analysis: alpha by year, which market conditions help/hurt\n"
        "- Per-screen monthly alpha time series — is alpha decaying or stable?\n"
        "- Any other patterns you find interesting\n\n"
        "Explore freely — run as many scripts as you need to understand the data deeply. "
        "Then write a concise research memo to analysis.md covering:\n"
        "1. What works and what fails (with computed evidence)\n"
        "2. Stock concentration and overlap analysis\n"
        "3. Regime/temporal patterns\n"
        "4. Strategies to avoid (already tried and failed)\n"
        "5. Specific promising directions with feature/threshold suggestions\n"
        "6. Current best Sharpe to beat\n\n"
        "Write analysis.md when done. Be specific with numbers — every claim should be backed by computed stats."
    )

    print("Running analysis pass...")
    _claude_call(prompt, timeout=300)

    # Read back what the agent wrote
    if ANALYSIS_PATH.exists():
        return ANALYSIS_PATH.read_text()
    return ""


def propose_screen() -> dict:
    """Use Claude Code CLI to propose a new screen.

    Reads program.md for features/rules and analysis.md for research insights.
    """
    prompt = (
        "Read program.md to understand the AutoScreen system and available features. "
    )
    if ANALYSIS_PATH.exists():
        prompt += "Read analysis.md for research insights from past screen results. "
    prompt += (
        "Based on the available features, the analysis insights, "
        "and your knowledge of what predicts stock returns, propose ONE new stock screen. "
        "The KEEP criterion is Sharpe >= 0.3 (on monthly alpha vs SPY, annualized). "
        "Output ONLY the JSON object in a ```json code block. No other text."
    )

    return parse_screen_json(_claude_call(prompt))


def append_result(result: dict):
    """Append result to results.jsonl."""
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


def run_loop(n_iterations: int = None, hours: float = None, patience: int = 20):
    """Main loop: analyze → propose → evaluate → log.

    Stopping conditions (whichever comes first):
    - n_iterations reached (if set)
    - hours elapsed (if set)
    - patience exhausted: no new KEEP for `patience` consecutive iterations
    - Ctrl+C (graceful shutdown after current iteration)
    """
    from screen import apply_screen, compute_all_features

    print("Computing features from cached data...")
    features = compute_all_features()
    print(f"Features ready: {features.shape}")

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
        print(f"Filters: {json.dumps(screen_def.get('filters', []), indent=2)}")

        # Step 3: Evaluate
        print("Backtesting...")
        result = apply_screen(screen_def, features)

        # Log
        sharpe = result['sharpe']
        verdict = result['verdict']
        print(f"Alpha (monthly): {result['alpha_monthly_mean']:.4f}")
        print(f"Alpha (annual):  {result.get('alpha_annual', 0):.2%}")
        print(f"Sharpe:          {sharpe:.2f}")
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
    parser.add_argument("-n", type=int, default=None,
                        help="Max number of iterations (default: unlimited)")
    parser.add_argument("--hours", type=float, default=None,
                        help="Time limit in hours (e.g. 8 for overnight)")
    parser.add_argument("--patience", type=int, default=20,
                        help="Stop after N iterations with no new KEEP (default: 20)")
    args = parser.parse_args()

    # Default to 10 iterations if no stopping condition specified
    if args.n is None and args.hours is None:
        args.n = 10

    run_loop(n_iterations=args.n, hours=args.hours, patience=args.patience)
