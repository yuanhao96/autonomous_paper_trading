"""Auditor Agent — adversarial inspector for trading strategies and data.

Aggregates all audit checks (look-ahead bias, overfitting, survivorship
bias, data quality) into a unified audit interface.  The auditor has
**read-only** access to the trading agent's code and data — it cannot
modify the trading system, only flag, report, and block promotion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from agents.auditor.checks.data_quality import check_data_quality
from agents.auditor.checks.look_ahead_bias import Finding, check_look_ahead_bias
from agents.auditor.checks.overfitting import check_overfitting
from agents.auditor.checks.survivorship_bias import check_survivorship_bias
from evaluation.metrics import PerformanceSummary

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AuditReport:
    """Result of an audit run, aggregating findings from all checks."""

    passed: bool
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""
    timestamp: str = ""


# ---------------------------------------------------------------------------
# Auditor Agent
# ---------------------------------------------------------------------------


class AuditorAgent:
    """Adversarial auditor that inspects backtest results and market data.

    The auditor runs a battery of checks and produces an ``AuditReport``
    indicating whether the artefact under review is fit for promotion to
    live paper trading.
    """

    def audit_backtest(
        self,
        backtest_result: Any,
        strategy_code: str = "",
        tickers: list[str] | None = None,
        in_sample_metrics: PerformanceSummary | None = None,
        out_of_sample_metrics: PerformanceSummary | None = None,
    ) -> AuditReport:
        """Run all applicable checks against a backtest result.

        Parameters
        ----------
        backtest_result:
            Object with ``trades``, ``equity_curve``, and ``windows_used``
            attributes.
        strategy_code:
            Raw Python source of the strategy (for static analysis).
        tickers:
            Ticker symbols used in the backtest universe.
        in_sample_metrics:
            Performance summary for the in-sample period.
        out_of_sample_metrics:
            Performance summary for the out-of-sample period.

        Returns
        -------
        AuditReport
        """
        all_findings: list[Finding] = []

        # -- Look-ahead bias -----------------------------------------------
        try:
            all_findings.extend(
                check_look_ahead_bias(backtest_result, strategy_code)
            )
        except Exception:
            logger.exception("look_ahead_bias check raised an exception")

        # -- Overfitting (only when both metric sets are provided) ----------
        if in_sample_metrics is not None and out_of_sample_metrics is not None:
            try:
                all_findings.extend(
                    check_overfitting(
                        backtest_result,
                        in_sample_metrics,
                        out_of_sample_metrics,
                    )
                )
            except Exception:
                logger.exception("overfitting check raised an exception")

        # -- Survivorship bias (only when tickers are provided) -------------
        if tickers is not None:
            backtest_start: str = ""
            equity_curve: pd.Series | None = getattr(
                backtest_result, "equity_curve", None
            )
            if equity_curve is not None and not equity_curve.empty:
                try:
                    backtest_start = str(equity_curve.index[0].date())
                except Exception:
                    pass
            try:
                all_findings.extend(
                    check_survivorship_bias(tickers, backtest_start)
                )
            except Exception:
                logger.exception("survivorship_bias check raised an exception")

        # -- Data quality on equity curve -----------------------------------
        equity_curve = getattr(backtest_result, "equity_curve", None)
        if equity_curve is not None and isinstance(equity_curve, pd.Series):
            try:
                # Convert equity curve Series into a single-column DataFrame
                # so the data-quality checks can inspect it.
                eq_df = equity_curve.to_frame(name="Close")
                all_findings.extend(check_data_quality(eq_df))
            except Exception:
                logger.exception("data_quality check raised an exception")

        return self._build_report(all_findings)

    def audit_data(self, data: pd.DataFrame) -> AuditReport:
        """Run data-quality checks only.

        Parameters
        ----------
        data:
            OHLCV DataFrame with a DatetimeIndex.

        Returns
        -------
        AuditReport
        """
        all_findings: list[Finding] = []

        try:
            all_findings.extend(check_data_quality(data))
        except Exception:
            logger.exception("data_quality check raised an exception")

        return self._build_report(all_findings)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_report(findings: list[Finding]) -> AuditReport:
        """Aggregate findings into an ``AuditReport``."""
        has_critical = any(f.severity == "critical" for f in findings)
        passed = not has_critical

        # Build a human-readable summary.
        critical_count = sum(1 for f in findings if f.severity == "critical")
        warning_count = sum(1 for f in findings if f.severity == "warning")
        info_count = sum(1 for f in findings if f.severity == "info")

        if not findings:
            summary = "All checks passed with no findings."
        else:
            parts: list[str] = []
            if critical_count:
                parts.append(f"{critical_count} critical")
            if warning_count:
                parts.append(f"{warning_count} warning(s)")
            if info_count:
                parts.append(f"{info_count} informational")
            summary = (
                f"Audit {'FAILED' if not passed else 'PASSED'} — "
                f"{len(findings)} finding(s): {', '.join(parts)}."
            )

            # Append brief descriptions of critical findings.
            if critical_count:
                summary += "\nCritical issues:"
                for f in findings:
                    if f.severity == "critical":
                        summary += f"\n  - [{f.check_name}] {f.description}"

        timestamp = datetime.now(tz=timezone.utc).isoformat()

        report = AuditReport(
            passed=passed,
            findings=findings,
            summary=summary,
            timestamp=timestamp,
        )

        logger.info("Audit report: passed=%s, findings=%d", passed, len(findings))
        return report
