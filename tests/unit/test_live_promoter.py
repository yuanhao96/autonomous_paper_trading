"""Tests for the promoter module."""

from datetime import datetime, timedelta

import pytest

from src.live.models import Deployment, LiveSnapshot, Position
from src.live.promoter import Promoter
from src.strategies.spec import StrategyResult


def _make_deployment(
    snapshots: list[LiveSnapshot] | None = None,
    days_ago: int = 25,
) -> Deployment:
    d = Deployment(
        spec_id="test_spec",
        account_id="paper",
        mode="paper",
        symbols=["SPY"],
        initial_cash=100_000,
    )
    d.status = "active"
    d.started_at = datetime.utcnow() - timedelta(days=days_ago)
    if snapshots:
        d.snapshots = snapshots
    return d


def _make_snapshot(equity: float, hours_offset: int = 0, with_positions: bool = True) -> LiveSnapshot:
    if with_positions:
        # Keep position weight within 10% limit
        pos_value = equity * 0.08
        positions = [Position("SPY", 10, pos_value / 10, pos_value, 0)]
    else:
        positions = []
    return LiveSnapshot(
        deployment_id="d1",
        timestamp=datetime.utcnow() - timedelta(hours=hours_offset),
        equity=equity,
        cash=equity - sum(p.market_value for p in positions),
        positions=positions,
    )


def _make_validation(**kwargs) -> StrategyResult:
    defaults = {
        "spec_id": "test_spec",
        "phase": "validate",
        "passed": True,
        "annual_return": 0.12,
        "sharpe_ratio": 1.0,
        "max_drawdown": -0.15,
    }
    defaults.update(kwargs)
    return StrategyResult(**defaults)


class TestPromoter:
    def test_approved_after_min_days(self):
        """Strategy meeting all criteria → approved."""
        promoter = Promoter()
        # 26 snapshots with steady, low-volatility gains
        import random
        random.seed(42)
        equity = 100_000.0
        snapshots = []
        for i in range(25):
            snapshots.append(_make_snapshot(equity, hours_offset=(25 - i) * 24))
            daily_ret = 0.0005 + random.gauss(0, 0.005)
            equity *= (1 + daily_ret)
        snapshots.append(_make_snapshot(equity, hours_offset=0))

        deployment = _make_deployment(snapshots=snapshots, days_ago=25)

        # Set validation expectations close to what the live data produces
        # so drift stays within tolerance
        from src.live.monitor import Monitor
        monitor = Monitor()
        live_return = monitor._compute_return(deployment)
        live_sharpe = monitor._compute_sharpe(deployment)
        validation = _make_validation(
            annual_return=live_return * (252.0 / 25),  # Match annualized live return
            sharpe_ratio=live_sharpe,  # Match live Sharpe
        )

        report = promoter.evaluate(deployment, validation)
        assert report.meets_time_requirement is True
        assert report.decision == "approved"

    def test_rejected_insufficient_days(self):
        """Not enough paper trading days → needs_review or rejected."""
        promoter = Promoter()
        snapshots = [
            _make_snapshot(100_000, hours_offset=24),
            _make_snapshot(101_000, hours_offset=0),
        ]
        deployment = _make_deployment(snapshots=snapshots, days_ago=5)
        validation = _make_validation()
        report = promoter.evaluate(deployment, validation)
        assert report.meets_time_requirement is False
        assert report.decision in ("needs_review", "rejected")

    def test_rejected_with_risk_violations(self):
        """Risk violations → rejected."""
        promoter = Promoter()
        # Create snapshots with a big drawdown (40% drop → exceeds 25% portfolio limit)
        snapshots = [
            _make_snapshot(100_000, hours_offset=48),
            _make_snapshot(60_000, hours_offset=24),  # 40% daily drop triggers max_daily_loss
            _make_snapshot(65_000, hours_offset=0),
        ]
        deployment = _make_deployment(snapshots=snapshots, days_ago=25)
        validation = _make_validation()
        report = promoter.evaluate(deployment, validation)
        assert report.decision == "rejected"
        assert len(report.risk_violations) > 0

    def test_no_snapshots_needs_review(self):
        """No performance data → needs_review."""
        promoter = Promoter()
        deployment = _make_deployment(snapshots=[], days_ago=25)
        validation = _make_validation()
        report = promoter.evaluate(deployment, validation)
        assert report.decision in ("needs_review", "rejected")

    def test_promotion_summary_string(self):
        """get_promotion_summary returns formatted string."""
        promoter = Promoter()
        snapshots = [
            _make_snapshot(100_000, hours_offset=48),
            _make_snapshot(101_000, hours_offset=0),
        ]
        deployment = _make_deployment(snapshots=snapshots, days_ago=25)
        validation = _make_validation()
        summary = promoter.get_promotion_summary(deployment, validation)
        assert "PROMOTION EVALUATION" in summary
        assert "test_spec" in summary

    def test_report_summary(self):
        """PromotionReport.summary() works."""
        promoter = Promoter()
        snapshots = [
            _make_snapshot(100_000, hours_offset=24),
            _make_snapshot(101_000, hours_offset=0),
        ]
        deployment = _make_deployment(snapshots=snapshots, days_ago=25)
        validation = _make_validation()
        report = promoter.evaluate(deployment, validation)
        summary = report.summary()
        assert "Promotion Report" in summary
        assert "test_spec" in summary
