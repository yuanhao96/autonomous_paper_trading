"""Tests for live trading data models."""

from datetime import datetime, timedelta

from src.live.models import (
    ComparisonReport,
    Deployment,
    LiveSnapshot,
    Position,
    PromotionReport,
    TradeRecord,
)


class TestPosition:
    def test_current_price(self):
        p = Position(symbol="AAPL", quantity=10, avg_cost=150.0, market_value=1600.0, unrealized_pnl=100.0)
        assert p.current_price == 160.0

    def test_current_price_zero_quantity(self):
        p = Position(symbol="AAPL", quantity=0, avg_cost=150.0, market_value=0.0, unrealized_pnl=0.0)
        assert p.current_price == 0.0


class TestTradeRecord:
    def test_notional(self):
        t = TradeRecord(symbol="SPY", side="buy", quantity=100, price=450.0, timestamp=datetime.utcnow())
        assert t.notional == 45000.0


class TestLiveSnapshot:
    def test_position_count(self):
        s = LiveSnapshot(
            deployment_id="d1", timestamp=datetime.utcnow(), equity=100000, cash=50000,
            positions=[
                Position("AAPL", 10, 150, 1500, 0),
                Position("MSFT", 20, 300, 6000, 0),
            ],
        )
        assert s.position_count == 2

    def test_invested_pct(self):
        s = LiveSnapshot(
            deployment_id="d1", timestamp=datetime.utcnow(), equity=100000, cash=50000,
            positions=[
                Position("AAPL", 10, 150, 25000, 0),
                Position("MSFT", 20, 300, 25000, 0),
            ],
        )
        assert s.invested_pct == 0.5

    def test_invested_pct_zero_equity(self):
        s = LiveSnapshot(deployment_id="d1", timestamp=datetime.utcnow(), equity=0, cash=0)
        assert s.invested_pct == 0.0


class TestDeployment:
    def test_defaults(self):
        d = Deployment(spec_id="s1", account_id="paper", mode="paper", symbols=["SPY"])
        assert d.status == "pending"
        assert d.is_active is False
        assert len(d.id) == 12

    def test_is_active(self):
        d = Deployment(spec_id="s1", account_id="paper", mode="paper", symbols=["SPY"])
        d.status = "active"
        assert d.is_active is True

    def test_days_elapsed(self):
        d = Deployment(spec_id="s1", account_id="paper", mode="paper", symbols=["SPY"])
        d.started_at = datetime.utcnow() - timedelta(days=10)
        assert d.days_elapsed >= 9  # Allow for timing


class TestComparisonReport:
    def test_summary_ok(self):
        r = ComparisonReport(
            deployment_id="d1", days_elapsed=20,
            live_return=0.05, expected_annual_return=0.10,
            live_sharpe=1.2, expected_sharpe=1.5,
            live_max_drawdown=0.08, expected_max_drawdown=0.15,
            within_tolerance=True,
        )
        summary = r.summary()
        assert "OK" in summary
        assert "20 days" in summary

    def test_summary_drift(self):
        r = ComparisonReport(
            deployment_id="d1", days_elapsed=20,
            within_tolerance=False,
            alerts=["Return drift exceeded"],
        )
        summary = r.summary()
        assert "DRIFT DETECTED" in summary


class TestPromotionReport:
    def test_summary(self):
        r = PromotionReport(
            deployment_id="d1", spec_id="s1",
            days_elapsed=25, min_days_required=20,
            meets_time_requirement=True,
            decision="approved", reasoning="All checks passed",
        )
        summary = r.summary()
        assert "APPROVED" in summary
        assert "25/20" in summary
