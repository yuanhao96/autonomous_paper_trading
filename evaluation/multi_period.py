"""Multi-period backtesting engine.

Runs a strategy across multiple historical periods (e.g. GFC, COVID,
rate-hiking) with configurable weights and a Sharpe floor check.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from evaluation.backtester import Backtester, BacktestResult
from strategies.base import Strategy
from trading.data import get_ohlcv_range

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PeriodConfig:
    """Configuration for one historical test period."""

    name: str
    start: str
    end: str
    weight: float = 1.0


@dataclass
class PeriodResult:
    """Result of backtesting a strategy on one period."""

    period: PeriodConfig
    backtest_result: BacktestResult
    passed_floor: bool


@dataclass
class MultiPeriodResult:
    """Aggregated result of backtesting across all periods."""

    strategy_name: str
    period_results: list[PeriodResult] = field(default_factory=list)
    composite_score: float = 0.0
    passed_all_floors: bool = True
    disqualified: bool = False
    disqualification_reason: str = ""


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------


def load_period_configs(settings_path: Path | None = None) -> list[PeriodConfig]:
    """Read period configurations from settings.yaml."""
    if settings_path is None:
        settings_path = _PROJECT_ROOT / "config" / "settings.yaml"

    with open(settings_path) as f:
        settings = yaml.safe_load(f) or {}

    evolution = settings.get("evolution", {})
    raw_periods = evolution.get("periods", [])

    periods: list[PeriodConfig] = []
    for p in raw_periods:
        periods.append(
            PeriodConfig(
                name=p["name"],
                start=p["start"],
                end=p["end"],
                weight=float(p.get("weight", 1.0)),
            )
        )
    return periods


def load_evolution_settings(settings_path: Path | None = None) -> dict[str, Any]:
    """Load the full evolution section from settings.yaml."""
    if settings_path is None:
        settings_path = _PROJECT_ROOT / "config" / "settings.yaml"

    with open(settings_path) as f:
        settings = yaml.safe_load(f) or {}

    return settings.get("evolution", {})


# ---------------------------------------------------------------------------
# Multi-period backtester
# ---------------------------------------------------------------------------


class MultiPeriodBacktester:
    """Run a strategy across multiple historical periods and score it."""

    def __init__(
        self,
        periods: list[PeriodConfig] | None = None,
        min_sharpe_floor: float = -0.5,
        ticker: str = "SPY",
        data_fetcher: Any = None,
    ) -> None:
        self._periods = periods or load_period_configs()
        self._min_sharpe_floor = min_sharpe_floor
        self._ticker = ticker
        self._data_fetcher = data_fetcher or get_ohlcv_range
        self._backtester = Backtester()

    def run(self, strategy: Strategy) -> MultiPeriodResult:
        """Backtest *strategy* across all configured periods."""
        result = MultiPeriodResult(strategy_name=strategy.name)
        total_weighted_sharpe = 0.0
        total_weight = 0.0

        for period in self._periods:
            try:
                data = self._data_fetcher(
                    self._ticker, start=period.start, end=period.end
                )
            except Exception:
                logger.exception(
                    "Failed to fetch data for period '%s' (%s to %s)",
                    period.name, period.start, period.end,
                )
                result.disqualified = True
                result.disqualification_reason = (
                    f"Data fetch failed for period '{period.name}'"
                )
                return result

            if data.empty:
                logger.warning("Empty data for period '%s', skipping", period.name)
                continue

            data.attrs["ticker"] = self._ticker

            bt_result = self._backtester.run(strategy, data)
            sharpe = bt_result.metrics.sharpe_ratio
            passed_floor = sharpe >= self._min_sharpe_floor

            period_result = PeriodResult(
                period=period,
                backtest_result=bt_result,
                passed_floor=passed_floor,
            )
            result.period_results.append(period_result)

            if not passed_floor:
                result.passed_all_floors = False
                result.disqualified = True
                result.disqualification_reason = (
                    f"Sharpe {sharpe:.3f} < floor {self._min_sharpe_floor} "
                    f"in period '{period.name}'"
                )

            total_weighted_sharpe += period.weight * sharpe
            total_weight += period.weight

        if total_weight > 0 and not result.disqualified:
            result.composite_score = total_weighted_sharpe / total_weight

        return result

    @staticmethod
    def rank(results: list[MultiPeriodResult]) -> list[MultiPeriodResult]:
        """Sort results by composite_score (descending), disqualified last."""
        return sorted(
            results,
            key=lambda r: (not r.disqualified, r.composite_score),
            reverse=True,
        )
