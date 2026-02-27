#!/usr/bin/env python3
"""CLI entry point for the autonomous trading agent.

Usage:
    # Run full pipeline with default settings (sector ETFs, paper trading)
    python main.py run

    # Run with computed equity screening (momentum top 10)
    python main.py run --computation momentum_screen --computation-param top_n=10

    # Run evolution only (no deployment)
    python main.py evolve --cycles 3 --universe sp500

    # Deploy a specific strategy
    python main.py deploy --spec-id <SPEC_ID> --mode paper

    # Monitor active deployments
    python main.py status

    # Show available strategy templates and universes
    python main.py info
"""

from __future__ import annotations

import argparse
import logging
import sys

from src.core.config import Settings
from src.orchestrator import Orchestrator
from src.universe.computed import get_available_computations
from src.universe.static import list_static_universes


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


def _parse_computation_params(params: list[str] | None) -> dict:
    """Parse key=value pairs from --computation-param flags."""
    if not params:
        return {}
    result = {}
    for p in params:
        if "=" not in p:
            continue
        key, value = p.split("=", 1)
        # Auto-convert numeric values
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                pass
        result[key.strip()] = value
    return result


def cmd_run(args: argparse.Namespace) -> None:
    """Run the full pipeline: evolve → screen → validate → deploy."""
    print(f"\n{'='*60}")
    print("AUTONOMOUS TRADING AGENT — FULL PIPELINE")
    print(f"{'='*60}")

    comp_params = _parse_computation_params(args.computation_param)

    orch = Orchestrator(
        universe_id=args.universe,
        symbols=args.symbols.split(",") if args.symbols else None,
        mode=args.mode,
    )

    result = orch.run_full_cycle(
        n_evolution_cycles=args.cycles,
        deploy_best=not args.no_deploy,
        computation=args.computation,
        computation_params=comp_params,
    )

    print(f"\n{result.summary()}")
    print(f"\n{orch.get_pipeline_status()}")

    if result.best_spec_id:
        print(f"\n{orch.get_strategy_report(result.best_spec_id)}")

    print(f"\n{orch.get_evolution_report()}")


def cmd_evolve(args: argparse.Namespace) -> None:
    """Run evolution cycles only (no deployment)."""
    print(f"\n{'='*60}")
    print("AUTONOMOUS TRADING AGENT — EVOLUTION")
    print(f"{'='*60}")

    orch = Orchestrator(
        universe_id=args.universe,
        symbols=args.symbols.split(",") if args.symbols else None,
    )

    cycle_results = orch.run_evolution(n_cycles=args.cycles)

    for cr in cycle_results:
        print(f"\n{cr.summary()}")

    print(f"\n{orch.get_evolution_report()}")


def cmd_deploy(args: argparse.Namespace) -> None:
    """Deploy a strategy by spec ID."""
    print(f"\n{'='*60}")
    print("AUTONOMOUS TRADING AGENT — DEPLOY")
    print(f"{'='*60}")

    orch = Orchestrator(
        universe_id=args.universe,
        symbols=args.symbols.split(",") if args.symbols else None,
        mode=args.mode,
    )

    deployment = orch.deploy_strategy(
        spec_id=args.spec_id,
        mode=args.mode,
    )

    if deployment:
        print(f"\nDeployment created: {deployment.id}")
        print(f"  Mode: {deployment.mode}")
        print(f"  Status: {deployment.status}")
    else:
        print("\nDeployment failed. Check logs for details.")


def cmd_status(args: argparse.Namespace) -> None:
    """Show pipeline status."""
    orch = Orchestrator()
    print(orch.get_pipeline_status())


def cmd_schedule(args: argparse.Namespace) -> None:
    """Start the automated trading scheduler."""
    from src.scheduler import TradingScheduler

    print(f"\n{'='*60}")
    print("AUTONOMOUS TRADING AGENT — SCHEDULER")
    print(f"{'='*60}")

    comp_params = _parse_computation_params(args.computation_param)

    sched = TradingScheduler(
        universe_id=args.universe,
        cycles=args.cycles,
        computation=args.computation,
        computation_params=comp_params or None,
    )

    print(f"\n{sched.scheduler.get_status()}")
    print("\nPress Ctrl-C to stop.\n")
    sched.start(blocking=True)


