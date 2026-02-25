"""Tournament selection for strategy evolution.

Backtests a batch of strategies, ranks them, and selects the top N
survivors for the next generation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from evaluation.multi_period import MultiPeriodBacktester, MultiPeriodResult
from strategies.base import Strategy

logger = logging.getLogger(__name__)


@dataclass
class TournamentResult:
    """Outcome of one tournament cycle."""

    all_results: list[MultiPeriodResult] = field(default_factory=list)
    survivors: list[MultiPeriodResult] = field(default_factory=list)
    eliminated: list[MultiPeriodResult] = field(default_factory=list)
    cycle_number: int = 0


class Tournament:
    """Run a tournament: backtest all strategies and select top N."""

    def __init__(
        self,
        backtester: MultiPeriodBacktester,
        survivor_count: int = 3,
    ) -> None:
        self._backtester = backtester
        self._survivor_count = survivor_count

    def run(
        self,
        strategies: list[Strategy],
        cycle_number: int = 0,
    ) -> TournamentResult:
        """Backtest all strategies and select top survivors.

        Parameters
        ----------
        strategies:
            Candidate strategies to evaluate.
        cycle_number:
            Current evolution cycle number (for record-keeping).

        Returns
        -------
        TournamentResult
        """
        all_results: list[MultiPeriodResult] = []

        for strategy in strategies:
            logger.info("Tournament: backtesting '%s'", strategy.name)
            try:
                result = self._backtester.run(strategy)
                all_results.append(result)
            except Exception:
                logger.exception(
                    "Tournament: backtest failed for '%s'", strategy.name
                )
                all_results.append(
                    MultiPeriodResult(
                        strategy_name=strategy.name,
                        disqualified=True,
                        disqualification_reason="Backtest raised an exception",
                    )
                )

        ranked = self._backtester.rank(all_results)

        survivors = ranked[: self._survivor_count]
        eliminated = ranked[self._survivor_count:]

        logger.info(
            "Tournament cycle %d: %d candidates, %d survivors, best score %.4f",
            cycle_number,
            len(all_results),
            len(survivors),
            survivors[0].composite_score if survivors else 0.0,
        )

        return TournamentResult(
            all_results=ranked,
            survivors=survivors,
            eliminated=eliminated,
            cycle_number=cycle_number,
        )
