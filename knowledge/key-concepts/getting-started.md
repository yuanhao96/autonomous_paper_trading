# Getting Started with Algorithmic Trading

## Overview

Introduces the fundamental structure and lifecycle of a trading algorithm. Covers the core components every algorithm needs: initialization, data handling, event processing, and portfolio management.

## Algorithm Structure

Every trading algorithm follows a common pattern with these core components:

### Initialization

The initialization phase runs once when the algorithm starts. It configures:

- **Data subscriptions**: Which instruments to trade (equities, forex, crypto, etc.)
- **Time period**: Backtest start/end dates, or live trading mode
- **Starting capital**: Initial cash allocation
- **Resolution**: Data granularity (tick, second, minute, hourly, daily)
- **Brokerage settings**: Fee models, slippage assumptions, margin requirements
- **Parameters**: Strategy-specific configuration (lookback periods, thresholds, etc.)

```python
def initialize(self):
    self.set_start_date(2020, 1, 1)
    self.set_end_date(2023, 12, 31)
    self.set_cash(100000)
    self.add_equity("SPY", Resolution.Daily)
    self.add_forex("EURUSD", Resolution.Hour)
```

### Data Event Handler

The primary event handler receives market data as it becomes available. In backtesting, data streams in chronological order simulating real-time delivery. In live trading, data arrives as the market produces it.

```python
def on_data(self, data):
    if not data.contains_key("SPY"):
        return
    price = data["SPY"].close
    if price > self.sma.current.value:
        self.set_holdings("SPY", 1.0)
    else:
        self.liquidate("SPY")
```

### End-of-Day Handler

Called at the end of each trading day for housekeeping: logging, position reviews, daily calculations.

```python
def on_end_of_day(self, symbol):
    self.log(f"{symbol}: {self.portfolio[symbol].profit}")
```

### Algorithm Shutdown

Called when the algorithm terminates (backtest complete or live session ends). Used for final reporting and cleanup.

## Core Managers

Trading algorithms typically interact with several subsystems:

| Manager | Purpose | Example |
|---------|---------|---------|
| **Securities** | Stores instrument objects with properties and models | `securities["SPY"].price` |
| **Portfolio** | Tracks holdings, P&L, margin, and aggregate performance | `portfolio["SPY"].unrealized_profit` |
| **Transactions** | Manages order submission, fills, and history | `transactions.get_open_orders()` |
| **Scheduler** | Triggers functions at specific times or market events | `schedule.on(date_rules.every_day(), time_rules.market_open())` |
| **Universe** | Manages dynamic instrument selection | `add_universe(coarse_selection_function)` |

## Event-Driven Model

Algorithmic trading systems are **event-driven**: the algorithm reacts to events (new data, fills, dividends, end-of-day) rather than running in a continuous loop.

**Key events**:
- **Data events**: New price bar or tick arrives
- **Order events**: An order is submitted, filled, or cancelled
- **Split/Dividend events**: Corporate actions affecting positions
- **Scheduled events**: Time-based triggers (e.g., rebalance monthly)
- **End-of-day events**: Daily housekeeping

This design prevents look-ahead bias because the algorithm only sees data up to the current simulated time.

## Backtesting vs Live Trading

| Aspect | Backtesting | Live Trading |
|--------|-------------|--------------|
| Data source | Historical files | Real-time market feed |
| Execution | Simulated fills | Actual broker execution |
| Speed | Fast-forward through history | Real-time clock |
| Slippage/Fees | Modeled | Actual |
| State | Deterministic | Subject to disconnections, partial fills |

The goal is **seamless portability**: the same algorithm code should work in both modes with minimal changes.

## Financial Application Notes

- Start with a simple strategy (e.g., moving average crossover) to learn the framework
- Always validate with out-of-sample backtesting before live deployment
- Use paper trading as an intermediate step between backtesting and live
- Keep initialization separate from strategy logic for clean, testable code
- Log extensively during development; reduce logging in production

## Summary

Every trading algorithm has the same fundamental structure: an initialization phase that configures instruments and parameters, event handlers that react to market data, and managers that track portfolio state. The event-driven architecture prevents look-ahead bias and enables seamless transition from backtesting to live trading.

## Source

- Based on [QuantConnect: Key Concepts — Getting Started](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/getting-started)
