"""Pass/fail filters for screening results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.config import Settings
from src.strategies.spec import StrategyResult


@dataclass
class FilterResult:
    """Result of applying screening filters."""

    passed: bool
    checks: dict[str, bool]
    details: dict[str, str]

    @property
    def failure_reason(self) -> str | None:
        if self.passed:
            return None
        failed = [name for name, ok in self.checks.items() if not ok]
        return ", ".join(failed)


class ScreeningFilters:
    """Apply pass/fail criteria to screening results.

    Criteria from settings.yaml:
    - min_sharpe: Minimum Sharpe ratio (walk-forward, out-of-sample)
    - max_drawdown: Maximum allowed drawdown
    - min_trades: Minimum trade count for statistical significance
    - min_profit_factor: Minimum profit factor
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()

    def apply(self, result: StrategyResult) -> FilterResult:
        """Apply all screening filters to a result."""
        criteria = self._get_criteria()
        checks: dict[str, bool] = {}
        details: dict[str, str] = {}

        # Sharpe ratio
        min_sharpe = criteria["min_sharpe"]
        checks["min_sharpe"] = result.sharpe_ratio >= min_sharpe
        details["min_sharpe"] = f"Sharpe {result.sharpe_ratio:.2f} vs min {min_sharpe}"

        # Max drawdown
        max_dd = criteria["max_drawdown"]
        checks["max_drawdown"] = abs(result.max_drawdown) <= max_dd
        details["max_drawdown"] = f"MaxDD {abs(result.max_drawdown):.1%} vs limit {max_dd:.1%}"

        # Minimum trades
        min_trades = criteria["min_trades"]
        checks["min_trades"] = result.total_trades >= min_trades
        details["min_trades"] = f"{result.total_trades} trades vs min {min_trades}"

        # Profit factor
        min_pf = criteria["min_profit_factor"]
        checks["min_profit_factor"] = result.profit_factor >= min_pf
        details["min_profit_factor"] = f"PF {result.profit_factor:.2f} vs min {min_pf}"

        return FilterResult(
            passed=all(checks.values()),
            checks=checks,
            details=details,
        )

    def _get_criteria(self) -> dict[str, Any]:
        return {
            "min_sharpe": self._settings.get("screening.pass_criteria.min_sharpe", 0.5),
            "max_drawdown": self._settings.get("screening.pass_criteria.max_drawdown", 0.30),
            "min_trades": self._settings.get("screening.pass_criteria.min_trades", 20),
            "min_profit_factor": self._settings.get("screening.pass_criteria.min_profit_factor", 1.2),
        }
