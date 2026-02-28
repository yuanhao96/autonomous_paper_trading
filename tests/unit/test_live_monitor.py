"""Tests for the live trading monitor."""

from datetime import datetime, timedelta

import pytest

from src.live.models import Deployment, LiveSnapshot, Position
from src.live.monitor import Monitor
from src.strategies.spec import StrategyResult


def _make_deployment(
    snapshots: list[LiveSnapshot] | None = None,
    initial_cash: float = 100_000,
    days_ago: int = 30,
) -> Deployment:
    d = Deployment(
        spec_id="test_spec",
        account_id="paper",
        mode="paper",
        symbols=["SPY"],
        initial_cash=initial_cash,
    )
    d.status = "active"
    d.started_at = datetime.utcnow() - timedelta(days=days_ago)
    if snapshots:
        d.snapshots = snapshots
    return d


def _make_snapshot(
    deployment_id: str = "d1",
    equity: float = 100_000,
    cash: float = 50_000,
    positions: list[Position] | None = None,
    hours_offset: int = 0,
) -> LiveSnapshot:
    return LiveSnapshot(
        deployment_id=deployment_id,
        timestamp=datetime.utcnow() - timedelta(hours=hours_offset),
        equity=equity,
        cash=cash,
        positions=positions or [],
    )


def _make_validation_result(**kwargs) -> StrategyResult:
    defaults = {
        "spec_id": "test_spec",
        "phase": "validate",
        "passed": True,
        "annual_return": 0.15,
        "sharpe_ratio": 1.2,
        "max_drawdown": -0.12,
    }
    defaults.update(kwargs)
    return StrategyResult(**defaults)


class TestMonitorCompare:
    def test_compare_within_tolerance(self):
        """Good live performance → within tolerance."""
        monitor = Monitor()
        snapshots = [
            _make_snapshot(equity=100_000, hours_offset=48),
            _make_snapshot(equity=101_000, hours_offset=24),
            _make_snapshot(equity=102_000, hours_offset=0),
        ]
        deployment = _make_deployment(snapshots=snapshots, days_ago=30)
        validation = _make_validation_result()
        report = monitor.compare(deployment, validation)
        assert report.live_return == pytest.approx(0.02, abs=0.001)
        assert report.days_elapsed >= 29

    def test_compare_no_snapshots(self):
        """No snapshots → alerts and not within tolerance."""
        monitor = Monitor()
        deployment = _make_deployment(snapshots=[], days_ago=10)
        validation = _make_validation_result()
        report = monitor.compare(deployment, validation)
        assert not report.within_tolerance
        assert "No snapshots" in report.alerts[0]

    def test_compare_sharpe_drift(self):
        """Large Sharpe drift triggers alert."""
        monitor = Monitor()
        # Create snapshots with volatile returns
        snapshots = [
            _make_snapshot(equity=100_000, hours_offset=96),
            _make_snapshot(equity=90_000, hours_offset=72),
            _make_snapshot(equity=110_000, hours_offset=48),
            _make_snapshot(equity=85_000, hours_offset=24),
            _make_snapshot(equity=95_000, hours_offset=0),
        ]
        deployment = _make_deployment(snapshots=snapshots, days_ago=30)
        validation = _make_validation_result(sharpe_ratio=3.0)  # Very high expected Sharpe
        report = monitor.compare(deployment, validation)
        # Live Sharpe with volatile returns should be far from 3.0
        sharpe_alerts = [a for a in report.alerts if "Sharpe" in a]
        assert len(sharpe_alerts) > 0

    def test_compare_drawdown_alert(self):
        """Large drawdown triggers alert."""
        monitor = Monitor()
        snapshots = [
            _make_snapshot(equity=100_000, hours_offset=48),
            _make_snapshot(equity=80_000, hours_offset=24),  # 20% drawdown
            _make_snapshot(equity=82_000, hours_offset=0),
        ]
        deployment = _make_deployment(snapshots=snapshots, days_ago=10)
        validation = _make_validation_result(max_drawdown=-0.10)
        report = monitor.compare(deployment, validation)
        dd_alerts = [a for a in report.alerts if "drawdown" in a.lower()]
        assert len(dd_alerts) > 0


