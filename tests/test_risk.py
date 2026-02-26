"""Tests for trading.risk — risk management checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.preferences import Preferences, load_preferences
from trading.risk import OrderRequest, PortfolioState, RiskManager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def prefs(sample_preferences_yaml: Path) -> Preferences:
    return load_preferences(sample_preferences_yaml)


@pytest.fixture
def risk_mgr(prefs: Preferences) -> RiskManager:
    return RiskManager(prefs)


def _portfolio(
    total_equity: float = 100_000.0,
    cash: float = 50_000.0,
    positions: dict | None = None,
    daily_pnl: float = 0.0,
) -> PortfolioState:
    return PortfolioState(
        total_equity=total_equity,
        cash=cash,
        positions=positions or {},
        daily_pnl=daily_pnl,
    )


# ---------------------------------------------------------------------------
# Tests — normal orders pass
# ---------------------------------------------------------------------------


class TestCheckOrderPasses:
    def test_small_buy_passes(self, risk_mgr: RiskManager) -> None:
        order = OrderRequest(
            ticker="AAPL", side="buy", quantity=10,
            order_type="limit", limit_price=150.0,
        )
        portfolio = _portfolio()
        result = risk_mgr.check_order(order, portfolio)
        assert result.approved is True

    def test_sell_always_passes_sanity(self, risk_mgr: RiskManager) -> None:
        """Sell orders only need to pass sanity; other checks are skipped."""
        order = OrderRequest(ticker="AAPL", side="sell", quantity=5, order_type="market")
        portfolio = _portfolio()
        result = risk_mgr.check_order(order, portfolio)
        assert result.approved is True


# ---------------------------------------------------------------------------
# Tests — rejections
# ---------------------------------------------------------------------------


class TestCheckOrderRejections:
    def test_reject_zero_quantity(self, risk_mgr: RiskManager) -> None:
        order = OrderRequest(ticker="AAPL", side="buy", quantity=0, order_type="market")
        portfolio = _portfolio()
        result = risk_mgr.check_order(order, portfolio)
        assert result.approved is False
        assert "quantity" in result.reason.lower()

    def test_reject_max_position_size_exceeded(self, risk_mgr: RiskManager) -> None:
        """max_position_pct is 10 => max $10,000 for $100k portfolio.
        Buying 100 shares at $150 = $15,000 > $10,000.
        """
        order = OrderRequest(
            ticker="AAPL", side="buy", quantity=100,
            order_type="limit", limit_price=150.0,
        )
        portfolio = _portfolio(total_equity=100_000.0)
        result = risk_mgr.check_order(order, portfolio)
        assert result.approved is False
        assert "position size" in result.reason.lower()

    def test_reject_daily_loss_limit(self, risk_mgr: RiskManager) -> None:
        """max_daily_loss_pct is 3 => if daily_pnl <= -3000 on 100k, buys blocked."""
        order = OrderRequest(
            ticker="AAPL", side="buy", quantity=5,
            order_type="limit", limit_price=100.0,
        )
        portfolio = _portfolio(total_equity=100_000.0, daily_pnl=-3500.0)
        result = risk_mgr.check_order(order, portfolio)
        assert result.approved is False
        assert "daily loss" in result.reason.lower()

    def test_reject_sector_concentration(self, risk_mgr: RiskManager) -> None:
        """max_sector_concentration_pct is 30 => max $30,000 for $100k portfolio.
        Existing Tech position worth $28,000 + new buy of $5,000 = $33,000 > $30,000.
        """
        positions = {
            "MSFT": {
                "quantity": 100, "market_value": 28_000.0,
                "avg_cost": 280.0, "sector": "Technology",
            },
            "AAPL": {
                "quantity": 10, "market_value": 1_500.0,
                "avg_cost": 150.0, "sector": "Technology",
            },
        }
        order = OrderRequest(
            ticker="AAPL", side="buy", quantity=30,
            order_type="limit", limit_price=150.0,
        )
        portfolio = _portfolio(total_equity=100_000.0, positions=positions)
        result = risk_mgr.check_order(order, portfolio)
        assert result.approved is False
        assert "sector" in result.reason.lower()

    def test_reject_invalid_side(self, risk_mgr: RiskManager) -> None:
        order = OrderRequest(ticker="AAPL", side="short", quantity=5, order_type="market")
        portfolio = _portfolio()
        result = risk_mgr.check_order(order, portfolio)
        assert result.approved is False
        assert "side" in result.reason.lower()

    def test_reject_limit_order_without_price(self, risk_mgr: RiskManager) -> None:
        order = OrderRequest(
            ticker="AAPL", side="buy", quantity=5,
            order_type="limit", limit_price=None,
        )
        portfolio = _portfolio()
        result = risk_mgr.check_order(order, portfolio)
        assert result.approved is False
        assert "limit_price" in result.reason.lower()


# ---------------------------------------------------------------------------
# Tests — portfolio health warnings
# ---------------------------------------------------------------------------


class TestCheckPortfolioHealth:
    def test_no_warnings_healthy_portfolio(self, risk_mgr: RiskManager) -> None:
        portfolio = _portfolio(
            positions={
                "AAPL": {
                    "quantity": 10, "market_value": 1_500.0,
                    "avg_cost": 150.0, "sector": "Technology",
                },
            },
        )
        warnings = risk_mgr.check_portfolio_health(portfolio)
        assert warnings == []

    def test_position_size_warning(self, risk_mgr: RiskManager) -> None:
        """Position at >=80% of the 10% limit => warning when >= 8% of equity."""
        portfolio = _portfolio(
            total_equity=100_000.0,
            positions={
                "AAPL": {
                    "quantity": 50, "market_value": 8_500.0,
                    "avg_cost": 170.0, "sector": "Technology",
                },
            },
        )
        warnings = risk_mgr.check_portfolio_health(portfolio)
        assert any("AAPL" in w for w in warnings)

    def test_daily_loss_warning(self, risk_mgr: RiskManager) -> None:
        """Daily loss at >=80% of the 3% limit => warning when >= 2.4% of equity."""
        portfolio = _portfolio(total_equity=100_000.0, daily_pnl=-2_500.0)
        warnings = risk_mgr.check_portfolio_health(portfolio)
        assert any("daily loss" in w.lower() for w in warnings)

    def test_zero_equity_warning(self, risk_mgr: RiskManager) -> None:
        portfolio = _portfolio(total_equity=0.0)
        warnings = risk_mgr.check_portfolio_health(portfolio)
        assert any("zero or negative" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# Tests — daily loss gate actually blocks when wired to real daily_pnl
# ---------------------------------------------------------------------------


class TestDailyLossGateIntegration:
    """Verify that real daily_pnl (not hardcoded 0.0) blocks buy orders."""

    def test_loss_below_threshold_allows_buy(self, risk_mgr: RiskManager) -> None:
        """A small daily loss should not block buys."""
        # max_daily_loss_pct=3 on 100k => threshold is -3000.
        portfolio = _portfolio(total_equity=100_000.0, daily_pnl=-1_000.0)
        order = OrderRequest(
            ticker="AAPL", side="buy", quantity=5,
            order_type="limit", limit_price=100.0,
        )
        result = risk_mgr.check_order(order, portfolio)
        assert result.approved is True

    def test_loss_at_exact_threshold_blocks_buy(self, risk_mgr: RiskManager) -> None:
        """Daily loss at exactly the threshold should block buys."""
        portfolio = _portfolio(total_equity=100_000.0, daily_pnl=-3_000.0)
        order = OrderRequest(
            ticker="AAPL", side="buy", quantity=5,
            order_type="limit", limit_price=100.0,
        )
        result = risk_mgr.check_order(order, portfolio)
        assert result.approved is False

    def test_sell_allowed_despite_loss_breach(self, risk_mgr: RiskManager) -> None:
        """Sell orders should still be allowed even if daily loss breached."""
        portfolio = _portfolio(total_equity=100_000.0, daily_pnl=-5_000.0)
        order = OrderRequest(ticker="AAPL", side="sell", quantity=5, order_type="market")
        result = risk_mgr.check_order(order, portfolio)
        assert result.approved is True
