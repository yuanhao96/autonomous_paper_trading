"""Rich diagnostics reviewer — formats strategy results for LLM feedback.

Converts StrategySpec + StrategyResult pairs into structured text that the
LLM can analyze to decide on next evolution steps (parameter tuning, template
switching, universe modifications, etc.).
"""

from __future__ import annotations

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