class TestMonitorRisk:
    def test_no_violations_healthy(self):
        """Healthy deployment has no risk violations."""
        monitor = Monitor()
        snapshots = [
            _make_snapshot(
                equity=100_000, cash=50_000,
                positions=[Position("SPY", 100, 450, 9000, 500)],
            ),
        ]
        deployment = _make_deployment(snapshots=snapshots)
        violations = monitor.check_risk(deployment)
        assert len(violations) == 0

    def test_position_concentration_violation(self):
        """Single position > max_position_pct triggers violation."""
        monitor = Monitor()
        snapshots = [
            _make_snapshot(
                equity=100_000, cash=10_000,
                positions=[Position("SPY", 1000, 90, 90_000, 0)],  # 90% of equity
            ),
        ]
        deployment = _make_deployment(snapshots=snapshots)
        violations = monitor.check_risk(deployment)
        rules = [v.rule for v in violations]
        assert "max_position_pct" in rules

    def test_daily_loss_violation(self):
        """Large daily loss triggers violation."""
        monitor = Monitor()
        snapshots = [
            _make_snapshot(equity=100_000, hours_offset=24),
            _make_snapshot(equity=90_000, hours_offset=0),  # 10% daily loss
        ]
        deployment = _make_deployment(snapshots=snapshots)
        violations = monitor.check_risk(deployment)
        rules = [v.rule for v in violations]
        assert "max_daily_loss" in rules

    def test_no_snapshots_no_violations(self):
        monitor = Monitor()
        deployment = _make_deployment(snapshots=[])
        violations = monitor.check_risk(deployment)
        assert len(violations) == 0

    def test_leverage_violation(self):
        """Positions exceeding max leverage trigger violation."""
        monitor = Monitor()
        # equity=100k, positions worth 150k total → 1.5x leverage
        snapshots = [
            _make_snapshot(
                equity=100_000, cash=-50_000,
                positions=[
                    Position("SPY", 200, 375, 75_000, 0),
                    Position("QQQ", 200, 375, 75_000, 0),
                ],
            ),
        ]
        deployment = _make_deployment(snapshots=snapshots)
        violations = monitor.check_risk(deployment)
        rules = [v.rule for v in violations]
        assert "max_leverage" in rules

    def test_cash_reserve_violation(self):
        """Cash below min_cash_reserve_pct triggers violation."""
        monitor = Monitor()
        # equity=100k, cash=1k → 1% cash (below 5% min)
        snapshots = [
            _make_snapshot(
                equity=100_000, cash=1_000,
                positions=[Position("SPY", 200, 495, 99_000, 0)],
            ),
        ]
        deployment = _make_deployment(snapshots=snapshots)
        violations = monitor.check_risk(deployment)
        rules = [v.rule for v in violations]
        assert "min_cash_reserve_pct" in rules


class TestComputeLiveResult:
    def test_compile_result(self):
        """Compile snapshots into a StrategyResult."""
        monitor = Monitor()
        snapshots = [
            _make_snapshot(equity=100_000, hours_offset=48),
            _make_snapshot(equity=105_000, hours_offset=24),
            _make_snapshot(equity=110_000, hours_offset=0),
        ]
        deployment = _make_deployment(snapshots=snapshots, days_ago=30)
        result = monitor.compute_live_result(deployment, "test_spec")
        assert result.phase == "live"
        assert result.total_return == pytest.approx(0.10, abs=0.01)
        assert len(result.equity_curve) == 3
        assert result.passed is True

    def test_compile_result_no_snapshots(self):
        monitor = Monitor()
        deployment = _make_deployment(snapshots=[], days_ago=5)
        result = monitor.compute_live_result(deployment, "test_spec")
        assert result.failure_reason == "No snapshots"
