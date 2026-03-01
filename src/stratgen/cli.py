"""Unified CLI for stratgen: discover, optimize, signals, status."""

import argparse

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="stratgen",
        description="Autonomous trading: alpha factor discovery and trading",
    )
    sub = parser.add_subparsers(dest="command")

    # --- discover ---
    p_disc = sub.add_parser(
        "discover", help="Discover and backtest all alpha factor docs",
    )
    p_disc.add_argument(
        "--reset", action="store_true", help="Start fresh, ignore previous results",
    )
    p_disc.add_argument(
        "--provider", choices=["openai", "anthropic"], default="openai",
        help="LLM provider (default: openai)",
    )

    # --- optimize ---
    p_opt = sub.add_parser(
        "optimize", help="Optimize params for passing factors via grid search",
    )
    p_opt.add_argument(
        "--reset", action="store_true", help="Start fresh, ignore previous results",
    )
    p_opt.add_argument(
        "--provider", choices=["openai", "anthropic"], default="openai",
        help="LLM provider (unused — code is cached from discover)",
    )
    p_opt.add_argument(
        "--max-tries", type=int, default=200,
        help="Max param combos per factor (default: 200)",
    )

    # --- signals ---
    p_sig = sub.add_parser(
        "signals", help="Generate LONG/FLAT signals from top optimized factors",
    )
    p_sig.add_argument(
        "--top-n", type=int, default=5,
        help="Number of top factors to use (default: 5)",
    )

    # --- analyze ---
    p_analyze = sub.add_parser(
        "analyze", help="Cross-sectional factor analysis on a stock universe",
    )
    p_analyze.add_argument(
        "--reset", action="store_true", help="Start fresh, ignore previous results",
    )
    p_analyze.add_argument(
        "--provider", choices=["openai", "anthropic"], default="openai",
        help="LLM provider (default: openai)",
    )
    p_analyze.add_argument(
        "--n-groups", type=int, default=5,
        help="Number of portfolio groups/quintiles (default: 5)",
    )
    p_analyze.add_argument(
        "--universe", choices=["sp100", "sector-etfs"], default="sp100",
        help="Stock universe (default: sp100)",
    )

    # --- optimize-xs ---
    p_opt_xs = sub.add_parser(
        "optimize-xs", help="Optimize XS factor params via grid search (score by |IC|)",
    )
    p_opt_xs.add_argument(
        "--reset", action="store_true", help="Start fresh, ignore previous results",
    )
    p_opt_xs.add_argument(
        "--max-tries", type=int, default=200,
        help="Max param combos per factor (default: 200)",
    )
    p_opt_xs.add_argument(
        "--n-groups", type=int, default=5,
        help="Number of portfolio groups/quintiles (default: 5)",
    )
    p_opt_xs.add_argument(
        "--universe", choices=["sp100", "sector-etfs"], default="sp100",
        help="Stock universe (default: sp100)",
    )
    p_opt_xs.add_argument(
        "--train-end", type=str, default="2022-12-31",
        help="Last date of train period (default: 2022-12-31)",
    )
    p_opt_xs.add_argument(
        "--test-start", type=str, default="2023-01-01",
        help="First date of test period (default: 2023-01-01)",
    )

    # --- status ---
    sub.add_parser("status", help="Show Alpaca account status and positions")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "discover":
        from stratgen.factor_discover import run_factor_discover
        run_factor_discover(provider=args.provider, reset=args.reset)

    elif args.command == "optimize":
        from stratgen.factor_optimize import run_factor_optimize
        run_factor_optimize(
            provider=args.provider, reset=args.reset, max_tries=args.max_tries,
        )

    elif args.command == "signals":
        from stratgen.factor_signals import run_factor_signals
        run_factor_signals(top_n=args.top_n)

    elif args.command == "analyze":
        from stratgen.factor_analyze import run_factor_analyze
        run_factor_analyze(
            provider=args.provider, reset=args.reset,
            n_groups=args.n_groups, universe=args.universe,
        )

    elif args.command == "optimize-xs":
        from stratgen.factor_optimize_xs import run_factor_optimize_xs
        run_factor_optimize_xs(
            reset=args.reset, max_tries=args.max_tries,
            n_groups=args.n_groups, universe=args.universe,
            train_end=args.train_end, test_start=args.test_start,
        )

    elif args.command == "status":
        from stratgen.trade import cmd_status
        cmd_status()
