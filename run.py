"""AutoScreen: autonomous stock screening research loop.

Uses Claude Code CLI (`claude -p`) to propose screens. Claude Code has full
access to project files (CLAUDE.md, program.md, knowledge/, factors/) and
can reason about what screens to try based on the full project context.
"""
import json
import re
import subprocess
from pathlib import Path

PROGRAM_PATH = Path("program.md")
RESULTS_PATH = Path("results.jsonl")


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


def propose_screen() -> dict:
    """Use Claude Code CLI to propose a new screen.

    Claude Code automatically sees CLAUDE.md, can read program.md and
    results.jsonl, and has access to the knowledge base and factor docs.
    """
    prompt = (
        "Read program.md to understand the AutoScreen system. "
        "Read results.jsonl if it exists to see past screen results. "
        "Based on the available features, past results (learn from what worked/failed), "
        "and your knowledge of what predicts stock returns, propose ONE new stock screen. "
        "Output ONLY the JSON object in a ```json code block. No other text."
    )

    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude Code failed: {result.stderr[:500]}")

    return parse_screen_json(result.stdout)


def append_result(result: dict):
    """Append result to results.jsonl and to program.md."""
    # Append to JSONL
    with open(RESULTS_PATH, "a") as f:
        f.write(json.dumps(result) + "\n")

    # Append human-readable summary to program.md
    summary = (
        f"\n### Screen #{count_results()}: {result['name']}\n"
        f"- **Hypothesis**: {result['hypothesis']}\n"
        f"- **Filters**: {json.dumps(result['filters'])}\n"
        f"- **Alpha (monthly)**: {result['alpha_monthly_mean']:.4f} "
        f"({result.get('alpha_annual', 0):.2%} annualized)\n"
        f"- **Sharpe**: {result['sharpe']:.2f}\n"
        f"- **Win rate**: {result['win_rate']:.1%}\n"
        f"- **Avg stocks**: {result['n_avg_stocks']}\n"
        f"- **Months**: {result['n_months']}\n"
        f"- **Verdict**: {result['verdict']}\n"
    )
    with open(PROGRAM_PATH, "a") as f:
        f.write(summary)


def count_results() -> int:
    """Count existing results."""
    if not RESULTS_PATH.exists():
        return 0
    with open(RESULTS_PATH) as f:
        return sum(1 for _ in f)


def run_loop(n_iterations: int = 10):
    """Main loop: propose → evaluate → log, repeated n times."""
    from screen import apply_screen, compute_all_features

    print("Computing features from cached data...")
    features = compute_all_features()
    print(f"Features ready: {features.shape}")

    for i in range(n_iterations):
        iteration = count_results() + 1
        print(f"\n{'='*60}")
        print(f"Iteration {iteration}")
        print(f"{'='*60}")

        # Claude Code proposes screen
        print("Asking Claude Code for screen proposal...")
        try:
            screen_def = propose_screen()
        except Exception as e:
            print(f"Error: {e}")
            continue

        print(f"Screen: {screen_def.get('name', '?')}")
        print(f"Hypothesis: {screen_def.get('hypothesis', '?')}")
        print(f"Filters: {json.dumps(screen_def.get('filters', []), indent=2)}")

        # Evaluate
        print("Backtesting...")
        result = apply_screen(screen_def, features)

        # Log
        print(f"Alpha (monthly): {result['alpha_monthly_mean']:.4f}")
        print(f"Alpha (annual):  {result.get('alpha_annual', 0):.2%}")
        print(f"Sharpe:          {result['sharpe']:.2f}")
        print(f"Win rate:        {result['win_rate']:.1%}")
        print(f"Avg stocks:      {result['n_avg_stocks']}")
        print(f"Verdict:         {result['verdict']}")

        append_result(result)

    # Summary
    print(f"\n{'='*60}")
    print(f"Done. {count_results()} total screens evaluated.")
    if RESULTS_PATH.exists():
        import pandas as pd
        df = pd.read_json(RESULTS_PATH, lines=True)
        kept = df[df["verdict"] == "KEEP"]
        print(f"Keepers: {len(kept)} / {len(df)}")
        if len(kept) > 0:
            print("\nBest screens:")
            print(kept.sort_values("alpha_annual", ascending=False)[
                ["name", "alpha_annual", "sharpe", "win_rate"]
            ].head(5).to_string(index=False))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AutoScreen research loop")
    parser.add_argument("-n", type=int, default=10, help="Number of iterations")
    args = parser.parse_args()
    run_loop(n_iterations=args.n)
