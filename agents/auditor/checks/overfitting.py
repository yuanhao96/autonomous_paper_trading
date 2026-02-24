"""Overfitting detection by comparing in-sample vs out-of-sample metrics.

Flags strategies whose in-sample performance is dramatically better than
out-of-sample, which is a strong signal that the strategy has been
curve-fitted to historical noise rather than capturing genuine edge.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.auditor.checks.look_ahead_bias import Finding
from evaluation.metrics import PerformanceSummary

logger = logging.getLogger(__name__)


def check_overfitting(
    backtest_result: Any,
    in_sample_metrics: PerformanceSummary,
    out_of_sample_metrics: PerformanceSummary,
) -> list[Finding]:
    """Compare in-sample and out-of-sample metrics to detect overfitting.

    Parameters
    ----------
    backtest_result:
        The full backtest result object (reserved for future use by
        additional heuristics).
    in_sample_metrics:
        Performance summary computed on the training / in-sample period.
    out_of_sample_metrics:
        Performance summary computed on the held-out / out-of-sample period.

    Returns
    -------
    list[Finding]
        All overfitting-related findings.
    """
    findings: list[Finding] = []

    is_sharpe = in_sample_metrics.sharpe_ratio
    oos_sharpe = out_of_sample_metrics.sharpe_ratio
    is_wr = in_sample_metrics.win_rate
    oos_wr = out_of_sample_metrics.win_rate
    is_dd = in_sample_metrics.max_drawdown
    oos_dd = out_of_sample_metrics.max_drawdown

    # ------------------------------------------------------------------
    # 1. Sharpe ratio degradation
    # ------------------------------------------------------------------
    if oos_sharpe != 0.0 and is_sharpe > 2.0 * oos_sharpe:
        findings.append(
            Finding(
                check_name="overfitting",
                severity="warning",
                description=(
                    "In-sample Sharpe ratio is more than 2x the "
                    "out-of-sample Sharpe ratio, suggesting overfitting."
                ),
                evidence=(
                    f"In-sample Sharpe: {is_sharpe:.2f}, "
                    f"Out-of-sample Sharpe: {oos_sharpe:.2f} "
                    f"(ratio: {is_sharpe / oos_sharpe:.1f}x)"
                ),
            )
        )

    # ------------------------------------------------------------------
    # 2. Win-rate drop
    # ------------------------------------------------------------------
    win_rate_diff = is_wr - oos_wr
    if win_rate_diff > 0.15:
        findings.append(
            Finding(
                check_name="overfitting",
                severity="warning",
                description=(
                    "Win rate drops significantly out-of-sample, "
                    "indicating the strategy may be overfit."
                ),
                evidence=(
                    f"In-sample win rate: {is_wr:.2%}, "
                    f"Out-of-sample win rate: {oos_wr:.2%} "
                    f"(delta: {win_rate_diff:.2%})"
                ),
            )
        )

    # ------------------------------------------------------------------
    # 3. Drawdown divergence
    # ------------------------------------------------------------------
    if oos_dd > 0.0 and is_dd < 0.5 * oos_dd:
        findings.append(
            Finding(
                check_name="overfitting",
                severity="warning",
                description=(
                    "In-sample max drawdown is less than half of the "
                    "out-of-sample max drawdown, suggesting the strategy "
                    "was optimised to avoid in-sample drawdowns."
                ),
                evidence=(
                    f"In-sample max drawdown: {is_dd:.2%}, "
                    f"Out-of-sample max drawdown: {oos_dd:.2%}"
                ),
            )
        )

    # ------------------------------------------------------------------
    # 4. Complete out-of-sample failure
    # ------------------------------------------------------------------
    if oos_sharpe < 0.0 and is_sharpe > 1.0:
        findings.append(
            Finding(
                check_name="overfitting",
                severity="critical",
                description=(
                    "Strategy has a negative out-of-sample Sharpe ratio "
                    "despite a strong in-sample Sharpe (>1.0). The "
                    "strategy almost certainly does not generalise."
                ),
                evidence=(
                    f"In-sample Sharpe: {is_sharpe:.2f}, "
                    f"Out-of-sample Sharpe: {oos_sharpe:.2f}"
                ),
            )
        )

    logger.info(
        "overfitting check complete: %d finding(s)",
        len(findings),
    )
    return findings
