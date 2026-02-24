"""Main trading agent for V1 scope.

Orchestrates the daily trading cycle, learning sessions, evaluations,
and market scans.  Each method is designed to be called from OpenClaw
cron jobs or tool invocations.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.trading.state import StateManager
from core.preferences import load_preferences
from knowledge.curriculum import CurriculumTracker
from knowledge.ingestion import fetch_arxiv, fetch_news, fetch_wikipedia
from knowledge.store import KnowledgeStore
from strategies.registry import StrategyRegistry
from strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from strategies.sma_crossover import SMACrossoverStrategy
from trading.data import get_multiple
from trading.executor import Signal, execute_signals
from trading.paper_broker import PaperBroker, Portfolio
from trading.risk import PortfolioState, RiskManager

logger = logging.getLogger(__name__)

_DEFAULT_TICKERS: list[str] = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def _portfolio_to_state(portfolio: Portfolio) -> PortfolioState:
    """Convert a ``Portfolio`` broker object to a ``PortfolioState`` for risk checks."""
    positions: dict[str, dict[str, Any]] = {}
    for pos in portfolio.positions:
        positions[pos.ticker] = {
            "quantity": pos.quantity,
            "market_value": pos.market_value,
            "avg_cost": pos.avg_cost,
            "sector": pos.sector,
        }
    return PortfolioState(
        total_equity=portfolio.total_equity,
        cash=portfolio.cash,
        positions=positions,
        daily_pnl=0.0,  # V1: daily P&L tracking not yet implemented
    )


class TradingAgent:
    """V1 trading agent that runs the core trading loop.

    Parameters
    ----------
    mock:
        If ``True`` (default), use the local mock broker backed by SQLite
        and yfinance.  Set to ``False`` to route orders to Alpaca paper trading.
    """

    def __init__(self, mock: bool = True) -> None:
        self._broker = PaperBroker(mock=mock)

        preferences = load_preferences()
        self._risk_manager = RiskManager(preferences)
        self._curriculum = CurriculumTracker()
        self._state_manager = StateManager()
        self._registry = StrategyRegistry()

        # Register default strategies.
        self._registry.register(SMACrossoverStrategy())
        self._registry.register(RSIMeanReversionStrategy())

        logger.info(
            "TradingAgent initialised (mock=%s, strategies=%s)",
            mock,
            self._registry.list_strategies(),
        )

    # ------------------------------------------------------------------
    # Daily trading cycle
    # ------------------------------------------------------------------

    def run_daily_cycle(self, tickers: list[str] | None = None) -> str:
        """Execute one full daily trading cycle.

        1. Fetch market data for each ticker.
        2. Generate signals from all active strategies.
        3. Execute signals through risk checks and the broker.

        Parameters
        ----------
        tickers:
            Symbols to trade.  Defaults to a built-in watchlist.

        Returns
        -------
        str
            Human-readable summary of the actions taken.
        """
        tickers = tickers or _DEFAULT_TICKERS
        logger.info("Starting daily cycle for tickers: %s", tickers)

        # 1. Fetch market data.
        try:
            market_data = get_multiple(tickers)
        except Exception:
            logger.exception("Failed to fetch market data")
            return "Daily cycle failed: could not fetch market data."

        # 2. Generate signals.
        all_signals: list[Signal] = []
        strategies = self._registry.get_all()

        for ticker, df in market_data.items():
            if df.empty:
                logger.warning("No data for %s, skipping", ticker)
                continue
            # Attach ticker to the DataFrame so strategies can read it.
            df.attrs["ticker"] = ticker
            for strategy in strategies:
                try:
                    signals = strategy.generate_signals(df)
                    all_signals.extend(signals)
                except Exception:
                    logger.exception(
                        "Strategy '%s' failed on %s", strategy.name, ticker
                    )

        if not all_signals:
            summary = f"Daily cycle complete. No signals generated for {tickers}."
            logger.info(summary)
            return summary

        # 3. Get portfolio state and execute signals.
        try:
            portfolio = self._broker.get_portfolio()
            portfolio_state = _portfolio_to_state(portfolio)
        except Exception:
            logger.exception("Failed to get portfolio state")
            return "Daily cycle failed: could not retrieve portfolio state."

        try:
            results = execute_signals(
                all_signals, self._broker, self._risk_manager, portfolio_state
            )
        except Exception:
            logger.exception("Failed to execute signals")
            return "Daily cycle failed: error during signal execution."

        # Build summary.
        executed = [r for r in results if r.executed]
        rejected = [r for r in results if not r.executed]
        lines: list[str] = [
            f"Daily cycle complete. "
            f"Signals: {len(all_signals)}, "
            f"Executed: {len(executed)}, "
            f"Rejected: {len(rejected)}."
        ]
        for r in executed:
            lines.append(
                f"  {r.signal.action.upper()} {r.signal.ticker} "
                f"(strategy={r.signal.strategy_name}, strength={r.signal.strength:.2f})"
            )
        for r in rejected:
            lines.append(
                f"  REJECTED {r.signal.action.upper()} {r.signal.ticker}: "
                f"{r.rejection_reason}"
            )

        summary = "\n".join(lines)
        logger.info(summary)

        # Persist updated state.
        try:
            updated_portfolio = self._broker.get_portfolio()
            snapshot = {
                "total_equity": updated_portfolio.total_equity,
                "cash": updated_portfolio.cash,
                "positions": [
                    {
                        "ticker": p.ticker,
                        "quantity": p.quantity,
                        "avg_cost": p.avg_cost,
                        "market_value": p.market_value,
                        "unrealized_pnl": p.unrealized_pnl,
                    }
                    for p in updated_portfolio.positions
                ],
                "timestamp": updated_portfolio.timestamp,
            }
            self._state_manager.update_field("portfolio_snapshot", snapshot)
            self._state_manager.update_field(
                "active_strategies", self._registry.list_strategies()
            )
        except Exception:
            logger.exception("Failed to persist state after daily cycle")

        return summary

    # ------------------------------------------------------------------
    # Learning session
    # ------------------------------------------------------------------

    # Map curriculum stage number to the ChromaDB collection name.
    _STAGE_COLLECTION: dict[int, str] = {
        1: "stage_1_foundations",
        2: "stage_2_strategies",
        3: "stage_3_risk_management",
        4: "stage_4_advanced",
    }

    # Mastery increment applied each time a topic is successfully studied.
    _MASTERY_INCREMENT: float = 0.1

    def run_learning_session(self) -> str:
        """Run a knowledge-learning session.

        Fetches content for the current stage's least-mastered topics and
        stores it in the ChromaDB knowledge base.  Source selection is
        stage-aware:

        * **Stages 1–2** (foundations, strategy families) → Wikipedia summaries,
          which give clear conceptual definitions suitable for beginner topics.
        * **Stages 3–4** (risk management, advanced) → arXiv q-fin paper abstracts,
          which give rigorous, technical depth.
        * **Ongoing tasks** → Yahoo Finance RSS, which covers current market news.

        Each fetched document is persisted in the appropriate KnowledgeStore
        collection, and the topic's mastery score is nudged up by
        ``_MASTERY_INCREMENT`` to track progression.

        Returns
        -------
        str
            Human-readable summary of what was studied.
        """
        logger.info("Starting learning session")

        try:
            tasks = self._curriculum.get_next_learning_tasks()
        except Exception:
            logger.exception("Failed to get learning tasks from curriculum")
            return "Learning session failed: could not load curriculum tasks."

        if not tasks:
            summary = "Learning session: no pending topics. All current stage topics mastered."
            logger.info(summary)
            return summary

        current_stage = self._curriculum.get_current_stage()
        collection_name = self._STAGE_COLLECTION.get(current_stage, "general")
        store = KnowledgeStore()

        studied: list[str] = []
        for topic in tasks:
            logger.info(
                "Studying topic: %s (%s) [stage=%d, source=%s]",
                topic.name, topic.id, current_stage,
                "wikipedia" if current_stage <= 2 else "arxiv",
            )

            # --- Fetch from stage-appropriate source --------------------------
            docs = []
            try:
                if current_stage <= 2:
                    docs = fetch_wikipedia(topic.name)
                else:
                    docs = fetch_arxiv(topic.name, max_results=5)
            except Exception:
                logger.exception(
                    "Failed to fetch content for topic '%s'", topic.name
                )

            # --- Store documents in ChromaDB ----------------------------------
            stored_count = 0
            for doc in docs:
                try:
                    store.add_document(doc, collection_name=collection_name)
                    stored_count += 1
                except Exception:
                    logger.exception(
                        "Failed to store document '%s' for topic '%s'",
                        doc.title, topic.name,
                    )

            # --- Nudge mastery score -----------------------------------------
            if stored_count > 0:
                try:
                    current_mastery = self._curriculum.get_mastery(topic.id)
                    new_mastery = min(current_mastery + self._MASTERY_INCREMENT, 1.0)
                    self._curriculum.set_mastery(topic.id, new_mastery)
                    logger.info(
                        "Mastery for '%s' updated: %.0f%% → %.0f%%",
                        topic.id, current_mastery * 100, new_mastery * 100,
                    )
                except Exception:
                    logger.exception(
                        "Failed to update mastery for topic '%s'", topic.id
                    )

            entry_summary = (
                f"Studied '{topic.name}': "
                f"fetched {len(docs)} doc(s), stored {stored_count}."
            )
            studied.append(entry_summary)

            try:
                self._state_manager.add_learning_entry(
                    topic=topic.name, summary=entry_summary
                )
            except Exception:
                logger.exception(
                    "Failed to persist learning entry for '%s'", topic.name
                )

        try:
            self._state_manager.update_field("current_stage", current_stage)
        except Exception:
            logger.exception("Failed to update current_stage in state")

        summary = (
            f"Learning session complete (stage {current_stage}). "
            f"Topics studied: {len(studied)}.\n"
            + "\n".join(f"  - {s}" for s in studied)
        )
        logger.info(summary)
        return summary

    # ------------------------------------------------------------------
    # Daily evaluation
    # ------------------------------------------------------------------

    def run_daily_evaluation(self) -> str:
        """Generate a daily performance evaluation report.

        Returns
        -------
        str
            Performance report string.
        """
        logger.info("Starting daily evaluation")

        # 1. Get portfolio.
        try:
            portfolio = self._broker.get_portfolio()
        except Exception:
            logger.exception("Failed to get portfolio for evaluation")
            return "Daily evaluation failed: could not retrieve portfolio."

        # 2. Get order history.
        try:
            orders = self._broker.get_order_history(limit=50)
        except Exception:
            logger.exception("Failed to get order history")
            orders = []

        # 3. Calculate metrics.
        total_equity = portfolio.total_equity
        cash = portfolio.cash
        position_count = len(portfolio.positions)
        total_unrealized_pnl = sum(p.unrealized_pnl for p in portfolio.positions)
        total_market_value = sum(p.market_value for p in portfolio.positions)

        filled_orders = [o for o in orders if o.status == "filled"]
        buy_count = sum(1 for o in filled_orders if o.side == "buy")
        sell_count = sum(1 for o in filled_orders if o.side == "sell")

        # 4. Build report.
        lines: list[str] = [
            "=== Daily Performance Report ===",
            f"Total Equity:      ${total_equity:,.2f}",
            f"Cash:              ${cash:,.2f}",
            f"Invested:          ${total_market_value:,.2f}",
            f"Unrealized P&L:    ${total_unrealized_pnl:,.2f}",
            f"Open Positions:    {position_count}",
            f"Recent Orders:     {len(filled_orders)} filled "
            f"({buy_count} buys, {sell_count} sells)",
            "",
            "--- Positions ---",
        ]

        if portfolio.positions:
            for pos in portfolio.positions:
                pnl_sign = "+" if pos.unrealized_pnl >= 0 else ""
                lines.append(
                    f"  {pos.ticker}: {pos.quantity} shares @ ${pos.avg_cost:.2f} "
                    f"(mkt ${pos.market_value:,.2f}, P&L {pnl_sign}${pos.unrealized_pnl:,.2f})"
                )
        else:
            lines.append("  (no open positions)")

        lines.append("")
        lines.append(f"Active Strategies: {', '.join(self._registry.list_strategies())}")
        lines.append(f"Curriculum Stage:  {self._curriculum.get_current_stage()}")
        lines.append("=== End Report ===")

        report = "\n".join(lines)
        logger.info("Daily evaluation complete")

        # Persist portfolio snapshot.
        try:
            snapshot = {
                "total_equity": total_equity,
                "cash": cash,
                "positions": [
                    {
                        "ticker": p.ticker,
                        "quantity": p.quantity,
                        "avg_cost": p.avg_cost,
                        "market_value": p.market_value,
                        "unrealized_pnl": p.unrealized_pnl,
                    }
                    for p in portfolio.positions
                ],
                "timestamp": portfolio.timestamp,
            }
            self._state_manager.update_field("portfolio_snapshot", snapshot)
        except Exception:
            logger.exception("Failed to persist portfolio snapshot after evaluation")

        return report

    # ------------------------------------------------------------------
    # Market scan (signal preview without execution)
    # ------------------------------------------------------------------

    def run_market_scan(self, tickers: list[str] | None = None) -> str:
        """Scan tickers for signals without executing any trades.

        Parameters
        ----------
        tickers:
            Symbols to scan.  Defaults to the built-in watchlist.

        Returns
        -------
        str
            Summary of signals found.
        """
        tickers = tickers or _DEFAULT_TICKERS
        logger.info("Starting market scan for tickers: %s", tickers)

        try:
            market_data = get_multiple(tickers)
        except Exception:
            logger.exception("Failed to fetch market data for scan")
            return "Market scan failed: could not fetch market data."

        all_signals: list[Signal] = []
        strategies = self._registry.get_all()

        for ticker, df in market_data.items():
            if df.empty:
                logger.warning("No data for %s, skipping", ticker)
                continue
            df.attrs["ticker"] = ticker
            for strategy in strategies:
                try:
                    signals = strategy.generate_signals(df)
                    all_signals.extend(signals)
                except Exception:
                    logger.exception(
                        "Strategy '%s' failed on %s during scan",
                        strategy.name,
                        ticker,
                    )

        if not all_signals:
            summary = f"Market scan complete. No signals found for {tickers}."
            logger.info(summary)
            return summary

        lines: list[str] = [
            f"Market scan complete. {len(all_signals)} signal(s) found:"
        ]
        for sig in sorted(all_signals, key=lambda s: s.strength, reverse=True):
            lines.append(
                f"  {sig.action.upper()} {sig.ticker} "
                f"(strategy={sig.strategy_name}, strength={sig.strength:.2f}) "
                f"— {sig.reason}"
            )

        summary = "\n".join(lines)
        logger.info(summary)
        return summary

    # ------------------------------------------------------------------
    # Weekly review
    # ------------------------------------------------------------------

    def run_weekly_review(self) -> str:
        """Generate a weekly review combining performance and learning progress.

        Returns
        -------
        str
            Combined weekly review string suitable for messaging delivery.
        """
        logger.info("Starting weekly review")

        perf_report = self.run_daily_evaluation()

        stage = self._curriculum.get_current_stage()
        try:
            tasks = self._curriculum.get_next_learning_tasks()
        except Exception:
            logger.exception("Failed to get learning tasks for weekly review")
            tasks = []

        lines: list[str] = [
            "=== Weekly Review ===",
            "",
            perf_report,
            "",
            "--- Learning Progress ---",
            f"Current Stage: {stage}",
        ]

        if tasks:
            lines.append("Next topics to study:")
            for task in tasks:
                mastery = self._curriculum.get_mastery(task.id)
                lines.append(f"  [{mastery:.0%}] {task.name}")
        else:
            lines.append("All current stage topics mastered.")

        lines.append("=== End Weekly Review ===")
        summary = "\n".join(lines)
        logger.info("Weekly review complete")
        return summary

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> str:
        """Return a human-readable status string.

        Includes portfolio value, active strategies, and curriculum stage.
        """
        try:
            portfolio = self._broker.get_portfolio()
            equity_str = f"${portfolio.total_equity:,.2f}"
            cash_str = f"${portfolio.cash:,.2f}"
            positions_count = len(portfolio.positions)
        except Exception:
            logger.exception("Failed to get portfolio for status")
            equity_str = "N/A"
            cash_str = "N/A"
            positions_count = 0

        strategies = self._registry.list_strategies()
        stage = self._curriculum.get_current_stage()

        lines: list[str] = [
            "=== Trading Agent Status ===",
            f"Portfolio Equity: {equity_str}",
            f"Cash:             {cash_str}",
            f"Open Positions:   {positions_count}",
            f"Active Strategies: {', '.join(strategies) if strategies else '(none)'}",
            f"Curriculum Stage:  {stage}",
            "============================",
        ]
        return "\n".join(lines)
