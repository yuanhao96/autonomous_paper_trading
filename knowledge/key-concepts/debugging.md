# Debugging

## Overview

Covers techniques for debugging algorithmic trading strategies: logging, assertions, common bug categories, backtesting artifacts, and systematic debugging methodology. Trading bugs can be subtle and expensive — systematic debugging is essential.

## Logging

The most fundamental debugging tool. Log key decision points, not every data event.

### What to Log

```python
def on_data(self, data):
    price = data["SPY"].close
    signal = self.compute_signal(price)

    # Log signals and trades, not every price tick
    if signal != self.previous_signal:
        self.log(f"Signal change: {self.previous_signal} → {signal} "
                 f"at price {price:.2f}")

    if self.should_trade(signal):
        self.log(f"ORDER: {'BUY' if signal > 0 else 'SELL'} SPY "
                 f"at {price:.2f}, portfolio value: {self.portfolio.total_value:.2f}")
```

### Log Levels

| Level | Use For |
|-------|---------|
| **DEBUG** | Detailed diagnostic info (indicator values, intermediate calculations) |
| **INFO** | Key events (trades, rebalances, signal changes) |
| **WARNING** | Unexpected but non-fatal conditions (missing data, stale prices) |
| **ERROR** | Failures that affect strategy behavior |

### Structured Logging

For post-hoc analysis, log structured data:

```python
import json

trade_log = {
    "timestamp": str(self.time),
    "symbol": "SPY",
    "action": "BUY",
    "price": 450.25,
    "quantity": 100,
    "signal_value": 0.85,
    "portfolio_value": 100250.00
}
self.log(json.dumps(trade_log))
```

## Assertions

Catch impossible states early:

```python
def set_position(self, symbol, weight):
    assert -1.0 <= weight <= 1.0, f"Invalid weight: {weight}"
    assert symbol in self.universe, f"Unknown symbol: {symbol}"

def compute_returns(self, prices):
    returns = prices.pct_change().dropna()
    assert not returns.isnull().any(), "NaN in returns"
    assert len(returns) > 0, "Empty returns series"
    return returns
```

Assertions are development-time checks. In production, replace with proper error handling.

## Common Bug Categories

### Data Bugs

| Bug | Symptom | Fix |
|-----|---------|-----|
| **Look-ahead bias** | Backtest Sharpe too good to be true | Verify data delivery timing |
| **Survivorship bias** | Strategy works on historical data, fails live | Use point-in-time universe |
| **Missing data** | NaN in calculations, wrong signals | Check fillna/dropna logic |
| **Wrong resolution** | Signals fire at wrong times | Verify data subscription resolution |
| **Timezone errors** | Trades at wrong times | Explicit timezone in all comparisons |

### Logic Bugs

| Bug | Symptom | Fix |
|-----|---------|-----|
| **Off-by-one** | Indicator uses wrong bar | Check indexing (0-based vs 1-based) |
| **Sign error** | Long when should be short | Trace signal calculation step by step |
| **Stale state** | Old signal persists | Reset state on rebalance/exit |
| **Warmup issues** | Trades before indicators ready | Check warmup period sufficient |
| **Division by zero** | Crash on low-volume days | Guard against zero denominators |

### Execution Bugs

| Bug | Symptom | Fix |
|-----|---------|-----|
| **Double orders** | Position too large | Track order state; check before ordering |
| **Unfilled orders** | Position never established | Check order type and limit prices |
| **Wrong quantity** | Over/under exposed | Verify position sizing calculation |
| **Margin violation** | Orders rejected | Check buying power before ordering |

## Debugging Methodology

### Step 1: Reproduce

Find the smallest reproducible case:
- Narrow the date range to when the bug occurs
- Reduce to a single instrument if possible
- Disable other strategy components

### Step 2: Isolate

Determine which component is wrong:
- Is the data correct? Log raw data values
- Is the signal correct? Log intermediate calculations
- Is the order correct? Log order parameters
- Is the fill correct? Log fill prices and quantities

### Step 3: Trace

Follow the data flow through the bug:

```python
def on_data(self, data):
    # Trace every step
    price = data["SPY"].close
    self.debug(f"Step 1 - Price: {price}")

    sma = self.sma.current.value
    self.debug(f"Step 2 - SMA: {sma}")

    signal = 1 if price > sma else -1
    self.debug(f"Step 3 - Signal: {signal}")

    current_holding = self.portfolio["SPY"].quantity
    self.debug(f"Step 4 - Current position: {current_holding}")
```

### Step 4: Fix and Verify

- Fix the bug
- Add a test case that catches this specific bug
- Run the full backtest to check for regressions

## Backtesting Artifacts

Be aware of results that look good but aren't real:

- **Unrealistic fills**: Backtester fills at close price, but live orders get worse fills
- **Zero slippage**: Backtester ignores market impact
- **Lookahead in sorting**: Cross-sectional strategy uses end-of-day data that wasn't available intraday
- **Calendar effects**: Backtest doesn't account for holidays when market was closed

## Financial Application Notes

- Log trades and signals, not raw prices — the log volume will be manageable
- Structured JSON logs enable automated analysis of strategy behavior
- The most dangerous bugs are silent (wrong signal, no error) — use assertions liberally
- Always verify backtest results against a simple benchmark before trusting
- When a backtest looks "too good," assume there's a bug until proven otherwise

## Summary

Debugging trading algorithms requires systematic logging (structured, at appropriate levels), assertions for impossible states, awareness of common bug categories (data, logic, execution), and a disciplined methodology (reproduce, isolate, trace, fix). Backtesting artifacts can make buggy strategies appear profitable. When in doubt, log more and trust less.

## Source

- Based on [QuantConnect: Key Concepts — Debugging Tools](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/debugging-tools)
