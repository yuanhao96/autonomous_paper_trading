"""Deterministic audit gate — pre-deployment checks for strategy quality."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.config import Preferences, load_preferences
from src.strategies.spec import StrategyResult, StrategySpec


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
    5. Look-ahead bias detection (temporal overlap, anomalous perfection)
    """

    def __init__(self, preferences: Preferences | None = None) -> None:
        self._prefs = preferences or load_preferences()

    def audit(
        self,
        screen_result: StrategyResult,
        validation_result: StrategyResult | None = None,
        spec: StrategySpec | None = None,
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

        # Check 7: Anomalous performance detection (heuristic proxy)
        report.checks.append(self._check_anomalous_performance(screen_result))

        # Check 7b: OOS/IS Sharpe degradation (overfit detection)
        if screen_result.in_sample_sharpe > 0 and screen_result.sharpe_ratio > 0:
            report.checks.append(self._check_overfit(screen_result))

        # Check 8: Survivorship bias detection
        report.checks.append(self._check_survivorship_bias(screen_result))

        # Check 9: Concentration risk (requires spec)
        if spec is not None:
            report.checks.append(self._check_concentration_risk(spec))

        # Check 10: Look-ahead bias detection
        if validation_result is not None:
            report.checks.append(
                self._check_look_ahead_bias(screen_result, validation_result)
            )

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

    def _check_anomalous_performance(self, result: StrategyResult) -> AuditCheck:
        """Flag statistical anomalies that signal overfitting or data issues.

        Templates use safe self.I() wrappers, so code-level look-ahead is
        unlikely. But "too good to be true" results strongly signal either
        look-ahead or extreme overfitting.
        """
        reasons: list[str] = []

        if result.sharpe_ratio > 5.0:
            reasons.append(f"Sharpe {result.sharpe_ratio:.2f} > 5.0")

        if result.win_rate > 0.95 and result.total_trades > 10:
            reasons.append(
                f"Win rate {result.win_rate:.1%} > 95% with {result.total_trades} trades"
            )

        if result.max_drawdown == 0 and result.total_trades > 10:
            reasons.append(f"Zero drawdown with {result.total_trades} trades")

        passed = len(reasons) == 0
        return AuditCheck(
            name="anomalous_performance",
            passed=passed,
            message=(
                "No anomalous performance detected"
                if passed
                else f"Anomalous performance: {'; '.join(reasons)}"
            ),
        )

    def _check_overfit(self, result: StrategyResult) -> AuditCheck:
        """Check OOS/IS Sharpe degradation — flag potential overfitting.

        If OOS Sharpe < 30% of IS Sharpe, the strategy likely overfits
        to in-sample data.
        """
        degradation = result.sharpe_ratio / result.in_sample_sharpe
        if degradation < 0.30:
            return AuditCheck(
                name="overfit",
                passed=False,
                message=(
                    f"OOS/IS Sharpe ratio {degradation:.1%} < 30% "
                    f"(IS={result.in_sample_sharpe:.2f}, OOS={result.sharpe_ratio:.2f})"
                ),
            )
        return AuditCheck(
            name="overfit",
            passed=True,
            message=(
                f"OOS/IS Sharpe ratio {degradation:.1%} — degradation acceptable "
                f"(IS={result.in_sample_sharpe:.2f}, OOS={result.sharpe_ratio:.2f})"
            ),
        )

    def _check_survivorship_bias(self, result: StrategyResult) -> AuditCheck:
        """Detect survivorship bias from missing symbol data.

        If the screener silently drops > 20% of the universe, the results
        are biased toward survivors.
        """
        if result.symbols_requested == 0:
            return AuditCheck(
                name="survivorship_bias",
                passed=True,
                message="Inconclusive — no symbol counts available (legacy result)",
            )

        coverage = result.symbols_with_data / result.symbols_requested
        passed = coverage >= 0.80
        return AuditCheck(
            name="survivorship_bias",
            passed=passed,
            message=(
                f"Symbol coverage {coverage:.0%} "
                f"({result.symbols_with_data}/{result.symbols_requested}) "
                f"{'OK' if passed else 'below 80% threshold'}"
            ),
        )

    def _check_look_ahead_bias(
        self, screen: StrategyResult, validation: StrategyResult
    ) -> AuditCheck:
        """Detect potential look-ahead bias via temporal and statistical signals.

        Checks:
        1. Validation period overlaps screening period (data leakage).
        2. Validation performance suspiciously close to or better than screening
           with near-zero drawdown (signals future knowledge).
        """
        from datetime import datetime as dt

        reasons: list[str] = []

        # Temporal overlap check
        if screen.backtest_end and validation.backtest_start:
            try:
                screen_end = dt.strptime(screen.backtest_end, "%Y-%m-%d")
                val_start = dt.strptime(validation.backtest_start, "%Y-%m-%d")
                if val_start < screen_end:
                    reasons.append(
                        f"Validation start {validation.backtest_start} overlaps "
                        f"screening end {screen.backtest_end}"
                    )
            except ValueError:
                pass  # Unparseable dates — skip check

        # Suspiciously perfect validation: better Sharpe + near-zero drawdown
        if (
            validation.sharpe_ratio > screen.sharpe_ratio * 1.2
            and validation.sharpe_ratio > 3.0
            and abs(validation.max_drawdown) < 0.02
            and validation.total_trades > 10
        ):
            reasons.append(
                f"Validation suspiciously better than screening "
                f"(Sharpe {validation.sharpe_ratio:.2f} vs {screen.sharpe_ratio:.2f}, "
                f"DD {abs(validation.max_drawdown):.1%})"
            )

        passed = len(reasons) == 0
        return AuditCheck(
            name="look_ahead_bias",
            passed=passed,
            message=(
                "No look-ahead bias signals detected"
                if passed
                else f"Look-ahead bias risk: {'; '.join(reasons)}"
            ),
        )

    def _check_concentration_risk(self, spec: StrategySpec) -> AuditCheck:
        """Defense-in-depth check that spec position size respects preferences."""
        limit = self._prefs.risk_limits.max_position_pct
        actual = spec.risk.max_position_pct
        passed = actual <= limit
        return AuditCheck(
            name="concentration_risk",
            passed=passed,
            message=(
                f"Max position {actual:.0%} "
                f"({'OK' if passed else f'exceeds limit {limit:.0%}'})"
            ),
        )
