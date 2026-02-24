"""Entry point for the autonomous evolving investment system.

Can be invoked manually for a single daily cycle, or with --dry-run
to inspect current agent status without executing trades.  Scheduled
execution is handled by OpenClaw cron jobs.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent


def _setup_logging() -> None:
    """Configure logging to both console and a rotating log file."""
    log_dir = _PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "agent.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Console handler.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    root_logger.addHandler(console_handler)

    # File handler.
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    root_logger.addHandler(file_handler)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Autonomous Evolving Investment System",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print agent status (portfolio, curriculum stage, active strategies) and exit.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=True,
        help="Use mock paper broker (local SQLite) instead of Alpaca API. Default: True.",
    )
    parser.add_argument(
        "--no-mock",
        action="store_true",
        default=False,
        help="Use real Alpaca paper trading API instead of local mock.",
    )
    parser.add_argument(
        "--tickers",
        type=str,
        default="",
        help="Comma-separated list of tickers to focus on (e.g. 'AAPL,MSFT,GOOG').",
    )
    parser.add_argument(
        "--action",
        choices=[
            "market_scan", "daily_eval", "daily_report",
            "learn", "weekly_review",
            "query_portfolio", "query_performance",
            "query_knowledge", "run_backtest",
        ],
        default=None,
        help="Specific action to run (used by OpenClaw cron jobs and tool calls).",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="",
        help=(
            "Query string for query_knowledge and run_backtest actions. "
            "For run_backtest, format as 'strategy_name [ticker]' "
            "(e.g. 'sma_crossover SPY')."
        ),
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        default=False,
        help="Broadcast the action result via OpenClaw outbound message after running.",
    )
    return parser.parse_args()


def _print_status(mock: bool) -> None:
    """Print the current agent status and exit."""
    from agents.trading.state import StateManager
    from knowledge.curriculum import CurriculumTracker
    from strategies.registry import registry
    from trading.paper_broker import PaperBroker

    # Load agent state.
    state_mgr = StateManager()
    state = state_mgr.load_state()

    # Load curriculum.
    try:
        curriculum = CurriculumTracker()
        current_stage = curriculum.get_current_stage()
        next_tasks = curriculum.get_next_learning_tasks(max_tasks=3)
    except Exception as exc:
        logging.getLogger(__name__).warning("Could not load curriculum: %s", exc)
        current_stage = state.current_stage
        next_tasks = []

    # Load portfolio.
    broker = PaperBroker(mock=mock)
    portfolio = broker.get_portfolio()

    # Print status.
    print("=" * 60)
    print("  Autonomous Evolving Investment System — Status")
    print("=" * 60)
    print()
    print(f"  Curriculum Stage:    {current_stage}")
    print(f"  Active Strategies:   {state.active_strategies or '(none)'}")
    print(f"  Self-Assessment:     {state.self_assessment or '(none)'}")
    print()
    print("  --- Portfolio ---")
    print(f"  Total Equity:  ${portfolio.total_equity:,.2f}")
    print(f"  Cash:          ${portfolio.cash:,.2f}")
    if portfolio.positions:
        print(f"  Positions:     {len(portfolio.positions)}")
        for pos in portfolio.positions:
            print(
                f"    {pos.ticker:<6}  qty={pos.quantity:<6}  "
                f"avg_cost=${pos.avg_cost:,.2f}  "
                f"pnl=${pos.unrealized_pnl:+,.2f}"
            )
    else:
        print("  Positions:     (none)")
    print()

    if next_tasks:
        print("  --- Next Learning Tasks ---")
        for task in next_tasks:
            mastery = curriculum.get_mastery(task.id)
            print(f"    [{mastery:.0%}] {task.name}: {task.description}")
        print()

    registered = registry.list_strategies()
    if registered:
        print("  --- Registered Strategies ---")
        for name in registered:
            print(f"    - {name}")
        print()

    print("=" * 60)


def _send_openclaw_message(message: str) -> None:
    """Broadcast *message* via the OpenClaw CLI outbound channel.

    Calls ``openclaw message broadcast --message <text>`` if the OpenClaw
    CLI is available on PATH.  Silently no-ops when OpenClaw is not installed
    (e.g. during local testing) so the rest of the action still completes.
    """
    import shutil
    import subprocess

    openclaw_path = shutil.which("openclaw")
    if not openclaw_path:
        logging.getLogger(__name__).warning(
            "openclaw CLI not found on PATH; skipping outbound message."
        )
        return

    try:
        subprocess.run(
            [openclaw_path, "message", "broadcast", "--message", message],
            timeout=15,
            check=True,
            capture_output=True,
            text=True,
        )
        logging.getLogger(__name__).info("OpenClaw broadcast sent successfully.")
    except Exception as exc:
        logging.getLogger(__name__).warning("Failed to send OpenClaw message: %s", exc)


def _dispatch_action(action: str, query: str, notify: bool, mock: bool) -> None:
    """Dispatch a single named action and optionally notify via OpenClaw.

    This is the entry-point used by OpenClaw cron jobs and plugin tool calls.
    Results are always printed to stdout so that the calling process (or the
    OpenClaw agent turn) can capture them.

    Parameters
    ----------
    action:
        One of the choices registered in ``--action``.
    query:
        Free-text argument forwarded to ``query_knowledge`` and
        ``run_backtest`` actions.
    notify:
        When ``True``, the result string is also broadcast via the OpenClaw
        outbound messaging channel.
    mock:
        Passed through to ``TradingAgent`` to select mock vs live broker.
    """
    import asyncio

    from agents.trading.agent import TradingAgent

    result: str

    if action == "market_scan":
        agent = TradingAgent(mock=mock)
        result = agent.run_market_scan()

    elif action == "daily_eval":
        agent = TradingAgent(mock=mock)
        result = agent.run_daily_evaluation()

    elif action == "daily_report":
        agent = TradingAgent(mock=mock)
        result = agent.run_daily_evaluation()
        if notify:
            _send_openclaw_message(result)

    elif action == "learn":
        agent = TradingAgent(mock=mock)
        result = agent.run_learning_session()

    elif action == "weekly_review":
        agent = TradingAgent(mock=mock)
        result = agent.run_weekly_review()
        if notify:
            _send_openclaw_message(result)

    elif action == "query_portfolio":
        from openclaw.tools.query_portfolio import handle
        result = asyncio.run(handle({}))

    elif action == "query_performance":
        from openclaw.tools.query_performance import handle
        result = asyncio.run(handle({}))

    elif action == "query_knowledge":
        from openclaw.tools.query_knowledge import handle
        if not query:
            result = "Error: --query is required for query_knowledge."
        else:
            result = asyncio.run(handle({"query": query}))

    elif action == "run_backtest":
        # Populate the module-level registry so the tool handler can find strategies.
        from strategies.registry import registry as global_registry
        from strategies.rsi_mean_reversion import RSIMeanReversionStrategy
        from strategies.sma_crossover import SMACrossoverStrategy
        if not global_registry.list_strategies():
            global_registry.register(SMACrossoverStrategy())
            global_registry.register(RSIMeanReversionStrategy())

        from openclaw.tools.run_backtest import handle
        parts = query.split() if query else []
        params: dict = {}
        if parts:
            params["strategy_name"] = parts[0]
        if len(parts) >= 2:
            params["ticker"] = parts[1]
        if len(parts) >= 3:
            params["period"] = parts[2]
        if not params.get("strategy_name"):
            result = (
                "Error: --query must specify at least a strategy name "
                "(e.g. --query 'sma_crossover SPY')."
            )
        else:
            result = asyncio.run(handle(params))

    else:
        result = f"Unknown action: {action}"

    print(result)


def _run_daily_cycle(mock: bool, tickers: list[str]) -> None:
    """Execute one daily trading cycle.

    This is the manual-invocation path. OpenClaw cron handles scheduled
    runs by calling individual agent methods directly.
    """
    logger = logging.getLogger(__name__)

    from agents.trading.state import StateManager
    from core.preferences import load_preferences
    from strategies.registry import registry
    from strategies.rsi_mean_reversion import RSIMeanReversionStrategy
    from strategies.sma_crossover import SMACrossoverStrategy
    from trading.data import get_ohlcv
    from trading.executor import Signal, execute_signals
    from trading.paper_broker import PaperBroker
    from trading.risk import PortfolioState, RiskManager

    # Load preferences.
    preferences = load_preferences()
    logger.info(
        "Loaded preferences: risk=%s, horizon=%s, max_dd=%s%%",
        preferences.risk_tolerance,
        preferences.trading_horizon,
        preferences.max_drawdown_pct,
    )

    # Register default strategies if registry is empty.
    if not registry.list_strategies():
        registry.register(SMACrossoverStrategy())
        registry.register(RSIMeanReversionStrategy())
        logger.info("Registered default strategies: %s", registry.list_strategies())

    # Load state.
    state_mgr = StateManager()
    state = state_mgr.load_state()

    # Default tickers if none specified.
    if not tickers:
        tickers = ["SPY", "QQQ", "AAPL", "MSFT", "GOOG"]

    logger.info("Running daily cycle for tickers: %s", tickers)

    # Fetch market data and generate signals.
    all_signals: list[Signal] = []
    for ticker in tickers:
        try:
            data = get_ohlcv(ticker=ticker, period="1y", interval="1d")
            if data.empty:
                logger.warning("No data for %s, skipping", ticker)
                continue

            # Run each active strategy.
            for strategy in registry.get_all():
                try:
                    signals = strategy.generate_signals(data)
                    all_signals.extend(signals)
                    if signals:
                        logger.info(
                            "Strategy '%s' generated %d signal(s) for %s",
                            strategy.name,
                            len(signals),
                            ticker,
                        )
                except Exception:
                    logger.exception(
                        "Strategy '%s' failed on %s", strategy.name, ticker
                    )
        except Exception:
            logger.exception("Failed to process ticker %s", ticker)

    logger.info("Total signals generated: %d", len(all_signals))

    # Execute signals via the broker with risk checks.
    broker = PaperBroker(mock=mock)
    if all_signals:
        risk_manager = RiskManager(preferences)
        portfolio = broker.get_portfolio()

        # Build PortfolioState from broker portfolio.
        positions_dict: dict[str, dict] = {}
        for pos in portfolio.positions:
            positions_dict[pos.ticker] = {
                "quantity": pos.quantity,
                "market_value": pos.market_value,
                "avg_cost": pos.avg_cost,
                "sector": pos.sector,
            }

        portfolio_state = PortfolioState(
            total_equity=portfolio.total_equity,
            cash=portfolio.cash,
            positions=positions_dict,
            daily_pnl=0.0,  # Approximate; full tracking is a future enhancement.
        )

        results = execute_signals(
            signals=all_signals,
            broker=broker,
            risk_manager=risk_manager,
            portfolio_state=portfolio_state,
        )

        executed_count = sum(1 for r in results if r.executed)
        rejected_count = sum(1 for r in results if not r.executed)
        logger.info(
            "Execution complete: %d executed, %d rejected out of %d signals",
            executed_count,
            rejected_count,
            len(results),
        )

        for result in results:
            if result.executed and result.order:
                logger.info(
                    "Executed %s %s: %s @ $%s",
                    result.order.side,
                    result.order.ticker,
                    result.order.status,
                    result.order.filled_price or "pending",
                )
            elif not result.executed:
                logger.info(
                    "Rejected %s %s: %s",
                    result.signal.action,
                    result.signal.ticker,
                    result.rejection_reason,
                )

    # Update state.
    state.active_strategies = registry.list_strategies()
    state_mgr.save_state(state)

    # Portfolio summary.
    portfolio = broker.get_portfolio()
    logger.info(
        "Daily cycle complete. Equity: $%s, Cash: $%s, Positions: %d",
        f"{portfolio.total_equity:,.2f}",
        f"{portfolio.cash:,.2f}",
        len(portfolio.positions),
    )


def main() -> None:
    """Main entry point."""
    # Load environment variables.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass  # dotenv is optional for --dry-run

    _setup_logging()
    logger = logging.getLogger(__name__)

    args = _parse_args()

    # Resolve mock flag.
    mock = not args.no_mock

    # Parse tickers.
    tickers: list[str] = []
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    try:
        if args.dry_run:
            _print_status(mock=mock)
        elif args.action:
            logger.info(
                "Dispatching action: %s (mock=%s, notify=%s)",
                args.action, mock, args.notify,
            )
            _dispatch_action(
                action=args.action,
                query=args.query,
                notify=args.notify,
                mock=mock,
            )
        else:
            logger.info("Starting daily trading cycle (mock=%s)", mock)
            _run_daily_cycle(mock=mock, tickers=tickers)
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        sys.exit(0)
    except Exception:
        logger.exception("Fatal error in main")
        sys.exit(1)


if __name__ == "__main__":
    main()
