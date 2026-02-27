"""Rich diagnostics reviewer — formats strategy results for LLM feedback.

Converts StrategySpec + StrategyResult pairs into structured text that the
LLM can analyze to decide on next evolution steps (parameter tuning, template
switching, universe modifications, etc.).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.strategies.spec import StrategyResult, StrategySpec


def format_result_for_llm(
    spec: StrategySpec,
    screen_result: StrategyResult | None = None,
    validation_result: StrategyResult | None = None,
) -> str:
    """Format a strategy's results as structured text for LLM analysis.

    Returns a multi-line string with strategy details, screening results,
    validation results (with regime breakdown), and failure analysis.
    """
    lines: list[str] = []

    # Strategy identity
    lines.append(f"Strategy: {spec.template} (v{spec.version})")
    lines.append(f"Name: {spec.name}")
    lines.append(f"Parameters: {spec.parameters}")
    lines.append(f"Universe: {spec.universe_id}")
    lines.append(f"Risk: position={spec.risk.max_position_pct:.0%}, "
                 f"max_positions={spec.risk.max_positions}, "
                 f"method={spec.risk.position_size_method}")
    if spec.parent_id:
        lines.append(f"Parent: {spec.parent_id} (gen {spec.generation})")
    lines.append(f"Created by: {spec.created_by}")
    lines.append("")

    # Screening result
    if screen_result is not None:
        status = "PASS" if screen_result.passed else "FAIL"
        lines.append(f"SCREENING RESULT: {status}")
        lines.append(f"  Sharpe: {screen_result.sharpe_ratio:.2f}")
        lines.append(f"  Annual Return: {screen_result.annual_return:.2%}")
        lines.append(f"  Total Return: {screen_result.total_return:.2%}")
        lines.append(f"  Max Drawdown: {screen_result.max_drawdown:.2%}")
        lines.append(f"  Win Rate: {screen_result.win_rate:.2%}")
        lines.append(f"  Profit Factor: {screen_result.profit_factor:.2f}")
        lines.append(f"  Trades: {screen_result.total_trades}")
        if screen_result.failure_reason:
            lines.append(f"  FAILURE: {screen_result.failure_reason}")
            if screen_result.failure_details:
                lines.append(f"  Details: {screen_result.failure_details}")
        if screen_result.optimized_parameters:
            lines.append(f"  Optimized params: {screen_result.optimized_parameters}")
        lines.append("")

    # Validation result
    if validation_result is not None:
        status = "PASS" if validation_result.passed else "FAIL"
        lines.append(f"VALIDATION RESULT: {status}")
        lines.append(f"  Sharpe: {validation_result.sharpe_ratio:.2f}")
        lines.append(f"  Annual Return: {validation_result.annual_return:.2%}")
        lines.append(f"  Max Drawdown: {validation_result.max_drawdown:.2%}")
        lines.append(f"  Trades: {validation_result.total_trades}")
        lines.append(f"  Fees: {validation_result.total_fees:.4f}")
        lines.append(f"  Slippage: {validation_result.total_slippage:.4f}")

        if validation_result.failure_reason:
            lines.append(f"  FAILURE: {validation_result.failure_reason}")
            if validation_result.failure_details:
                lines.append(f"  Details: {validation_result.failure_details}")

        # Regime breakdown
        if validation_result.regime_results:
            lines.append("")
            lines.append("  Regime Breakdown:")
            for rr in validation_result.regime_results:
                sign = "+" if rr.annual_return > 0 else "-"
                lines.append(
                    f"    [{sign}] {rr.regime:10s} "
                    f"Return={rr.annual_return:7.2%}  "
                    f"Sharpe={rr.sharpe_ratio:5.2f}  "
                    f"MaxDD={rr.max_drawdown:7.2%}  "
                    f"Trades={rr.total_trades}"
                )

        # Sharpe degradation
        if screen_result is not None and screen_result.sharpe_ratio > 0:
            degradation = screen_result.sharpe_ratio - validation_result.sharpe_ratio
            pct = degradation / screen_result.sharpe_ratio * 100
            lines.append("")
            lines.append(f"  Sharpe Degradation: {degradation:.2f} ({pct:.0f}%)")

        lines.append("")

    return "\n".join(lines)


def format_history_for_llm(
    history: list[tuple[StrategySpec, StrategyResult]],
    max_entries: int = 10,
) -> str:
    """Format recent evolution history as a summary table for LLM context.

    Args:
        history: List of (spec, best_result) tuples, most recent first.
        max_entries: Max entries to include.

    Returns:
        Formatted text summarizing past strategy attempts.
    """
    if not history:
        return "No previous strategies tested."

    lines = [
        "EVOLUTION HISTORY (most recent first):",
        f"{'Template':35s} {'By':12s} {'Sharpe':>7s} {'Return':>8s} {'MaxDD':>7s} {'Trades':>7s} {'Pass':>5s}",
        "-" * 85,
    ]

    for spec, result in history[:max_entries]:
        template = spec.template.split("/")[-1][:34]
        lines.append(
            f"{template:35s} {spec.created_by:12s} "
            f"{result.sharpe_ratio:7.2f} {result.annual_return:8.2%} "
            f"{result.max_drawdown:7.2%} {result.total_trades:7d} "
            f"{'Y' if result.passed else 'N':>5s}"
        )

    lines.append(f"\nTotal strategies tested: {len(history)}")
    passed = sum(1 for _, r in history if r.passed)
    lines.append(f"Passed: {passed}/{len(history)}")

    if history:
        best = max(history, key=lambda p: p[1].sharpe_ratio)
        lines.append(f"Best Sharpe: {best[1].sharpe_ratio:.2f} ({best[0].template})")

    return "\n".join(lines)


def format_failure_analysis(results: list[tuple[StrategySpec, StrategyResult]]) -> str:
    """Analyze common failure patterns across multiple strategy results.

    Returns text summarizing why strategies are failing, to help the LLM
    avoid repeating the same mistakes.
    """
    if not results:
        return "No failed strategies to analyze."

    failures: dict[str, int] = {}
    for _, result in results:
        if not result.passed and result.failure_reason:
            for reason in result.failure_reason.split(";"):
                reason = reason.strip()
                if reason:
                    failures[reason] = failures.get(reason, 0) + 1

    if not failures:
        return "No failure patterns detected."

    lines = ["FAILURE ANALYSIS:"]
    for reason, count in sorted(failures.items(), key=lambda x: -x[1]):
        lines.append(f"  {reason}: {count} occurrences")

    # Actionable suggestions
    lines.append("\nSuggested actions:")
    if failures.get("min_trades", 0) > 0:
        lines.append("  - Low trade count: try shorter lookback periods or more liquid universes")
    if failures.get("min_sharpe", 0) > 0:
        lines.append("  - Low Sharpe: try different templates or add risk filters (e.g., market state)")
    if failures.get("max_drawdown", 0) > 0:
        lines.append("  - High drawdown: add stop-loss parameters or reduce position sizes")
    if failures.get("min_positive_regimes", 0) > 0:
        lines.append("  - Poor regime performance: try strategies that adapt to market conditions")

    return "\n".join(lines)


def format_param_optimization_insights(
    specs: list[StrategySpec],
    results: list[StrategyResult],
) -> str:
    """Summarize parameter optimization insights from screening results.

    Compares original parameters (from specs) with optimized parameters
    (from results) to show which parameter shifts improved performance.
    Groups by template slug to identify template-specific sweet spots.
    """
    # Pair specs with results that have optimized params
    insights: list[dict[str, Any]] = []
    result_by_spec: dict[str, StrategyResult] = {r.spec_id: r for r in results}
    for spec in specs:
        result = result_by_spec.get(spec.id)
        if result is None or not result.optimized_parameters:
            continue
        shifts: dict[str, str] = {}
        for key, opt_val in result.optimized_parameters.items():
            orig_val = spec.parameters.get(key)
            if orig_val is not None and orig_val != opt_val:
                shifts[key] = f"{orig_val}→{opt_val}"
        if shifts:
            insights.append({
                "template": spec.template,
                "sharpe": result.sharpe_ratio,
                "shifts": shifts,
            })

    if not insights:
        return ""

    # Group by template
    by_template: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in insights:
        by_template[item["template"]].append(item)

    lines = ["PARAMETER OPTIMIZATION INSIGHTS:"]
    for template, items in sorted(by_template.items()):
        slug = template.split("/")[-1] if "/" in template else template
        lines.append(f"  Template {slug}:")
        for item in items:
            shift_parts = [f"{k}: {v}" for k, v in item["shifts"].items()]
            lines.append(f"    Sharpe {item['sharpe']:.2f} — {', '.join(shift_parts)}")

    return "\n".join(lines)


def format_overfitting_analysis(cross_phase: list[dict[str, Any]]) -> str:
    """Analyze screening→validation gaps to detect overfitting patterns.

    Args:
        cross_phase: List of dicts with keys:
            spec_id, template, screen_sharpe, val_sharpe,
            screen_passed, val_passed, parameters

    Returns:
        Formatted text with overfit rate, Sharpe degradation, and
        template-level breakdown.
    """
    if not cross_phase:
        return "No cross-phase data available for overfitting analysis."

    total = len(cross_phase)
    screen_pass_val_fail = [
        r for r in cross_phase if r["screen_passed"] and not r["val_passed"]
    ]
    overfit_count = len(screen_pass_val_fail)
    overfit_pct = overfit_count / total * 100

    # Average Sharpe degradation (screen → validation)
    degradations: list[float] = []
    for r in cross_phase:
        if r["screen_sharpe"] is not None and r["val_sharpe"] is not None:
            degradations.append(r["screen_sharpe"] - r["val_sharpe"])

    avg_degradation = sum(degradations) / len(degradations) if degradations else 0.0

    lines = [
        "OVERFITTING ANALYSIS (screen → validation):",
        f"  Strategies analyzed: {total}",
        f"  Overfit rate (screen pass, val fail): {overfit_pct:.0f}% ({overfit_count}/{total})",
        f"  Avg Sharpe degradation: {avg_degradation:.2f}",
    ]

    # Template-level overfit rates
    by_template: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in cross_phase:
        by_template[r["template"]].append(r)

    template_overfit: list[tuple[str, float, int]] = []
    for template, items in by_template.items():
        overfit_in_template = sum(
            1 for r in items if r["screen_passed"] and not r["val_passed"]
        )
        if len(items) >= 2:
            rate = overfit_in_template / len(items) * 100
            template_overfit.append((template, rate, len(items)))

    if template_overfit:
        template_overfit.sort(key=lambda x: -x[1])
        lines.append("  Templates by overfit rate:")
        for template, rate, count in template_overfit:
            slug = template.split("/")[-1] if "/" in template else template
            lines.append(f"    {slug}: {rate:.0f}% ({count} strategies)")

    return "\n".join(lines)


def format_parameter_insights(
    specs: list[StrategySpec],
    results: list[StrategyResult],
) -> str:
    """Cross-strategy parameter analysis.

    Groups by template, computes correlation between parameter values
    and outcomes. Reports universe/category insights and per-template
    parameter ranges correlated with high/low Sharpe.
    """
    if not specs or not results:
        return ""

    result_by_spec: dict[str, StrategyResult] = {r.spec_id: r for r in results}
    paired: list[tuple[StrategySpec, StrategyResult]] = []
    for spec in specs:
        result = result_by_spec.get(spec.id)
        if result is not None:
            paired.append((spec, result))

    if not paired:
        return ""

    lines: list[str] = ["PARAMETER INSIGHTS:"]
    _append_universe_insights(lines, paired)
    _append_category_insights(lines, paired)
    _append_parameter_correlations(lines, paired)

    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def _append_universe_insights(
    lines: list[str],
    paired: list[tuple[StrategySpec, StrategyResult]],
) -> None:
    """Rank universes by average Sharpe ratio."""
    by_universe: dict[str, list[float]] = defaultdict(list)
    for spec, result in paired:
        by_universe[spec.universe_id].append(result.sharpe_ratio)

    if not by_universe:
        return

    ranked = sorted(
        ((u, sum(v) / len(v), len(v)) for u, v in by_universe.items()),
        key=lambda x: -x[1],
    )
    lines.append("  Universe performance:")
    for universe, avg_sharpe, count in ranked:
        lines.append(f"    {universe}: avg Sharpe {avg_sharpe:.2f} ({count} strategies)")


def _append_category_insights(
    lines: list[str],
    paired: list[tuple[StrategySpec, StrategyResult]],
) -> None:
    """Rank strategy categories by average Sharpe ratio."""
    by_category: dict[str, list[float]] = defaultdict(list)
    for spec, result in paired:
        category = spec.template.split("/")[0] if "/" in spec.template else "other"
        by_category[category].append(result.sharpe_ratio)

    if not by_category:
        return

    ranked = sorted(
        ((c, sum(v) / len(v), len(v)) for c, v in by_category.items()),
        key=lambda x: -x[1],
    )
    lines.append("  Category performance:")
    for category, avg_sharpe, count in ranked:
        lines.append(f"    {category}: avg Sharpe {avg_sharpe:.2f} ({count} strategies)")


def _append_parameter_correlations(
    lines: list[str],
    paired: list[tuple[StrategySpec, StrategyResult]],
) -> None:
    """For each template with ≥3 results, correlate parameter values with Sharpe.

    Splits results into top-half and bottom-half by Sharpe, compares mean
    parameter values. Reports parameters where the difference is >0.1 Sharpe.
    """
    by_template: dict[str, list[tuple[StrategySpec, StrategyResult]]] = defaultdict(list)
    for spec, result in paired:
        by_template[spec.template].append((spec, result))

    has_correlations = False
    for template, items in sorted(by_template.items()):
        if len(items) < 3:
            if not has_correlations:
                msg = "  Parameter correlations: insufficient data"
                lines.append(f"{msg} (<3 results per template)")
                has_correlations = True
            continue

        # Sort by Sharpe
        items.sort(key=lambda x: x[1].sharpe_ratio, reverse=True)
        mid = len(items) // 2
        top_half = items[:mid] if mid > 0 else items[:1]
        bottom_half = items[mid:] if mid > 0 else items[1:]

        # Find all numeric params
        all_params: set[str] = set()
        for spec, _ in items:
            for key, val in spec.parameters.items():
                if isinstance(val, (int, float)):
                    all_params.add(key)

        slug = template.split("/")[-1] if "/" in template else template
        template_lines: list[str] = []
        for param in sorted(all_params):
            top_vals = [
                s.parameters[param] for s, _ in top_half
                if param in s.parameters and isinstance(s.parameters[param], (int, float))
            ]
            bottom_vals = [
                s.parameters[param] for s, _ in bottom_half
                if param in s.parameters and isinstance(s.parameters[param], (int, float))
            ]

            if not top_vals or not bottom_vals:
                continue

            top_mean = sum(top_vals) / len(top_vals)
            bottom_mean = sum(bottom_vals) / len(bottom_vals)
            top_sharpe_mean = sum(r.sharpe_ratio for _, r in top_half) / len(top_half)
            bottom_sharpe_mean = sum(r.sharpe_ratio for _, r in bottom_half) / len(bottom_half)
            sharpe_diff = top_sharpe_mean - bottom_sharpe_mean

            if abs(sharpe_diff) > 0.1:
                template_lines.append(
                    f"      {param}: top-half avg={top_mean:.1f}, "
                    f"bottom-half avg={bottom_mean:.1f} "
                    f"(Sharpe diff: {sharpe_diff:+.2f})"
                )

        if template_lines:
            if not has_correlations:
                lines.append("  Parameter correlations:")
                has_correlations = True
            lines.append(f"    Template {slug}:")
            lines.extend(template_lines)