def cmd_info(args: argparse.Namespace) -> None:
    """Show available templates, universes, and computations."""
    from src.agent.generator import SUPPORTED_TEMPLATES

    print(f"\n{'='*60}")
    print("AVAILABLE RESOURCES")
    print(f"{'='*60}")

    print("\nSupported Strategy Templates:")
    for t in SUPPORTED_TEMPLATES:
        print(f"  - {t}")

    print(f"\nStatic Universes:")
    for name in list_static_universes():
        from src.universe.static import STATIC_UNIVERSES
        symbols = STATIC_UNIVERSES[name]
        print(f"  - {name:15s} ({len(symbols)} symbols)")

    print(f"\nComputed Universe Builders:")
    for name in get_available_computations():
        print(f"  - {name}")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="autonomous-trader",
        description="Autonomous trading agent — LLM-driven strategy evolution + live trading",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # ── run ──
    run_parser = subparsers.add_parser("run", help="Run full pipeline")
    run_parser.add_argument("--cycles", type=int, default=1, help="Evolution cycles (default 1)")
    run_parser.add_argument("--universe", default="sector_etfs", help="Universe ID")
    run_parser.add_argument("--symbols", default=None, help="Override symbols (comma-separated)")
    run_parser.add_argument("--mode", default="paper", choices=["paper", "live"], help="Trading mode")
    run_parser.add_argument("--computation", default=None, help="Computed universe builder name")
    run_parser.add_argument("--computation-param", action="append", help="Computation params (key=value)")
    run_parser.add_argument("--no-deploy", action="store_true", help="Skip deployment step")

    # ── evolve ──
    evolve_parser = subparsers.add_parser("evolve", help="Run evolution cycles only")
    evolve_parser.add_argument("--cycles", type=int, default=3, help="Number of cycles")
    evolve_parser.add_argument("--universe", default="sector_etfs", help="Universe ID")
    evolve_parser.add_argument("--symbols", default=None, help="Override symbols (comma-separated)")

    # ── deploy ──
    deploy_parser = subparsers.add_parser("deploy", help="Deploy a strategy by spec ID")
    deploy_parser.add_argument("spec_id", help="Strategy spec ID to deploy")
    deploy_parser.add_argument("--mode", default="paper", choices=["paper", "live"], help="Trading mode")
    deploy_parser.add_argument("--universe", default="sector_etfs", help="Universe ID")
    deploy_parser.add_argument("--symbols", default=None, help="Override symbols (comma-separated)")

    # ── schedule ──
    sched_parser = subparsers.add_parser("schedule", help="Start automated trading scheduler")
    sched_parser.add_argument("--cycles", type=int, default=3, help="Pipeline cycles per run (default 3)")
    sched_parser.add_argument("--universe", default="sector_etfs", help="Universe ID")
    sched_parser.add_argument("--computation", default=None, help="Computed universe builder name")
    sched_parser.add_argument("--computation-param", action="append", help="Computation params (key=value)")

    # ── status ──
    subparsers.add_parser("status", help="Show pipeline status")

    # ── info ──
    subparsers.add_parser("info", help="Show available templates and universes")

    args = parser.parse_args()
    _setup_logging(args.verbose)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "run": cmd_run,
        "evolve": cmd_evolve,
        "deploy": cmd_deploy,
        "schedule": cmd_schedule,
        "status": cmd_status,
        "info": cmd_info,
    }
    commands[args.command](args)


def _silence_resource_tracker() -> None:
    """Spawn the multiprocessing resource tracker with stderr silenced.

    backtesting.py's optimize() leaks shared_memory segments, causing hundreds
    of ``KeyError: '/psm_...'`` tracebacks and ``UserWarning``s from the
    resource_tracker subprocess at exit.

    The tracker is a separate process launched via ``spawnv_passfds`` which
    inherits the parent's stderr fd at spawn time.  We temporarily point fd 2
    to ``/dev/null``, force the tracker to start (so it inherits the silenced
    stderr), then restore fd 2 for the main process.
    """
    import os
    from multiprocessing import resource_tracker as rt

    saved_stderr = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        rt.ensure_running()
    finally:
        os.dup2(saved_stderr, 2)
        os.close(saved_stderr)


if __name__ == "__main__":
    _silence_resource_tracker()
    main()
