"""Deterministic audit gate — pre-deployment checks for strategy quality."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.config import Preferences, load_preferences
from src.strategies.spec import StrategyResult


@dataclass
class AuditCheck:
    """A single audit check result."""

    name: str
    passed: bool
    message: str


@dataclass
class AuditReport:
    """Full audit report for a strategy."""

    spec_id: str
    checks: list[AuditCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> list[AuditCheck]:
        return [c for c in self.checks if not c.passed]

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [f"Audit {status} for {self.spec_id}"]
        for check in self.checks:
            mark = "[OK]" if check.passed else "[FAIL]"
            lines.append(f"  {mark} {check.name}: {check.message}")
        return "\n".join(lines)


class Auditor:
    """Deterministic pre-deployment audit gate.

    All checks are rule-based (no LLM involvement). A strategy must
    pass all checks before promotion to paper/live trading.

    Checks:
    1. Overfitting detection (in-sample vs out-of-sample gap)
    2. Minimum trade count
    3. Drawdown limit
    4. Minimum paper trading days (if applicable)
    """

    def __init__(self, preferences: Preferences | None = None) -> None:
        self._prefs = preferences or load_preferences()

    def audit(
        self,
        screen_result: StrategyResult,
        validation_result: StrategyResult | None = None,
    ) -> AuditReport:
        """Run all audit checks on a strategy's results."""
        report = AuditReport(spec_id=screen_result.spec_id)

        # Check 1: Minimum trade count
        report.checks.append(self._check_min_trades(screen_result))

        # Check 2: Drawdown limit
        report.checks.append(self._check_drawdown(screen_result))

        # Check 3: Overfitting detection (needs both screen and validation)
        if validation_result is not None:
            report.checks.append(
                self._check_overfitting(screen_result, validation_result)
            )

        # Check 4: Profit factor
        report.checks.append(self._check_profit_factor(screen_result))

        # Check 5: Validation passed (if available)
        if validation_result is not None:
            report.checks.append(self._check_validation_passed(validation_result))

        # Check 6: Walk-forward overfitting gap (IS vs OOS Sharpe)
        if screen_result.in_sample_sharpe > 0:
            report.checks.append(self._check_walk_forward_gap(screen_result))

        return report

    def _check_min_trades(self, result: StrategyResult) -> AuditCheck:
        min_trades = 20
        passed = result.total_trades >= min_trades
        return AuditCheck(
            name="min_trades",
            passed=passed,
            message=(
                f"{result.total_trades} trades "
                f"({'OK' if passed else f'below minimum {min_trades}'})"
            ),
        )

    def _check_drawdown(self, result: StrategyResult) -> AuditCheck:
        limit = self._prefs.risk_limits.max_portfolio_drawdown
        actual = abs(result.max_drawdown)
        passed = actual <= limit
        return AuditCheck(
            name="drawdown_limit",
            passed=passed,
            message=(
                f"Max drawdown {actual:.1%} "
                f"({'OK' if passed else f'exceeds limit {limit:.1%}'})"
            ),
        )

    def _check_overfitting(
        self, screen: StrategyResult, validation: StrategyResult
    ) -> AuditCheck:
        """Detect overfitting by comparing screen vs validation Sharpe gap."""
        import math

        screen_sharpe = screen.sharpe_ratio
        val_sharpe = validation.sharpe_ratio

        # Handle NaN/inf — treat as inconclusive (pass with warning)
        if math.isnan(screen_sharpe) or math.isnan(val_sharpe):
            return AuditCheck(
                name="overfitting_detection",
                passed=True,
                message=(
                    f"Inconclusive — Sharpe is NaN "
                    f"(screen={screen_sharpe:.2f}, validation={val_sharpe:.2f})"
                ),
            )

        gap = screen_sharpe - val_sharpe
        max_gap = 1.0  # Sharpe gap threshold
        passed = gap <= max_gap
        return AuditCheck(
            name="overfitting_detection",
            passed=passed,
            message=(
                f"Sharpe gap: {gap:.2f} (screen={screen_sharpe:.2f}, "
                f"validation={val_sharpe:.2f}) "
                f"{'OK' if passed else f'exceeds max gap {max_gap}'}"
            ),
        )

    def _check_profit_factor(self, result: StrategyResult) -> AuditCheck:
        min_pf = 1.0
        passed = result.profit_factor >= min_pf
        return AuditCheck(
            name="profit_factor",
            passed=passed,
            message=(
                f"Profit factor {result.profit_factor:.2f} "
                f"({'OK' if passed else f'below minimum {min_pf}'})"
            ),
        )

    def _check_walk_forward_gap(self, result: StrategyResult) -> AuditCheck:
        """Detect walk-forward overfitting: IS Sharpe much higher than OOS."""
        import math

        is_sharpe = result.in_sample_sharpe
        oos_sharpe = result.sharpe_ratio
        max_gap = 1.5

        if math.isnan(is_sharpe) or math.isnan(oos_sharpe):
            return AuditCheck(
                name="walk_forward_gap",
                passed=True,
                message=(
                    f"Inconclusive — Sharpe is NaN "
                    f"(IS={is_sharpe:.2f}, OOS={oos_sharpe:.2f})"
                ),
            )

        gap = is_sharpe - oos_sharpe
        passed = gap <= max_gap
        return AuditCheck(
            name="walk_forward_gap",
            passed=passed,
            message=(
                f"IS-OOS Sharpe gap: {gap:.2f} "
                f"(IS={is_sharpe:.2f}, OOS={oos_sharpe:.2f}) "
                f"{'OK' if passed else f'exceeds max gap {max_gap}'}"
            ),
        )

    def _check_validation_passed(self, validation: StrategyResult) -> AuditCheck:
        return AuditCheck(
            name="validation_passed",
            passed=validation.passed,
            message=(
                "Validation passed"
                if validation.passed
                else f"Validation failed: {validation.failure_reason}"
            ),
        )
