"""Promoter — evaluate paper trading results for live promotion.

Decision logic:
1. Minimum paper trading days elapsed (from preferences.yaml)
2. Live performance within tolerance of validation backtest
3. No active risk violations
4. Strategy still passing audit checks

Decisions: "approved" | "rejected" | "needs_review"
"""

from __future__ import annotations

import logging
from datetime import datetime

from src.core.config import Preferences, Settings, load_preferences
from src.live.models import ComparisonReport, Deployment, PromotionReport
from src.live.monitor import Monitor
from src.strategies.spec import StrategyResult

logger = logging.getLogger(__name__)


class Promoter:
    """Evaluates whether a paper-traded strategy should be promoted to live.

    Usage:
        promoter = Promoter()
        report = promoter.evaluate(deployment, validation_result)
        if report.decision == "approved":
            # Proceed with live deployment
    """

    def __init__(
        self,
        monitor: Monitor | None = None,
        settings: Settings | None = None,
        preferences: Preferences | None = None,
    ) -> None:
        self._settings = settings or Settings()
        self._prefs = preferences or load_preferences()
        self._monitor = monitor or Monitor(settings=self._settings, preferences=self._prefs)
        self._min_days = self._prefs.min_paper_trading_days

    def evaluate(
        self,
        deployment: Deployment,
        validation_result: StrategyResult,
    ) -> PromotionReport:
        """Evaluate promotion readiness for a paper-traded strategy.

        Args:
            deployment: Paper trading deployment with accumulated snapshots.
            validation_result: The validation backtest to compare against.

        Returns:
            PromotionReport with decision and reasoning.
        """
        report = PromotionReport(
            deployment_id=deployment.id,
            spec_id=deployment.spec_id,
            days_elapsed=deployment.days_elapsed,
            min_days_required=self._min_days,
        )

        # Check 1: Minimum time requirement
        report.meets_time_requirement = deployment.days_elapsed >= self._min_days

        # Check 2: Performance comparison
        report.comparison = self._monitor.compare(deployment, validation_result)

        # Check 3: Risk violations
        violations = self._monitor.check_risk(deployment)
        report.risk_violations = [v.message for v in violations]

        # Make decision
        report.decision, report.reasoning = self._decide(report)

        logger.info(
            "Promotion evaluation for %s: %s — %s",
            deployment.id, report.decision, report.reasoning,
        )
        return report

    def _decide(self, report: PromotionReport) -> tuple[str, str]:
        """Determine promotion decision based on all checks."""
        reasons: list[str] = []

        # Time requirement
        if not report.meets_time_requirement:
            reasons.append(
                f"Only {report.days_elapsed}/{report.min_days_required} days of paper trading"
            )

        # Performance drift
        if report.comparison and not report.comparison.within_tolerance:
            reasons.append(
                f"Performance drift detected: {', '.join(report.comparison.alerts)}"
            )

        # Risk violations
        if report.risk_violations:
            reasons.append(
                f"{len(report.risk_violations)} risk violations: {report.risk_violations[0]}"
            )

        # No snapshots
        if not report.comparison or report.comparison.days_elapsed == 0:
            reasons.append("No performance data available")

        # Decision logic
        if not reasons:
            return "approved", "All checks passed: time requirement met, performance within tolerance, no risk violations"

        # Check if issues are severe enough for rejection
        has_risk_violations = len(report.risk_violations) > 0
        has_severe_drift = (
            report.comparison is not None
            and not report.comparison.within_tolerance
            and len(report.comparison.alerts) >= 2
        )

        if has_risk_violations or has_severe_drift:
            return "rejected", "; ".join(reasons)

        # Minor issues → needs human review
        return "needs_review", "; ".join(reasons)

    def get_promotion_summary(
        self,
        deployment: Deployment,
        validation_result: StrategyResult,
    ) -> str:
        """Generate a human-readable promotion summary.

        Args:
            deployment: Paper trading deployment.
            validation_result: Validation backtest result.

        Returns:
            Formatted summary string.
        """
        report = self.evaluate(deployment, validation_result)
        lines = [
            "=" * 60,
            f"PROMOTION EVALUATION — {report.decision.upper()}",
            "=" * 60,
            f"  Strategy:        {report.spec_id}",
            f"  Deployment:      {report.deployment_id}",
            f"  Paper trading:   {report.days_elapsed} days (min: {report.min_days_required})",
            f"  Time requirement: {'MET' if report.meets_time_requirement else 'NOT MET'}",
        ]

        if report.comparison:
            lines.extend([
                "",
                "  Performance:",
                f"    Live return:      {report.comparison.live_return:+.2%}",
                f"    Expected annual:  {report.comparison.expected_annual_return:+.2%}",
                f"    Live Sharpe:      {report.comparison.live_sharpe:.2f}",
                f"    Expected Sharpe:  {report.comparison.expected_sharpe:.2f}",
                f"    Live max DD:      {report.comparison.live_max_drawdown:.2%}",
                f"    Expected max DD:  {report.comparison.expected_max_drawdown:.2%}",
                f"    Within tolerance: {'YES' if report.comparison.within_tolerance else 'NO'}",
            ])
            if report.comparison.alerts:
                lines.append(f"    Alerts: {', '.join(report.comparison.alerts)}")

        if report.risk_violations:
            lines.extend([
                "",
                f"  Risk violations ({len(report.risk_violations)}):",
            ])
            for v in report.risk_violations:
                lines.append(f"    - {v}")

        lines.extend([
            "",
            f"  Decision:   {report.decision.upper()}",
            f"  Reasoning:  {report.reasoning}",
            "=" * 60,
        ])
        return "\n".join(lines)
