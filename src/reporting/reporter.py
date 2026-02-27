"""Rich diagnostics reporter — formatted strategy lifecycle reports.

Provides human-readable reports for:
  - Strategy screening results
  - Validation results with regime analysis
  - Live deployment status
  - Evolution cycle summaries
  - Full pipeline diagnostics
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.live.models import ComparisonReport, Deployment, PromotionReport
from src.strategies.spec import RegimeResult, StrategyResult, StrategySpec


def format_spec(spec: StrategySpec) -> str:
    """Format a strategy spec for display."""
    lines = [
        f"Strategy: {spec.template}",
        f"  ID:         {spec.id}",
        f"  Universe:   {spec.universe_id}",
        f"  Parameters: {spec.parameters}",
        f"  Risk:       max_pos={spec.risk.max_position_pct:.0%}, "
        f"max_n={spec.risk.max_positions}, "
        f"sizing={spec.risk.position_size_method}",
    ]
    if spec.risk.stop_loss_pct:
        lines.append(f"  Stop loss:  {spec.risk.stop_loss_pct:.1%}")
    if spec.parent_id:
        lines.append(f"  Parent:     {spec.parent_id} (gen {spec.generation})")
    lines.append(f"  Created:    {spec.created_by} @ {spec.created_at:%Y-%m-%d %H:%M}")
    return "\n".join(lines)


def format_result(result: StrategyResult, label: str | None = None) -> str:
    """Format a single strategy result for display."""
    tag = label or result.phase.upper()
    status = "PASSED" if result.passed else "FAILED"
    lines = [
        f"[{tag}] {status}",
        f"  Sharpe:   {result.sharpe_ratio:.2f}",
        f"  Return:   {result.annual_return:+.1%} annual, {result.total_return:+.1%} total",
        f"  MaxDD:    {result.max_drawdown:.1%}",
        f"  WinRate:  {result.win_rate:.0%}",
        f"  PF:       {result.profit_factor:.2f}",
        f"  Trades:   {result.total_trades}",
    ]
    if result.failure_reason:
        lines.append(f"  Failure:  {result.failure_reason}")
    if result.failure_details:
        lines.append(f"  Details:  {result.failure_details}")
    if result.run_duration_seconds > 0:
        lines.append(f"  Duration: {result.run_duration_seconds:.1f}s")
    return "\n".join(lines)


def format_regime_results(regimes: list[RegimeResult]) -> str:
    """Format regime analysis results."""
    if not regimes:
        return "  No regime analysis available."
    lines = ["  Regime Performance:"]
    for r in regimes:
        lines.append(
            f"    {r.regime:10s}  Sharpe={r.sharpe_ratio:5.2f}  "
            f"Return={r.annual_return:+6.1%}  MaxDD={r.max_drawdown:6.1%}  "
            f"Trades={r.total_trades:4d}  ({r.period_start}→{r.period_end})"
        )
    return "\n".join(lines)


def format_deployment(deployment: Deployment) -> str:
    """Format a live deployment for display."""
    lines = [
        f"Deployment: {deployment.id}",
        f"  Strategy:  {deployment.spec_id}",
        f"  Mode:      {deployment.mode}",
        f"  Status:    {deployment.status}",
        f"  Symbols:   {', '.join(deployment.symbols)}",
        f"  Cash:      ${deployment.initial_cash:,.0f}",
        f"  Started:   {deployment.started_at:%Y-%m-%d %H:%M}",
        f"  Days:      {deployment.days_elapsed}",
        f"  Snapshots: {len(deployment.snapshots)}",
        f"  Trades:    {len(deployment.trades)}",
    ]
    if deployment.snapshots:
        latest = deployment.snapshots[-1]
        lines.append(f"  Equity:    ${latest.equity:,.2f}")
        lines.append(f"  Invested:  {latest.invested_pct:.0%}")
    return "\n".join(lines)


def format_comparison(comparison: ComparisonReport) -> str:
    """Format a live-vs-validation comparison."""
    return comparison.summary()


def format_promotion(report: PromotionReport) -> str:
    """Format a promotion evaluation."""
    return report.summary()


# ── Composite reports ────────────────────────────────────────────────


def strategy_lifecycle_report(
    spec: StrategySpec,
    results: list[StrategyResult],
    deployment: Deployment | None = None,
    comparison: ComparisonReport | None = None,
    promotion: PromotionReport | None = None,
) -> str:
    """Full lifecycle report for a single strategy."""
    sep = "=" * 70
    lines = [
        sep,
        "STRATEGY LIFECYCLE REPORT",
        sep,
        "",
        format_spec(spec),
        "",
    ]

    for result in results:
        lines.append(format_result(result))
        if result.regime_results:
            lines.append(format_regime_results(result.regime_results))
        lines.append("")

    if deployment:
        lines.append(format_deployment(deployment))
        lines.append("")

    if comparison:
        lines.append(format_comparison(comparison))
        lines.append("")

    if promotion:
        lines.append(format_promotion(promotion))
        lines.append("")

    lines.append(sep)
    return "\n".join(lines)


def evolution_summary_report(
    cycle_results: list[dict[str, Any]],
    best_specs: list[tuple[StrategySpec, StrategyResult]],
    llm_usage: str = "",
) -> str:
    """Summary report for evolution session."""
    sep = "=" * 70
    total_generated = sum(c.get("specs_generated", 0) for c in cycle_results)
    total_passed = sum(c.get("specs_passed", 0) for c in cycle_results)

    lines = [
        sep,
        "EVOLUTION SESSION REPORT",
        sep,
        "",
        f"  Cycles:     {len(cycle_results)}",
        f"  Generated:  {total_generated}",
        f"  Passed:     {total_passed}",
    ]

    if llm_usage:
        lines.append(f"  LLM Usage:  {llm_usage}")
    lines.append("")

    # Per-cycle summary
    lines.append("  Cycle History:")
    for c in cycle_results:
        mode = c.get("mode", "?")
        gen = c.get("specs_generated", 0)
        scr = c.get("specs_screened", 0)
        passed = c.get("specs_passed", 0)
        best = c.get("best_sharpe", 0)
        dur = c.get("duration_seconds", 0)
        lines.append(
            f"    Cycle {c.get('cycle_number', '?'):2d} [{mode:7s}] "
            f"{gen}→{scr}→{passed}  best_sharpe={best:.2f}  ({dur:.1f}s)"
        )

    # Top strategies
    if best_specs:
        lines.append("")
        lines.append("  Top Strategies:")
        for spec, result in best_specs[:5]:
            lines.append(
                f"    {spec.template:40s}  Sharpe={result.sharpe_ratio:.2f}  "
                f"Return={result.annual_return:+.1%}  "
                f"{'PASSED' if result.passed else 'FAILED'}"
            )

    lines.append("")
    lines.append(sep)
    return "\n".join(lines)


def pipeline_status_report(
    total_specs: int,
    phases: dict[str, int],
    active_deployments: int = 0,
    best_sharpe: float = 0.0,
) -> str:
    """Quick status report for the full pipeline."""
    sep = "-" * 50
    lines = [
        sep,
        "PIPELINE STATUS",
        sep,
        f"  Total strategies:     {total_specs}",
    ]
    for phase, count in phases.items():
        lines.append(f"  {phase:22s} {count}")
    lines.append(f"  Active deployments:   {active_deployments}")
    if best_sharpe > 0:
        lines.append(f"  Best Sharpe:          {best_sharpe:.2f}")
    lines.append(sep)
    return "\n".join(lines)
