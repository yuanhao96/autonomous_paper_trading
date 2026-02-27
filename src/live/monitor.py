"""Monitor — track live performance and compare to backtest expectations.

Monitors:
- Daily P&L and cumulative returns
- Sharpe ratio evolution
- Drawdown tracking
- Drift from validation baseline
- Risk limit violations
"""

from __future__ import annotations

import logging
import math
from datetime import datetime

import numpy as np

from src.core.config import Preferences, Settings, load_preferences
from src.live.models import ComparisonReport, Deployment, LiveSnapshot
from src.risk.engine import RiskEngine, RiskViolation
from src.strategies.spec import StrategyResult

logger = logging.getLogger(__name__)


class Monitor:
    """Live performance monitoring and drift detection.

    Usage:
        monitor = Monitor()
        comparison = monitor.compare(deployment, validation_result)
        violations = monitor.check_risk(deployment)
    """

    def __init__(
        self,
        settings: Settings | None = None,
        preferences: Preferences | None = None,
    ) -> None:
        self._settings = settings or Settings()
        self._prefs = preferences or load_preferences()
        self._risk_engine = RiskEngine(preferences=self._prefs)
        self._tolerance = self._settings.get("live.comparison_tolerance", 0.30)
        self._max_sharpe_drift = self._settings.get("live.max_sharpe_drift", 1.0)
        self._drawdown_alert_pct = self._settings.get("live.drawdown_alert_pct", 0.15)
        self._daily_loss_alert_pct = self._settings.get("live.daily_loss_alert_pct", 0.03)

    def compare(
        self,
        deployment: Deployment,
        validation_result: StrategyResult,
    ) -> ComparisonReport:
        """Compare live performance to validation backtest.

        Args:
            deployment: Active or stopped deployment with snapshots.
            validation_result: The validation backtest result to compare against.

        Returns:
            ComparisonReport with drift metrics and alerts.
        """
        report = ComparisonReport(
            deployment_id=deployment.id,
            days_elapsed=deployment.days_elapsed,
            expected_annual_return=validation_result.annual_return,
            expected_sharpe=validation_result.sharpe_ratio,
            expected_max_drawdown=abs(validation_result.max_drawdown),
        )

        snapshots = deployment.snapshots
        if not snapshots:
            report.alerts.append("No snapshots available")
            report.within_tolerance = False
            return report

        # Compute live metrics from snapshots
        report.live_return = self._compute_return(deployment)
        report.live_sharpe = self._compute_sharpe(deployment)
        report.live_max_drawdown = self._compute_max_drawdown(deployment)

        # Compute drift
        # Annualize the live return for comparison
        if deployment.days_elapsed > 0:
            annualized_live = (1 + report.live_return) ** (252.0 / deployment.days_elapsed) - 1
        else:
            annualized_live = 0.0
        report.return_drift = abs(annualized_live - report.expected_annual_return)
        report.sharpe_drift = abs(report.live_sharpe - report.expected_sharpe)

        # Check tolerance
        alerts: list[str] = []

        # Return drift check
        if report.expected_annual_return != 0:
            relative_return_drift = report.return_drift / abs(report.expected_annual_return)
            if relative_return_drift > self._tolerance:
                alerts.append(
                    f"Return drift {relative_return_drift:.0%} exceeds tolerance {self._tolerance:.0%}"
                )

        # Sharpe drift check
        if report.sharpe_drift > self._max_sharpe_drift:
            alerts.append(
                f"Sharpe drift {report.sharpe_drift:.2f} exceeds max {self._max_sharpe_drift:.2f}"
            )

        # Drawdown check
        if report.live_max_drawdown > self._drawdown_alert_pct:
            alerts.append(
                f"Max drawdown {report.live_max_drawdown:.1%} exceeds alert threshold {self._drawdown_alert_pct:.1%}"
            )

        # Drawdown exceeds backtest
        if report.live_max_drawdown > report.expected_max_drawdown * 1.5:
            alerts.append(
                f"Max drawdown {report.live_max_drawdown:.1%} exceeds 1.5x expected {report.expected_max_drawdown:.1%}"
            )

        report.alerts = alerts
        report.within_tolerance = len(alerts) == 0

        return report

    def check_risk(self, deployment: Deployment) -> list[RiskViolation]:
        """Check if live trading violates risk limits.

        Args:
            deployment: Active deployment with snapshots.

        Returns:
            List of risk violations found.
        """
        violations: list[RiskViolation] = []
        snapshots = deployment.snapshots
        if not snapshots:
            return violations

        latest = snapshots[-1]

        # Portfolio drawdown check
        max_dd = self._compute_max_drawdown(deployment)
        dd_violations = self._risk_engine.check_result_drawdown(max_dd)
        violations.extend(dd_violations)

        # Daily loss check
        if len(snapshots) >= 2:
            prev_equity = snapshots[-2].equity
            if prev_equity > 0:
                daily_loss = (latest.equity - prev_equity) / prev_equity
                if daily_loss < -self._prefs.risk_limits.max_daily_loss:
                    violations.append(RiskViolation(
                        rule="max_daily_loss",
                        limit=self._prefs.risk_limits.max_daily_loss,
                        actual=abs(daily_loss),
                        message=f"Daily loss {abs(daily_loss):.1%} exceeds limit {self._prefs.risk_limits.max_daily_loss:.1%}",
                    ))

        # Position concentration check
        if latest.equity > 0:
            for pos in latest.positions:
                weight = pos.market_value / latest.equity
                if weight > self._prefs.risk_limits.max_position_pct:
                    violations.append(RiskViolation(
                        rule="max_position_pct",
                        limit=self._prefs.risk_limits.max_position_pct,
                        actual=weight,
                        message=f"{pos.symbol} weight {weight:.1%} exceeds limit {self._prefs.risk_limits.max_position_pct:.1%}",
                    ))

        # Max positions check
        if latest.position_count > self._prefs.risk_limits.max_positions:
            violations.append(RiskViolation(
                rule="max_positions",
                limit=self._prefs.risk_limits.max_positions,
                actual=latest.position_count,
                message=f"{latest.position_count} positions exceeds limit {self._prefs.risk_limits.max_positions}",
            ))

        return violations

    def compute_live_result(
        self,
        deployment: Deployment,
        spec_id: str,
    ) -> StrategyResult:
        """Compile live snapshots into a StrategyResult for storage.

        Args:
            deployment: Deployment with snapshots.
            spec_id: Strategy spec ID.

        Returns:
            StrategyResult with phase="live".
        """
        result = StrategyResult(spec_id=spec_id, phase="live")

        if not deployment.snapshots:
            result.failure_reason = "No snapshots"
            return result

        result.total_return = self._compute_return(deployment)
        result.sharpe_ratio = self._compute_sharpe(deployment)
        result.max_drawdown = self._compute_max_drawdown(deployment)
        result.total_trades = len(deployment.trades)
        result.total_fees = sum(t.commission for t in deployment.trades)

        # Annualize
        if deployment.days_elapsed > 0:
            result.annual_return = (1 + result.total_return) ** (252.0 / deployment.days_elapsed) - 1
        result.equity_curve = [s.equity for s in deployment.snapshots]

        # Win rate from trades
        if deployment.trades:
            # Group trades by symbol to compute P&L per round trip
            winning = sum(1 for t in deployment.trades if t.side == "sell" and t.price > 0)
            total = sum(1 for t in deployment.trades if t.side == "sell")
            result.win_rate = winning / total if total > 0 else 0.0

        # Time bounds
        result.backtest_start = deployment.started_at.strftime("%Y-%m-%d")
        end = deployment.stopped_at or datetime.utcnow()
        result.backtest_end = end.strftime("%Y-%m-%d")

        # Passed if no major issues
        violations = self.check_risk(deployment)
        result.passed = len(violations) == 0
        if violations:
            result.failure_reason = f"{len(violations)} risk violations"
            result.failure_details = "; ".join(v.message for v in violations)

        return result

    # ── Metric computations ──────────────────────────────────────────

    def _compute_return(self, deployment: Deployment) -> float:
        """Total return from first to last snapshot."""
        snapshots = deployment.snapshots
        if len(snapshots) < 1:
            return 0.0
        initial = deployment.initial_cash
        final = snapshots[-1].equity
        if initial <= 0:
            return 0.0
        return (final - initial) / initial

    def _compute_sharpe(self, deployment: Deployment) -> float:
        """Annualized Sharpe ratio from daily returns."""
        daily_returns = self._daily_returns(deployment)
        if len(daily_returns) < 2:
            return 0.0
        mean = np.mean(daily_returns)
        std = np.std(daily_returns, ddof=1)
        if std == 0 or math.isnan(std):
            return 0.0
        return float(mean / std * np.sqrt(252))

    def _compute_max_drawdown(self, deployment: Deployment) -> float:
        """Max drawdown from equity curve."""
        snapshots = deployment.snapshots
        if len(snapshots) < 2:
            return 0.0
        equities = [s.equity for s in snapshots]
        peak = equities[0]
        max_dd = 0.0
        for eq in equities:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)
        return max_dd

    def _daily_returns(self, deployment: Deployment) -> list[float]:
        """Compute daily returns from snapshots."""
        snapshots = deployment.snapshots
        if len(snapshots) < 2:
            return []
        returns = []
        for i in range(1, len(snapshots)):
            prev = snapshots[i - 1].equity
            curr = snapshots[i].equity
            if prev > 0:
                returns.append((curr - prev) / prev)
        return returns
