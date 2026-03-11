# Current Context

## Active Milestone

**Name**: Paper Trading Execution via Alpaca
**Goal**: Extend trade.py to submit orders to Alpaca paper trading based on allocation weights.

## Current Phase

**Phase**: review
**Started**: 2026-03-11

## Key Decisions

- [AUTO] Implement order submission as `stratgen trade` command (rebalance to target weights)
- [AUTO] Use market orders for simplicity — limit orders add complexity without clear benefit for paper trading
- [AUTO] Compute target shares from allocation weights * account equity / current price
- [AUTO] No Alpaca credentials available — implement and test with mocks, flag for user to add credentials

## Blockers

- [ ] ALPACA_API_KEY and ALPACA_SECRET_KEY not set in .env — needed for live testing

## Plan Reference

### Steps

1. [x] Add `compute_rebalance_orders()` and `execute_orders()` to trade.py
2. [x] Add `cmd_trade()` to trade.py — load allocation, call rebalance
3. [x] Add `trade` subcommand to cli.py (parser + dispatch)
4. [x] Create tests/test_trade.py with 9 tests for rebalance logic
5. [x] All 48 tests pass, lint clean

## Notes

- Existing: get_alpaca_client(), show_status(), cmd_status()
- alpaca-py SDK: TradingClient, MarketOrderRequest, OrderSide, TimeInForce
- Live testing blocked on Alpaca credentials — all pure logic fully tested
