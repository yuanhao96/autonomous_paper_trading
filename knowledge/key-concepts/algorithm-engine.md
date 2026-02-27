# Algorithm Engine

## Overview

Describes the architecture and execution model of an algorithmic trading engine. Covers the event-driven data flow, how data is synchronized and delivered to algorithms, the execution lifecycle, and the differences between backtesting and live trading modes.

## Engine Architecture

An algorithmic trading engine consists of several interconnected components:

```
Data Feed → Data Synchronizer → Algorithm Manager → Order Manager → Brokerage
     ↑                                                      |
     └──────────── Fill/Event Feedback ──────────────────────┘
```

### Core Components

| Component | Role |
|-----------|------|
| **Data Feed** | Connects to data sources; streams tick/bar data |
| **Data Synchronizer** | Aligns data from multiple sources into time-ordered slices |
| **Algorithm Manager** | Executes the user's algorithm logic on each data slice |
| **Transaction Handler** | Processes order submissions, manages open orders |
| **Portfolio Manager** | Tracks positions, P&L, margin, buying power |
| **Risk Manager** | Enforces pre-trade risk limits |
| **Results Handler** | Collects performance metrics, generates reports |

### Data Feed

The data feed is responsible for sourcing market data:
- **Backtesting**: Reads historical data from files/databases, replaying it in chronological order
- **Live trading**: Connects to a real-time stream (exchange feeds, broker APIs, third-party data providers)
- **Multi-resolution support**: Can simultaneously handle tick, second, minute, hourly, and daily data for different instruments

### Data Synchronization

When trading multiple instruments across different exchanges and time zones, the engine must synchronize all data streams:

1. Receive raw data events from all subscriptions
2. Sort/align events by timestamp
3. Group concurrent events into a single **timeslice**
4. Deliver the timeslice to the algorithm

This ensures the algorithm sees a consistent snapshot of all instruments at each point in time.

## Execution Lifecycle

### 1. Initialization Phase

The engine loads the algorithm, calls `initialize()`, and sets up:
- Data subscriptions and resolution
- Starting capital and date range
- Brokerage and reality models (fees, slippage, margin)

### 2. Main Loop (Event Processing)

For each timeslice:
1. Check for scheduled events that should fire
2. Update security prices and properties
3. Process any pending order fills
4. Call the algorithm's `on_data()` handler
5. Process any new orders submitted by the algorithm
6. Update portfolio values and statistics

### 3. End-of-Day Processing

At the end of each trading day:
- Call `on_end_of_day()` for each security
- Update daily statistics (P&L, drawdown, etc.)
- Run any scheduled daily events

### 4. Termination

When the backtest completes or live session ends:
- Call `on_end_of_algorithm()`
- Generate final performance report
- Close all data connections

## Event Types

| Event | Trigger | Purpose |
|-------|---------|---------|
| **Data** | New bar/tick available | Primary strategy logic |
| **Order** | Order submitted/filled/cancelled | Track execution |
| **Split** | Stock split detected | Adjust positions and history |
| **Dividend** | Dividend payment | Handle cash inflow, adjust cost basis |
| **Delistings** | Security delisted | Forced liquidation |
| **Scheduled** | User-defined time trigger | Rebalancing, reporting |

## Backtesting vs Live Mode

### Backtesting
- Data replayed from historical files in fast-forward
- Fills simulated using configurable fill models
- Scheduled events fire when the simulated clock passes their trigger time
- Deterministic: same inputs produce same outputs

### Live Trading
- Data arrives in real-time from broker/exchange
- Orders sent to actual broker for execution
- Scheduled events fire based on real-time clock (parallel thread)
- Non-deterministic: network latency, partial fills, disconnections

### Streaming vs Batch Processing

Trading engines use **streaming analysis**: data arrives point by point in chronological order, and the algorithm can only see present and past data — never the future. This is critical for:
- Preventing look-ahead bias in backtests
- Ensuring backtest results are representative of live performance
- Making algorithm code portable between backtest and live modes

## Multi-Threading

Modern trading engines use multiple threads:
- **Data thread**: Downloads and preprocesses data
- **Algorithm thread**: Runs strategy logic
- **Transaction thread**: Manages order processing
- **Results thread**: Computes and reports statistics

This parallelism maximizes throughput while maintaining data consistency.

## Financial Application Notes

- The event-driven model is the standard architecture for professional trading systems
- Understanding the execution lifecycle helps debug unexpected behavior (e.g., orders not filling, missed events)
- Data synchronization is critical for multi-asset strategies — incorrect timing can create false signals
- The streaming model prevents the most common backtesting pitfall: look-ahead bias
- Know the differences between backtest and live execution to avoid live trading surprises

## Summary

The algorithm engine orchestrates data flow from sources through synchronization to algorithm execution. Its event-driven, streaming architecture processes data chronologically, preventing look-ahead bias. Key components include the data feed, synchronizer, algorithm manager, and transaction handler. Understanding this architecture is essential for building reliable trading algorithms that perform consistently in both backtesting and live environments.

## Source

- Based on [QuantConnect: Key Concepts — Algorithm Engine](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/algorithm-engine)
