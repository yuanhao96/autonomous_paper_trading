"""Tests for trading.paper_broker — mock paper trading broker."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from trading.paper_broker import Order, PaperBroker, Portfolio, Position

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def broker(tmp_path: Path) -> PaperBroker:
    """Create a PaperBroker in mock mode with a temporary SQLite DB."""
    db_path = tmp_path / "test_paper_trades.db"
    return PaperBroker(mock=True, db_path=db_path)


def _mock_current_price(price: float = 150.0):
    """Return a patcher that makes _current_price return a fixed value."""
    return patch(
        "trading.paper_broker._current_price",
        return_value=price,
    )


# ---------------------------------------------------------------------------
# Tests — initialisation
# ---------------------------------------------------------------------------


class TestInitialisation:
    def test_mock_mode_initial_cash(self, broker: PaperBroker) -> None:
        assert broker.mock is True
        cash = broker._get_cash()
        assert cash == pytest.approx(100_000.0)

    def test_portfolio_starts_at_100k(self, broker: PaperBroker) -> None:
        with _mock_current_price():
            portfolio = broker.get_portfolio()
        assert isinstance(portfolio, Portfolio)
        assert portfolio.cash == pytest.approx(100_000.0)
        assert portfolio.positions == []
        assert portfolio.total_equity == pytest.approx(100_000.0)


# ---------------------------------------------------------------------------
# Tests — submit_order (buy)
# ---------------------------------------------------------------------------


class TestSubmitOrderBuy:
    def test_buy_market_order(self, broker: PaperBroker) -> None:
        with _mock_current_price(150.0):
            order = broker.submit_order("AAPL", "buy", 10)

        assert isinstance(order, Order)
        assert order.status == "filled"
        assert order.ticker == "AAPL"
        assert order.side == "buy"
        assert order.quantity == 10
        assert order.filled_price == pytest.approx(150.0)

        # Cash should decrease by 10 * 150 = 1500.
        cash = broker._get_cash()
        assert cash == pytest.approx(100_000.0 - 1_500.0)

    def test_buy_insufficient_cash(self, broker: PaperBroker) -> None:
        with _mock_current_price(200.0):
            with pytest.raises(ValueError, match="Insufficient cash"):
                broker.submit_order("AAPL", "buy", 1000)

    def test_buy_invalid_side(self, broker: PaperBroker) -> None:
        with pytest.raises(ValueError, match="side"):
            broker.submit_order("AAPL", "short", 10)

    def test_buy_zero_quantity(self, broker: PaperBroker) -> None:
        with pytest.raises(ValueError, match="quantity"):
            broker.submit_order("AAPL", "buy", 0)


# ---------------------------------------------------------------------------
# Tests — positions after buying
# ---------------------------------------------------------------------------


class TestGetPositions:
    def test_positions_after_buy(self, broker: PaperBroker) -> None:
        with _mock_current_price(150.0):
            broker.submit_order("AAPL", "buy", 10)

        with _mock_current_price(155.0):
            positions = broker.get_positions()

        assert len(positions) == 1
        pos = positions[0]
        assert isinstance(pos, Position)
        assert pos.ticker == "AAPL"
        assert pos.quantity == 10
        assert pos.avg_cost == pytest.approx(150.0)
        # Market value at $155.
        assert pos.market_value == pytest.approx(1_550.0)
        assert pos.unrealized_pnl == pytest.approx(50.0)

    def test_no_positions_initially(self, broker: PaperBroker) -> None:
        with _mock_current_price():
            positions = broker.get_positions()
        assert positions == []


# ---------------------------------------------------------------------------
# Tests — portfolio snapshot
# ---------------------------------------------------------------------------


class TestGetPortfolio:
    def test_portfolio_after_buy(self, broker: PaperBroker) -> None:
        with _mock_current_price(100.0):
            broker.submit_order("AAPL", "buy", 50)

        with _mock_current_price(110.0):
            portfolio = broker.get_portfolio()

        assert isinstance(portfolio, Portfolio)
        # Cash = 100k - 5000 = 95000.
        assert portfolio.cash == pytest.approx(95_000.0)
        # Equity = cash + 50 * 110 = 95000 + 5500 = 100500.
        assert portfolio.total_equity == pytest.approx(100_500.0)
        assert len(portfolio.positions) == 1


# ---------------------------------------------------------------------------
# Tests — order history
# ---------------------------------------------------------------------------


class TestGetOrderHistory:
    def test_order_history(self, broker: PaperBroker) -> None:
        with _mock_current_price(100.0):
            broker.submit_order("AAPL", "buy", 10)
            broker.submit_order("GOOG", "buy", 5)

        history = broker.get_order_history()
        assert len(history) == 2
        # Newest first.
        assert all(isinstance(o, Order) for o in history)
        assert history[0].ticker == "GOOG"
        assert history[1].ticker == "AAPL"

    def test_empty_history(self, broker: PaperBroker) -> None:
        history = broker.get_order_history()
        assert history == []


# ---------------------------------------------------------------------------
# Tests — sell orders
# ---------------------------------------------------------------------------


class TestSubmitOrderSell:
    def test_sell_existing_position(self, broker: PaperBroker) -> None:
        with _mock_current_price(100.0):
            broker.submit_order("AAPL", "buy", 20)

        with _mock_current_price(110.0):
            order = broker.submit_order("AAPL", "sell", 10)

        assert order.status == "filled"
        assert order.filled_price == pytest.approx(110.0)

        # Check remaining position.
        with _mock_current_price(110.0):
            positions = broker.get_positions()
        assert len(positions) == 1
        assert positions[0].quantity == 10

    def test_sell_more_than_held_raises(self, broker: PaperBroker) -> None:
        with _mock_current_price(100.0):
            broker.submit_order("AAPL", "buy", 5)
            with pytest.raises(ValueError, match="Cannot sell"):
                broker.submit_order("AAPL", "sell", 10)


# ---------------------------------------------------------------------------
# Tests — daily P&L tracking
# ---------------------------------------------------------------------------


class TestDailyPnL:
    def test_initial_daily_pnl_is_zero(self, broker: PaperBroker) -> None:
        """First portfolio call of the day should set baseline and return 0."""
        with _mock_current_price(100.0):
            portfolio = broker.get_portfolio()
        assert portfolio.daily_pnl == pytest.approx(0.0)

    def test_daily_pnl_reflects_gains(self, broker: PaperBroker) -> None:
        """After buying and price increasing, daily P&L should be positive."""
        # Establish baseline at $100k.
        with _mock_current_price(100.0):
            broker.get_portfolio()  # Sets opening equity = 100k.

        # Buy 100 shares at $100.
        with _mock_current_price(100.0):
            broker.submit_order("AAPL", "buy", 100)

        # Price goes up to $110 → equity = 90k cash + 100*110 = 101k.
        with _mock_current_price(110.0):
            portfolio = broker.get_portfolio()
        assert portfolio.daily_pnl == pytest.approx(1_000.0)

    def test_daily_pnl_reflects_losses(self, broker: PaperBroker) -> None:
        """After buying and price dropping, daily P&L should be negative."""
        with _mock_current_price(100.0):
            broker.get_portfolio()  # Baseline = 100k.
            broker.submit_order("AAPL", "buy", 100)

        # Price drops to $90 → equity = 90k + 100*90 = 99k.
        with _mock_current_price(90.0):
            portfolio = broker.get_portfolio()
        assert portfolio.daily_pnl == pytest.approx(-1_000.0)

    def test_reset_daily_pnl(self, broker: PaperBroker) -> None:
        """reset_daily_pnl() should zero out the daily P&L."""
        with _mock_current_price(100.0):
            broker.get_portfolio()
            broker.submit_order("AAPL", "buy", 100)

        with _mock_current_price(110.0):
            portfolio = broker.get_portfolio()
            assert portfolio.daily_pnl == pytest.approx(1_000.0)

            # Reset baseline to current equity.
            broker.reset_daily_pnl()
            portfolio = broker.get_portfolio()
            assert portfolio.daily_pnl == pytest.approx(0.0)

    def test_day_boundary_resets_baseline(self, broker: PaperBroker) -> None:
        """When day_date changes, the baseline should auto-reset."""
        with _mock_current_price(100.0):
            broker.get_portfolio()  # Baseline for today.
            broker.submit_order("AAPL", "buy", 100)

        # Simulate next day by changing the stored day_date.
        broker._set_opening_equity(100_000.0, "2020-01-01")

        # Now equity is still 100k but baseline is from "yesterday".
        # _ensure_day_baseline will see different day and reset.
        with _mock_current_price(110.0):
            portfolio = broker.get_portfolio()
        # New day → baseline reset to current equity → daily_pnl = 0.
        assert portfolio.daily_pnl == pytest.approx(0.0)

    def test_portfolio_dataclass_has_daily_pnl(self, broker: PaperBroker) -> None:
        """Portfolio dataclass should expose daily_pnl field."""
        with _mock_current_price(100.0):
            portfolio = broker.get_portfolio()
        assert hasattr(portfolio, "daily_pnl")
        assert isinstance(portfolio.daily_pnl, float)
