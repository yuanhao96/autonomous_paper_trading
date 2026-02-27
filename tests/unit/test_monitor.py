"""Tests for the live monitor module."""

from __future__ import annotations

from datetime import datetime

from src.live.models import Deployment, LiveSnapshot, TradeRecord
from src.live.monitor import Monitor


class TestWinRateRoundTrip:
    """Bug #4: win_rate should use round-trip matching, not t.price > 0."""

    def _make_deployment(self, trades: list[TradeRecord]) -> Deployment:
        dep = Deployment(
            spec_id="test",
            account_id="paper",
            mode="paper",
            symbols=["AAPL"],
            initial_cash=100_000.0,
        )
        dep.trades = trades
        dep.snapshots = [
            LiveSnapshot(
                deployment_id=dep.id,
                timestamp=datetime.utcnow(),
                equity=100_000.0,
                cash=50_000.0,
            ),
        ]
        return dep

    def test_all_losing_trades(self):
        trades = [
            TradeRecord(symbol="AAPL", side="buy", quantity=10, price=50.0,
                        timestamp=datetime.utcnow()),
            TradeRecord(symbol="AAPL", side="sell", quantity=10, price=45.0,
                        timestamp=datetime.utcnow()),
        ]
        dep = self._make_deployment(trades)
        monitor = Monitor()
        result = monitor.compute_live_result(dep, "test")
        assert result.win_rate == 0.0

    def test_all_winning_trades(self):
        trades = [
            TradeRecord(symbol="AAPL", side="buy", quantity=10, price=50.0,
                        timestamp=datetime.utcnow()),
            TradeRecord(symbol="AAPL", side="sell", quantity=10, price=55.0,
                        timestamp=datetime.utcnow()),
        ]
        dep = self._make_deployment(trades)
        monitor = Monitor()
        result = monitor.compute_live_result(dep, "test")
        assert result.win_rate == 1.0

    def test_mixed_trades(self):
        now = datetime.utcnow()
        trades = [
            TradeRecord(symbol="AAPL", side="buy", quantity=10, price=50.0, timestamp=now),
            TradeRecord(symbol="AAPL", side="sell", quantity=10, price=55.0, timestamp=now),
            TradeRecord(symbol="AAPL", side="buy", quantity=10, price=60.0, timestamp=now),
            TradeRecord(symbol="AAPL", side="sell", quantity=10, price=58.0, timestamp=now),
        ]
        dep = self._make_deployment(trades)
        monitor = Monitor()
        result = monitor.compute_live_result(dep, "test")
        assert result.win_rate == 0.5  # 1 win, 1 loss

    def test_no_trades_zero_win_rate(self):
        dep = self._make_deployment([])
        monitor = Monitor()
        result = monitor.compute_live_result(dep, "test")
        assert result.win_rate == 0.0

    def test_sell_without_buy_ignored(self):
        trades = [
            TradeRecord(symbol="AAPL", side="sell", quantity=10, price=55.0,
                        timestamp=datetime.utcnow()),
        ]
        dep = self._make_deployment(trades)
        monitor = Monitor()
        result = monitor.compute_live_result(dep, "test")
        assert result.win_rate == 0.0

    def test_multi_symbol_fifo(self):
        now = datetime.utcnow()
        trades = [
            TradeRecord(symbol="AAPL", side="buy", quantity=10, price=50.0, timestamp=now),
            TradeRecord(symbol="MSFT", side="buy", quantity=10, price=100.0, timestamp=now),
            TradeRecord(symbol="AAPL", side="sell", quantity=10, price=55.0, timestamp=now),
            TradeRecord(symbol="MSFT", side="sell", quantity=10, price=95.0, timestamp=now),
        ]
        dep = self._make_deployment(trades)
        dep.symbols = ["AAPL", "MSFT"]
        monitor = Monitor()
        result = monitor.compute_live_result(dep, "test")
        assert result.win_rate == 0.5  # AAPL win, MSFT loss
