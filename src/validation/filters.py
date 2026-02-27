"""Validation pass/fail filters — stricter than screening filters.

After realistic cost modeling, strategy must still meet thresholds.
Performance drop from screening is expected (costs eat alpha).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.config import Settings
from src.strategies.spec import RegimeResult, StrategyResult
from src.validation.capacity import CapacityEstimate


@dataclass
class ValidationFilterResult:
    """Result of applying validation filters."""

    passed: bool
    checks: dict[str, bool]
    details: dict[str, str]

    @property
    def failure_reason(self) -> str | None:
        if self.passed:
            return None
        failed = [name for name, ok in self.checks.items() if not ok]
        return ", ".join(failed)


class ValidationFilters:
    """Apply pass/fail criteria to validation results.

    Criteria from settings.yaml (validation section):
    - min_sharpe: Minimum Sharpe ratio (lower than screening — costs degrade it)
    - max_drawdown: Maximum allowed drawdown
    - min_positive_regimes: Must be positive in ≥ N of 4 regimes
    - min_capacity: Minimum dollar capacity
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()

    def apply(
        self,
        result: StrategyResult,
        capacity: CapacityEstimate | None = None,
    ) -> ValidationFilterResult:
        """Apply all validation filters."""
        criteria = self._get_criteria()
        checks: dict[str, bool] = {}
        details: dict[str, str] = {}

        # Sharpe ratio (lower threshold than screening)
        min_sharpe = criteria["min_sharpe"]
        checks["min_sharpe"] = result.sharpe_ratio >= min_sharpe
        details["min_sharpe"] = f"Sharpe {result.sharpe_ratio:.2f} vs min {min_sharpe}"

        # Max drawdown
        max_dd = criteria["max_drawdown"]
        checks["max_drawdown"] = abs(result.max_drawdown) <= max_dd
        details["max_drawdown"] = f"MaxDD {abs(result.max_drawdown):.1%} vs limit {max_dd:.1%}"

        # Regime performance
        min_positive = criteria["min_positive_regimes"]
        positive_regimes = sum(
            1 for r in result.regime_results if r.annual_return > 0
        )
        checks["min_positive_regimes"] = positive_regimes >= min_positive
        details["min_positive_regimes"] = (
            f"{positive_regimes} positive regimes vs min {min_positive}"
        )

        # Capacity
        if capacity is not None:
            min_cap = criteria["min_capacity"]
            checks["min_capacity"] = capacity.max_capital >= min_cap
            details["min_capacity"] = (
                f"Capacity ${capacity.max_capital:,.0f} vs min ${min_cap:,.0f}"
            )

        return ValidationFilterResult(
            passed=all(checks.values()),
            checks=checks,
            details=details,
        )

    def _get_criteria(self) -> dict[str, Any]:
        return {
            "min_sharpe": self._settings.get("validation.pass_criteria.min_sharpe", 0.3),
            "max_drawdown": self._settings.get("validation.pass_criteria.max_drawdown", 0.35),
            "min_positive_regimes": self._settings.get(
                "validation.pass_criteria.min_positive_regimes", 2
            ),
            "min_capacity": self._settings.get("validation.pass_criteria.min_capacity", 50000),
        }
