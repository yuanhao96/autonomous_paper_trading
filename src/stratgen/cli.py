"""Unified CLI for stratgen: discover, optimize, signals, run, status."""

import argparse

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="stratgen",
        description="Autonomous trading strategy generation and optimization",
    )
    sub = parser.add_subparsers(dest="command")

    # --- discover ---
    p_disc = sub.add_parser("discover", help="Discover and backtest all strategy docs")
    p_disc.add_argument("--reset", action="store_true", help="Start fresh, ignore previous results")
    p_disc.add_argument(
        "--provider", choices=["openai", "anthropic"], default="openai",
        help="LLM provider (default: openai)",
    )

    # --- optimize ---
    p_opt = sub.add_parser("optimize", help="Optimize params for PASS/MARGINAL strategies")
    p_opt.add_argument("--reset", action="store_true", help="Start fresh, ignore previous results")
    p_opt.add_argument(
        "--provider", choices=["openai", "anthropic"], default="openai",
        help="LLM provider (default: openai)",
    )
    p_opt.add_argument(
        "--v4-results", default=None,
        help="Path to discover results JSON (default: results_v4.json)",
    )
    p_opt.add_argument(
        "--max-tries", type=int, default=200,
        help="Max grid search combinations to try (default: 200)",
    )

    # --- signals ---
    p_sig = sub.add_parser("signals", help="Generate trading signals (no orders)")
    p_sig.add_argument(
        "--top-n", type=int, default=5,
        help="Number of top strategies (default: 5)",
    )
    p_sig.add_argument(
        "--provider", choices=["openai", "anthropic"], default="openai",
        help="LLM provider (default: openai)",
    )
    p_sig.add_argument("--v5-results", default=None, help="Path to optimize results JSON")
    p_sig.add_argument("--v4-results", default=None, help="Path to discover results JSON")

    # --- run ---
    p_run = sub.add_parser("run", help="Generate signals and submit orders to Alpaca")
    p_run.add_argument(
        "--top-n", type=int, default=5,
        help="Number of top strategies (default: 5)",
    )
    p_run.add_argument(
        "--provider", choices=["openai", "anthropic"], default="openai",
        help="LLM provider (default: openai)",
    )
    p_run.add_argument("--v5-results", default=None, help="Path to optimize results JSON")
    p_run.add_argument("--v4-results", default=None, help="Path to discover results JSON")

    # --- status ---
    sub.add_parser("status", help="Show Alpaca account status and positions")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "discover":
        from stratgen.discover import run_discover
        run_discover(provider=args.provider, reset=args.reset)

    elif args.command == "optimize":
        from stratgen.optimize import run_optimize
        run_optimize(
            provider=args.provider,
            reset=args.reset,
            v4_results_path=args.v4_results,
            max_tries=args.max_tries,
        )

    elif args.command == "signals":
        from stratgen.trade import cmd_signals
        cmd_signals(args)

    elif args.command == "run":
        from stratgen.trade import cmd_run
        cmd_run(args)

    elif args.command == "status":
        from stratgen.trade import cmd_status
        cmd_status(args)
