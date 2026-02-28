"""Tests for broker interface — PaperBroker simulation."""

from datetime import datetime

import pytest

from src.live.broker import PaperBroker, is_ibkr_available


class TestPaperBroker:
    def test_connect_disconnect(self):
        broker = PaperBroker()
        assert not broker.is_connected()
        broker.connect()
        assert broker.is_connected()
        broker.disconnect()
        assert not broker.is_connected()

    def test_initial_account_summary(self):
        broker = PaperBroker(initial_cash=100_000)
        broker.connect()
        summary = broker.get_account_summary()
        assert summary["equity"] == 100_000
        assert summary["cash"] == 100_000
        assert summary["gross_position_value"] == 0

    def test_buy_order(self):
        broker = PaperBroker(initial_cash=100_000, commission_rate=0.001)
        broker.connect()
        broker.set_prices({"SPY": 450.0})
        trade = broker.place_order("SPY", "buy", 10)
        assert trade is not None
        assert trade.symbol == "SPY"
        assert trade.side == "buy"
        assert trade.quantity == 10
        assert trade.price == 450.0
        assert trade.commission == 450.0 * 10 * 0.001

        positions = broker.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "SPY"
        assert positions[0].quantity == 10

    def test_sell_order(self):
        broker = PaperBroker(initial_cash=100_000, commission_rate=0.0)
        broker.connect()
        broker.set_prices({"SPY": 450.0})
        broker.place_order("SPY", "buy", 10)
        broker.set_prices({"SPY": 460.0})
        trade = broker.place_order("SPY", "sell", 5)
        assert trade is not None
        assert trade.quantity == 5

        positions = broker.get_positions()
        assert len(positions) == 1
        assert positions[0].quantity == 5

    def test_sell_all_removes_position(self):
        broker = PaperBroker(initial_cash=100_000, commission_rate=0.0)
        broker.connect()
        broker.set_prices({"SPY": 450.0})
        broker.place_order("SPY", "buy", 10)
        broker.place_order("SPY", "sell", 10)
        positions = broker.get_positions()
        assert len(positions) == 0

    def test_insufficient_cash(self):
        broker = PaperBroker(initial_cash=1_000)
        broker.connect()
        broker.set_prices({"SPY": 450.0})
        trade = broker.place_order("SPY", "buy", 100)  # $45,000 > $1,000
        assert trade is None

    def test_insufficient_shares(self):
        broker = PaperBroker(initial_cash=100_000)
        broker.connect()
        broker.set_prices({"SPY": 450.0})
        trade = broker.place_order("SPY", "sell", 10)  # No shares to sell
        assert trade is None

    def test_no_price_available(self):
        broker = PaperBroker()
        broker.connect()
        trade = broker.place_order("UNKNOWN", "buy", 10)
        assert trade is None

    def test_account_after_trades(self):
        broker = PaperBroker(initial_cash=100_000, commission_rate=0.0)
        broker.connect()
        broker.set_prices({"SPY": 100.0})
        broker.place_order("SPY", "buy", 100)  # $10,000

        summary = broker.get_account_summary()
        assert summary["cash"] == 90_000
        assert summary["equity"] == 100_000  # 90k cash + 10k position
        assert summary["gross_position_value"] == 10_000

    def test_recent_trades(self):
        broker = PaperBroker(initial_cash=100_000)
        broker.connect()
        broker.set_prices({"SPY": 450.0})
        broker.place_order("SPY", "buy", 10)
        broker.place_order("SPY", "sell", 5)
        trades = broker.get_recent_trades()
        assert len(trades) == 2
        assert trades[0].side == "buy"
        assert trades[1].side == "sell"

    def test_cancel_all_orders(self):
        broker = PaperBroker()
        broker.connect()
        assert broker.cancel_all_orders() == 0

    def test_add_to_existing_position(self):
        broker = PaperBroker(initial_cash=100_000, commission_rate=0.0)
        broker.connect()
        broker.set_prices({"SPY": 100.0})
        broker.place_order("SPY", "buy", 10)
        broker.set_prices({"SPY": 200.0})
        broker.place_order("SPY", "buy", 10)

        positions = broker.get_positions()
        assert len(positions) == 1
        assert positions[0].quantity == 20
        assert positions[0].avg_cost == 150.0  # (100*10 + 200*10) / 20


    def test_rehydrate_restores_state(self):
        """rehydrate() should restore cash and positions from snapshot."""
        from src.live.models import Position

        broker = PaperBroker(initial_cash=100_000)
        broker.connect()

        positions = [
            Position(symbol="SPY", quantity=50, avg_cost=450.0,
                     market_value=23_000.0, unrealized_pnl=500.0),
            Position(symbol="QQQ", quantity=30, avg_cost=380.0,
                     market_value=11_700.0, unrealized_pnl=300.0),
        ]
        broker.rehydrate(cash=65_000.0, positions=positions)

        assert broker._cash == 65_000.0
        assert len(broker._positions) == 2
        assert broker._positions["SPY"].quantity == 50
        assert broker._positions["QQQ"].avg_cost == 380.0

        summary = broker.get_account_summary()
        assert summary["cash"] == 65_000.0


class TestIBKRAvailability:
    def test_is_ibkr_available(self):
        # Just test it runs without error — result depends on environment
        result = is_ibkr_available()
        assert isinstance(result, bool)
