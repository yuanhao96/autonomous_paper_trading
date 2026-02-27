"""Tests for risk engine and auditor."""

import pytest

from src.core.config import Preferences, RiskLimits
from src.risk.auditor import Auditor, AuditReport
from src.risk.engine import RiskEngine, RiskViolation
from src.strategies.spec import RiskParams, StrategyResult, StrategySpec


@pytest.fixture
def prefs():
    return Preferences(
        risk_limits=RiskLimits(
            max_position_pct=0.10,
            max_portfolio_drawdown=0.25,
            max_daily_loss=0.05,
            max_leverage=1.0,
            max_positions=20,
            min_cash_reserve_pct=0.05,
        ),
        allowed_asset_classes=("us_equity", "etf"),
        audit_gate_enabled=True,
        min_paper_trading_days=20,
    )


@pytest.fixture
def risk_engine(prefs):
    return RiskEngine(preferences=prefs)


# ── Risk Engine Tests ────────────────────────────────────────────────


class TestRiskEngine:
    def test_valid_spec_passes(self, risk_engine):
        spec = StrategySpec(
            template="t",
            parameters={},
            universe_id="u",
            risk=RiskParams(max_position_pct=0.05, max_positions=10),
        )
        violations = risk_engine.check_spec(spec)
        assert len(violations) == 0

    def test_position_size_violation(self, risk_engine):
        spec = StrategySpec(
            template="t",
            parameters={},
            universe_id="u",
            risk=RiskParams(max_position_pct=0.20),  # exceeds 0.10 limit
        )
        violations = risk_engine.check_spec(spec)
        assert len(violations) == 1
        assert violations[0].rule == "max_position_pct"

    def test_max_positions_violation(self, risk_engine):
        spec = StrategySpec(
            template="t",
            parameters={},
            universe_id="u",
            risk=RiskParams(max_positions=50),  # exceeds 20 limit
        )
        violations = risk_engine.check_spec(spec)
        assert any(v.rule == "max_positions" for v in violations)

    def test_clamp_spec(self, risk_engine):
        spec = StrategySpec(
            template="t",
            parameters={},
            universe_id="u",
            risk=RiskParams(max_position_pct=0.50, max_positions=100),
        )
        clamped = risk_engine.clamp_spec(spec)
        assert clamped.risk.max_position_pct == 0.10
        assert clamped.risk.max_positions == 20
        assert clamped.id == spec.id  # Same identity

    def test_drawdown_check(self, risk_engine):
        violations = risk_engine.check_result_drawdown(0.15)
        assert len(violations) == 0

        violations = risk_engine.check_result_drawdown(0.30)
        assert len(violations) == 1

    def test_asset_class_allowed(self, risk_engine):
        assert risk_engine.is_asset_class_allowed("us_equity")
        assert risk_engine.is_asset_class_allowed("etf")
        assert not risk_engine.is_asset_class_allowed("crypto")


# ── Auditor Tests ────────────────────────────────────────────────────


class TestAuditor:
    @pytest.fixture
    def auditor(self, prefs):
        return Auditor(preferences=prefs)

    def test_good_strategy_passes(self, auditor):
        result = StrategyResult(
            spec_id="test",
            phase="screen",
            passed=True,
            sharpe_ratio=1.5,
            max_drawdown=-0.15,
            total_trades=50,
            profit_factor=1.8,
        )
        report = auditor.audit(result)
        assert report.passed

    def test_low_trades_fails(self, auditor):
        result = StrategyResult(
            spec_id="test",
            phase="screen",
            total_trades=5,
            profit_factor=2.0,
            max_drawdown=-0.10,
        )
        report = auditor.audit(result)
        assert not report.passed
        assert any(c.name == "min_trades" for c in report.failed_checks)

    def test_high_drawdown_fails(self, auditor):
        result = StrategyResult(
            spec_id="test",
            phase="screen",
            total_trades=50,
            profit_factor=2.0,
            max_drawdown=-0.40,  # exceeds 0.25 limit
        )
        report = auditor.audit(result)
        assert not report.passed
        assert any(c.name == "drawdown_limit" for c in report.failed_checks)

    def test_overfitting_detection(self, auditor):
        screen = StrategyResult(
            spec_id="test",
            phase="screen",
            sharpe_ratio=3.0,
            total_trades=50,
            profit_factor=2.0,
            max_drawdown=-0.10,
        )
        validation = StrategyResult(
            spec_id="test",
            phase="validate",
            sharpe_ratio=0.5,  # Gap of 2.5 > threshold of 1.0
            passed=True,
        )
        report = auditor.audit(screen, validation)
        assert not report.passed
        assert any(c.name == "overfitting_detection" for c in report.failed_checks)

    def test_summary_output(self, auditor):
        result = StrategyResult(
            spec_id="test",
            phase="screen",
            total_trades=50,
            profit_factor=2.0,
            max_drawdown=-0.10,
        )
        report = auditor.audit(result)
        summary = report.summary()
        assert "test" in summary
        assert "PASS" in summary or "FAIL" in summary
