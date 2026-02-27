"""Tests for the rich diagnostics reporter."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.live.models import ComparisonReport, Deployment, LiveSnapshot, Position, PromotionReport
from src.reporting.reporter import (
    evolution_summary_report,
    format_comparison,
    format_deployment,
    format_promotion,
    format_result,
    format_spec,
    pipeline_status_report,
    strategy_lifecycle_report,
)
from src.strategies.spec import RegimeResult, RiskParams, StrategyResult, StrategySpec


def _make_spec() -> StrategySpec:
    return StrategySpec(
        template="momentum/time-series-momentum",
        parameters={"lookback": 126, "threshold": 0.01},
        universe_id="sp500",
        risk=RiskParams(max_position_pct=0.10, max_positions=5),
    )


def _make_result(phase="screen", passed=True) -> StrategyResult:
    return StrategyResult(
        spec_id="test_spec",
        phase=phase,
        passed=passed,
        sharpe_ratio=1.5,
        annual_return=0.12,
        total_return=0.36,
        max_drawdown=-0.15,
        win_rate=0.55,
        profit_factor=1.8,
        total_trades=50,
        run_duration_seconds=3.2,
    )


def _make_deployment() -> Deployment:
    d = Deployment(
        spec_id="test_spec",
        account_id="paper",
        mode="paper",
        symbols=["SPY", "QQQ"],
        initial_cash=100_000,
    )
    d.status = "active"
    d.snapshots = [
        LiveSnapshot(
            deployment_id=d.id,
            timestamp=datetime.utcnow(),
            equity=102_000,
            cash=30_000,
            positions=[Position("SPY", 100, 450.0, 48_000, 3_000)],
        )
    ]
    return d


class TestFormatSpec:
    def test_contains_key_info(self):
        spec = _make_spec()
        text = format_spec(spec)
        assert "momentum/time-series-momentum" in text
        assert "sp500" in text
        assert "lookback" in text


class TestFormatResult:
    def test_passed_result(self):
        result = _make_result()
        text = format_result(result)
        assert "PASSED" in text
        assert "1.50" in text  # Sharpe
        assert "+12" in text   # Annual return

    def test_failed_result(self):
        result = _make_result(passed=False)
        result.failure_reason = "low_sharpe"
        text = format_result(result)
        assert "FAILED" in text
        assert "low_sharpe" in text

    def test_custom_label(self):
        result = _make_result()
        text = format_result(result, label="CUSTOM")
        assert "[CUSTOM]" in text


class TestFormatDeployment:
    def test_contains_deployment_info(self):
        dep = _make_deployment()
        text = format_deployment(dep)
        assert "paper" in text
        assert "active" in text
        assert "SPY" in text
        assert "$102,000" in text


class TestFormatComparison:
    def test_comparison_output(self):
        cr = ComparisonReport(
            deployment_id="d1",
            days_elapsed=20,
            live_return=0.02,
            expected_annual_return=0.12,
            live_sharpe=1.2,
            expected_sharpe=1.5,
            sharpe_drift=0.3,
            within_tolerance=True,
        )
        text = format_comparison(cr)
        assert "OK" in text
        assert "20 days" in text


class TestFormatPromotion:
    def test_promotion_output(self):
        pr = PromotionReport(
            deployment_id="d1",
            spec_id="test_spec",
            days_elapsed=25,
            min_days_required=20,
            meets_time_requirement=True,
            decision="approved",
            reasoning="All checks passed",
        )
        text = format_promotion(pr)
        assert "APPROVED" in text
        assert "test_spec" in text


class TestStrategyLifecycleReport:
    def test_full_report(self):
        spec = _make_spec()
        results = [_make_result("screen"), _make_result("validate")]
        text = strategy_lifecycle_report(spec, results)
        assert "LIFECYCLE" in text
        assert "SCREEN" in text or "screen" in text

    def test_with_regime_results(self):
        spec = _make_spec()
        result = _make_result()
        result.regime_results = [
            RegimeResult("bull", "2020-01", "2021-06", 0.20, 2.0, -0.10, 30),
            RegimeResult("bear", "2022-01", "2022-06", -0.05, -0.3, -0.25, 10),
        ]
        text = strategy_lifecycle_report(spec, [result])
        assert "bull" in text
        assert "bear" in text


class TestEvolutionSummaryReport:
    def test_report_structure(self):
        cycles = [
            {"cycle_number": 1, "mode": "explore", "specs_generated": 5,
             "specs_screened": 3, "specs_passed": 1, "best_sharpe": 1.5,
             "duration_seconds": 10.0},
        ]
        best = [(_make_spec(), _make_result())]
        text = evolution_summary_report(cycles, best, "1 call, 500 tokens")
        assert "EVOLUTION" in text
        assert "explore" in text
        assert "1.50" in text


class TestPipelineStatusReport:
    def test_report_structure(self):
        text = pipeline_status_report(
            total_specs=10,
            phases={"screened": 10, "validated": 5, "passed": 3},
            active_deployments=1,
            best_sharpe=2.1,
        )
        assert "PIPELINE" in text
        assert "10" in text
        assert "2.10" in text
