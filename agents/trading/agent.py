"""Main trading agent for V1 scope.

Orchestrates the daily trading cycle, learning sessions, evaluations,
and market scans.  Each method is designed to be called from OpenClaw
cron jobs or tool invocations.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from agents.trading.state import StateManager
from core.preferences import load_preferences
from knowledge.curriculum import CurriculumTracker
from knowledge.ingestion import fetch_alpaca_news, fetch_arxiv, fetch_book_text, fetch_wikipedia
from knowledge.learning_controller import LearningController
from knowledge.store import MarkdownMemory
from knowledge.synthesizer import KnowledgeSynthesizer
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

    def __init__(self, mock: bool = False) -> None:
        self._broker = PaperBroker(mock=mock)

        preferences = load_preferences()
        self._risk_manager = RiskManager(preferences)
        self._memory = MarkdownMemory()
        self._synthesizer = KnowledgeSynthesizer()
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
    # Book knowledge helpers
    # ------------------------------------------------------------------

    def _load_books_config(self) -> dict[str, list[str]]:
        """Load the topic→books mapping from ``config/books.yaml``.

        Returns a dict of ``{topic_id: [filename, ...]}`` or an empty dict
        on any error.
        """
        config_path = Path("config/books.yaml")
        if not config_path.exists():
            logger.warning("books.yaml not found at %s; skipping book ingestion.", config_path)
            return {}
        try:
            with open(config_path, "r") as fh:
                data = yaml.safe_load(fh) or {}
            return {k: v for k, v in data.items() if isinstance(v, list)}
        except Exception:
            logger.exception("Failed to load books.yaml")
            return {}

    def _get_books_dir(self) -> str:
        """Return the path to the investment books directory.

        Priority: ``BOOKS_DIR`` env var → ``settings.yaml data.books_dir``.
        """
        env_dir = os.getenv("BOOKS_DIR", "")
        if env_dir:
            return str(Path(env_dir).expanduser())

        try:
            import yaml as _yaml
            with open("config/settings.yaml", "r") as fh:
                settings = _yaml.safe_load(fh) or {}
            books_dir = settings.get("data", {}).get("books_dir", "")
            if books_dir:
                return str(Path(books_dir).expanduser())
        except Exception:
            pass
        return str(Path("~/projects/investment-books-text").expanduser())

    def _fetch_topic_books(self, topic_id: str, topic_name: str) -> list:
        """Return ``Document`` objects from books mapped to *topic_id*.

        Reads ``config/books.yaml`` for the topic→filenames mapping and
        calls :func:`~knowledge.ingestion.fetch_book_text` for each file.
        At most one book's chunks are loaded per learning session call to
        control LLM token usage; books are rotated across sessions via
        a simple round-robin based on the topic's current mastery score.

        Parameters
        ----------
        topic_id:
            Curriculum topic identifier (e.g. ``"momentum"``).
        topic_name:
            Human-readable name used as ``topic_hint`` for tagging.

        Returns
        -------
        list[Document]
            Combined list of chunked document objects, or an empty list.
        """
        books_map = self._load_books_config()
        book_files = books_map.get(topic_id, [])
        if not book_files:
            logger.debug("No books configured for topic '%s'.", topic_id)
            return []

        books_dir = self._get_books_dir()

        # Rotate which book to use based on how many times we've studied this
        # topic (approximated via mastery score bucket).
        mastery = self._curriculum.get_mastery(topic_id)
        book_index = int(mastery * 10) % len(book_files)
        chosen = book_files[book_index]

        book_path = os.path.join(books_dir, chosen)
        docs = fetch_book_text(book_path, topic_hint=topic_name)

        if not docs:
            logger.warning(
                "No content loaded from book '%s' for topic '%s'.", chosen, topic_id
            )
        else:
            logger.info(
                "Loaded %d chunk(s) from '%s' for topic '%s'.",
                len(docs), chosen, topic_id,
            )
        return docs

    def _load_learning_settings(self) -> dict[str, Any]:
        """Load learning settings from ``config/settings.yaml``."""
        config_path = Path("config/settings.yaml")
        if not config_path.exists():
            return {}
        try:
            with open(config_path, "r") as fh:
                data = yaml.safe_load(fh) or {}
            learning = data.get("learning", {})
            return learning if isinstance(learning, dict) else {}
        except Exception:
            logger.exception("Failed to load learning settings")
            return {}

    def _extract_discovered_topic_candidates(
        self,
        source_topic_name: str,
        key_concepts: list[str],
    ) -> list[str]:
        """Extract conservative candidate topic names from synthesis concepts."""
        source_lower = source_topic_name.strip().lower()
        candidates: list[str] = []
        seen: set[str] = set()

        for raw in key_concepts:
            name = str(raw).strip(" -\t\r\n")
            if not name:
                continue
            if len(name) < 4 or len(name) > 60:
                continue
            words = name.split()
            if len(words) > 6:
                continue
            lower = name.lower()
            if lower == source_lower:
                continue
            if lower in seen:
                continue
            seen.add(lower)
            candidates.append(name)

        return candidates

    def _auto_add_discovered_topics(
        self,
        current_stage: int,
        source_topic_name: str,
        key_concepts: list[str],
    ) -> list[str]:
        """Auto-add newly discovered topics to ``config/curriculum.yaml``."""
        cfg = self._load_learning_settings()
        enabled = bool(cfg.get("auto_add_discovered_topics", True))
        if not enabled:
            return []

        max_new = int(cfg.get("auto_add_max_per_topic", 2))
        if max_new <= 0:
            return []

        added_names: list[str] = []
        candidates = self._extract_discovered_topic_candidates(
            source_topic_name, key_concepts
        )
        for name in candidates:
            if len(added_names) >= max_new:
                break
            try:
                added, topic_id = self._curriculum.add_discovered_topic(
                    name=name,
                    description=f"Discovered during study of '{source_topic_name}'.",
                    stage_number=current_stage,
                )
                if added:
                    added_names.append(name)
                    logger.info(
                        "Auto-added discovered topic '%s' (id=%s, stage=%d)",
                        name,
                        topic_id,
                        current_stage,
                    )
            except Exception:
                logger.exception("Failed to auto-add discovered topic '%s'", name)
        return added_names

    # ------------------------------------------------------------------
    # Evolution cycle
    # ------------------------------------------------------------------

    def run_evolution_cycle(self, trigger: str = "manual") -> str:
        """Run one evolution cycle to generate and evaluate strategy candidates.

        Creates an ``EvolutionCycle`` wired with the agent's memory and
        curriculum instances, runs it, and returns a human-readable summary.
        """
        from evolution.cycle import EvolutionCycle
        from evolution.store import EvolutionStore

        try:
            store = EvolutionStore()
            cycle = EvolutionCycle(store=store)
            result = cycle.run(trigger=trigger)

            summary = (
                f"Evolution cycle {result.cycle_id}: "
                f"generated {result.specs_generated} specs, "
                f"compiled {result.specs_compiled}, "
                f"best score {result.best_score:.3f}"
            )
            if result.exhaustion_detected:
                summary += " (exhaustion detected)"

            logger.info(summary)
            return summary
        except Exception:
            logger.exception("Evolution cycle failed")
            return "Evolution cycle failed."

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

    def run_learning_session(self) -> str:
        """Run a knowledge-learning session.

        Fetches content for the current stage's least-mastered topics,
        synthesizes it via LLM, and stores the result as structured markdown
        in the knowledge memory.  Source selection is stage-aware:

        * **Stages 1-2** (foundations, strategy families) -> Wikipedia summaries.
        * **Stages 3-4** (risk management, advanced) -> arXiv q-fin abstracts.
        * **Ongoing tasks** -> Alpaca news for the watchlist tickers.

        Mastery is assessed by the LLM based on accumulated knowledge rather
        than incremented by a fixed amount.

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

        # Build the multi-round learning controller once per session.
        controller = LearningController(
            memory=self._memory,
            synthesizer=self._synthesizer,
            curriculum=self._curriculum,
        )
        logger.info(
            "LearningController ready (max_rounds=%d, threshold=%.2f, budget=%d tokens)",
            controller.max_rounds, controller.confidence_threshold, controller.per_topic_budget,
        )

        studied: list[str] = []
        for topic in tasks:
            logger.info(
                "Studying topic: %s (%s) [stage=%d]", topic.name, topic.id, current_stage,
            )

            # --- Multi-round retrieval + synthesis via LearningController -----
            try:
                knowledge, state = controller.learn_topic(topic)
            except Exception:
                logger.exception("LearningController failed for topic '%s'", topic.name)
                studied.append(f"Studied '{topic.name}': controller failed.")
                continue

            docs = state.evidence_pool
            if not docs:
                studied.append(f"Studied '{topic.name}': no documents retrieved.")
                continue

            # Log confidence trajectory
            for entry in state.round_log:
                logger.info(
                    "  Round %d | tools: %-35s | docs: %2d | confidence: %.2f",
                    entry["round"] + 1, ", ".join(entry["tools"]),
                    entry["docs_retrieved"], entry["confidence"],
                )
            if state.gaps:
                logger.info("  Unresolved gaps (%d): %s", len(state.gaps), state.gaps[:3])
            if state.conflicts:
                logger.info("  Conflicts detected: %d", len(state.conflicts))
            logger.info(
                "  Final: %d docs | %d source types | confidence=%.2f",
                len(docs), state.source_diversity(), state.confidence,
            )

            # --- Append evidence pool to daily log ----------------------------
            for doc in docs[:10]:
                try:
                    self._memory.append_daily_log(doc)
                except Exception:
                    logger.exception("Failed to log document '%s'", doc.title)

            # --- Build synthesized markdown with evidence trail ---------------
            sections: list[str] = []
            if knowledge.summary:
                sections.append(knowledge.summary)
            if knowledge.key_concepts:
                sections.append("**Key concepts:** " + ", ".join(knowledge.key_concepts))
            if knowledge.trading_implications:
                sections.append(
                    "**Trading implications:**\n"
                    + "\n".join(f"- {imp}" for imp in knowledge.trading_implications)
                )
            if knowledge.risk_factors:
                sections.append(
                    "**Risk factors:**\n"
                    + "\n".join(f"- {rf}" for rf in knowledge.risk_factors)
                )
            # Append evidence trail (claims with citations)
            if getattr(knowledge, "claims", None):
                trail = "\n".join(
                    f"- [{c.get('confidence','?')}] {c.get('claim','')} "
                    f"*(source: {c.get('source_title','?')})*"
                    for c in knowledge.claims[:10]
                )
                sections.append(f"**Evidence trail:**\n{trail}")
            if state.conflicts:
                conflict_lines = "\n".join(
                    f"- ⚠️ {cf.get('claim_a','')} ↔ {cf.get('claim_b','')}"
                    for cf in state.conflicts[:3]
                )
                sections.append(f"**Unresolved conflicts:**\n{conflict_lines}")
            synthesized_md = "\n\n".join(sections)

            # --- Store synthesized knowledge ----------------------------------
            try:
                self._memory.store_curriculum_knowledge(
                    topic_id=topic.id,
                    stage_number=current_stage,
                    doc=docs[0],
                    synthesized_content=synthesized_md,
                )
            except Exception:
                logger.exception("Failed to store knowledge for topic '%s'", topic.name)

            # --- Assess mastery from accumulated content ----------------------
            try:
                accumulated = self._memory.get_topic_content(topic.id, current_stage)
                score, reasoning, gaps = self._synthesizer.assess_mastery(
                    topic_id=topic.id,
                    topic_name=topic.name,
                    topic_description=topic.description,
                    mastery_criteria=topic.mastery_criteria,
                    learned_content=accumulated[:4000],
                )
                old_mastery = self._curriculum.get_mastery(topic.id)
                self._curriculum.set_mastery(topic.id, score, notes=reasoning)
                logger.info(
                    "Mastery for '%s': %.0f%% -> %.0f%% | rounds=%d | diversity=%d | gaps=%d",
                    topic.id, old_mastery * 100, score * 100,
                    state.round_idx, state.source_diversity(), len(gaps),
                )
            except Exception:
                logger.exception("Failed to assess mastery for topic '%s'", topic.id)

            discovered_topics: list[str] = []
            try:
                discovered_topics = self._auto_add_discovered_topics(
                    current_stage=current_stage,
                    source_topic_name=topic.name,
                    key_concepts=knowledge.key_concepts,
                )
            except Exception:
                logger.exception(
                    "Failed discovered-topic auto-add for topic '%s'", topic.id
                )

            entry_summary = (
                f"Studied '{topic.name}': {len(docs)} doc(s) across "
                f"{state.round_idx} round(s), {state.source_diversity()} source type(s), "
                f"confidence={state.confidence:.2f}."
            )
            if discovered_topics:
                entry_summary += (
                    " Added discovered topics: " + ", ".join(discovered_topics) + "."
                )
            studied.append(entry_summary)

            try:
                self._state_manager.add_learning_entry(
                    topic=topic.name, summary=entry_summary
                )
            except Exception:
                logger.exception("Failed to persist learning entry for '%s'", topic.name)

        # ------------------------------------------------------------------
        # Ongoing tasks — use Alpaca news for the watchlist tickers
        # ------------------------------------------------------------------
        ongoing_tasks = self._curriculum.get_ongoing_tasks()
        for task in ongoing_tasks:
            task_id: str = task.get("id", "")
            task_name: str = task.get("name", task_id)
            logger.info("Running ongoing task: %s", task_name)

            docs = []
            try:
                docs = fetch_alpaca_news(
                    tickers=_DEFAULT_TICKERS, max_results=20
                )
            except Exception:
                logger.exception(
                    "Failed to fetch Alpaca news for ongoing task '%s'", task_name
                )

            logged_count = 0
            for doc in docs:
                try:
                    self._memory.append_daily_log(doc)
                    logged_count += 1
                except Exception:
                    logger.exception(
                        "Failed to log Alpaca news article '%s'", doc.title
                    )

            entry_summary = (
                f"Ongoing '{task_name}': "
                f"fetched {len(docs)} article(s), logged {logged_count}."
            )
            studied.append(entry_summary)
            logger.info(entry_summary)

            # Only run the news fetch once even if multiple ongoing tasks
            # are defined — they all hit the same endpoint.
            break

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
