"""Unit tests for stratgen.trade module (rebalance logic, no Alpaca needed)."""

from stratgen.trade import compute_rebalance_orders


class TestComputeRebalanceOrders:
    def test_basic_buy(self):
        orders = compute_rebalance_orders(
            target_weights={"AAPL": 0.5},
            equity=10_000,
            current_positions={},
            prices={"AAPL": 100.0},
        )
        assert len(orders) == 1
        assert orders[0]["ticker"] == "AAPL"
        assert orders[0]["side"] == "buy"
        assert orders[0]["qty"] == 50  # 0.5 * 10000 / 100

    def test_basic_sell(self):
        orders = compute_rebalance_orders(
            target_weights={},
            equity=10_000,
            current_positions={"AAPL": 50},
            prices={"AAPL": 100.0},
        )
        assert len(orders) == 1
        assert orders[0]["ticker"] == "AAPL"
        assert orders[0]["side"] == "sell"
        assert orders[0]["qty"] == 50

    def test_rebalance_partial(self):
        orders = compute_rebalance_orders(
            target_weights={"AAPL": 0.5},
            equity=10_000,
            current_positions={"AAPL": 30},
            prices={"AAPL": 100.0},
        )
        assert len(orders) == 1
        assert orders[0]["side"] == "buy"
        assert orders[0]["qty"] == 20  # need 50, have 30

    def test_no_orders_when_balanced(self):
        orders = compute_rebalance_orders(
            target_weights={"AAPL": 0.5},
            equity=10_000,
            current_positions={"AAPL": 50},
            prices={"AAPL": 100.0},
        )
        assert len(orders) == 0

    def test_min_trade_value_filter(self):
        orders = compute_rebalance_orders(
            target_weights={"AAPL": 0.501},
            equity=10_000,
            current_positions={"AAPL": 50},
            prices={"AAPL": 100.0},
            min_trade_value=200.0,
        )
        # delta = floor(5010/100) - 50 = 50 - 50 = 0, no order
        assert len(orders) == 0

    def test_multiple_tickers(self):
        orders = compute_rebalance_orders(
            target_weights={"AAPL": 0.3, "GOOG": 0.3},
            equity=10_000,
            current_positions={"MSFT": 10},
            prices={"AAPL": 150.0, "GOOG": 100.0, "MSFT": 200.0},
        )
        tickers = {o["ticker"] for o in orders}
        assert "AAPL" in tickers  # buy
        assert "GOOG" in tickers  # buy
        assert "MSFT" in tickers  # sell

        for o in orders:
            if o["ticker"] == "MSFT":
                assert o["side"] == "sell"
            else:
                assert o["side"] == "buy"

    def test_missing_price_skipped(self):
        orders = compute_rebalance_orders(
            target_weights={"AAPL": 0.5, "GOOG": 0.5},
            equity=10_000,
            current_positions={},
            prices={"AAPL": 100.0},  # no GOOG price
        )
        assert len(orders) == 1
        assert orders[0]["ticker"] == "AAPL"

    def test_zero_price_skipped(self):
        orders = compute_rebalance_orders(
            target_weights={"AAPL": 0.5},
            equity=10_000,
            current_positions={},
            prices={"AAPL": 0.0},
        )
        assert len(orders) == 0

    def test_floor_rounding(self):
        orders = compute_rebalance_orders(
            target_weights={"AAPL": 0.5},
            equity=10_000,
            current_positions={},
            prices={"AAPL": 333.0},
        )
        # target_value = 5000, target_qty = floor(5000/333) = 15
        assert orders[0]["qty"] == 15
