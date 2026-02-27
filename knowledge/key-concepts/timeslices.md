# Timeslices

## Overview

Covers the timeslice concept: how an algorithmic trading engine synchronizes multiple data streams into unified snapshots at each point in time. The timeslice is the fundamental unit of data delivery to a trading algorithm, ensuring consistent and synchronized access to all subscribed instruments.

## What is a Timeslice?

A **timeslice** represents all available data at a single moment in time. When an algorithm subscribes to multiple instruments (potentially with different resolutions and from different exchanges), the engine:

1. Collects incoming data from all subscriptions
2. Synchronizes events by timestamp
3. Groups all concurrent data into a single timeslice
4. Delivers the timeslice to the algorithm's data handler

The algorithm receives one timeslice at a time, in strictly chronological order.

## The Time Frontier

The **time frontier** is the current simulation time — the latest point in time for which the algorithm has received data.

### Key Properties

- The algorithm can only see data at or before the time frontier
- Security prices reflect their values as of the time frontier
- Any data with a timestamp beyond the frontier is invisible to the algorithm
- The time frontier advances with each new timeslice

```
Time Frontier: 10:01:00 AM

Algorithm can see:
  ✓ All data up to 10:01:00 AM
  ✓ SPY minute bar (10:00-10:01)
  ✓ EURUSD tick at 10:00:59

Algorithm cannot see:
  ✗ SPY minute bar (10:01-10:02) — not yet complete
  ✗ Any data after 10:01:00 AM
```

### Why It Matters

The time frontier is the mechanism that **prevents look-ahead bias** in backtesting. By strictly enforcing chronological data delivery, the engine ensures the algorithm makes decisions using only information that would have been available at that time in live trading.

## Timeslice Contents

A typical timeslice may contain:

| Data Type | Description |
|-----------|-------------|
| **Trade bars** | OHLCV bars for subscribed instruments |
| **Quote bars** | Bid/ask bars for subscribed instruments |
| **Ticks** | Individual trade/quote events |
| **Dividends** | Dividend declarations for held equities |
| **Splits** | Stock split events |
| **Delistings** | Security delisting notifications |
| **Option chains** | Available option contracts and prices |
| **Futures chains** | Available futures contracts and prices |
| **Custom data** | User-defined data types |

Not every timeslice contains data for every instrument — only instruments with new data at that timestamp are included.

## Data Synchronization

### Same Resolution, Different Instruments

When subscribed to multiple instruments at the same resolution (e.g., minute bars for SPY, AAPL, GOOG):
- All minute bars ending at the same time arrive in one timeslice
- The algorithm sees a consistent snapshot across all instruments

### Mixed Resolutions

When using different resolutions (e.g., SPY at minute, EURUSD at tick):
- Timeslices are created at the finest resolution
- Higher-resolution instruments may not have new data in every slice
- Check for data existence before accessing: `if "SPY" in data:`

### Cross-Exchange Synchronization

When trading instruments on different exchanges with different market hours:
- The engine aligns data by timestamp
- Instruments on closed exchanges show stale (fill-forward) prices
- Only instruments with active markets produce new data

## Accessing Timeslice Data

```python
def on_data(self, data):
    # Check if specific instrument has new data
    if data.contains_key("SPY"):
        spy_bar = data["SPY"]
        price = spy_bar.close

    # Iterate all available bars
    for symbol, bar in data.bars.items():
        print(f"{symbol}: {bar.close}")

    # Check for corporate events
    for symbol, dividend in data.dividends.items():
        print(f"Dividend: {symbol} pays {dividend.distribution}")
```

## Processing Order Within a Timeslice

The engine performs these steps for each timeslice:

1. **Check scheduled events**: Fire any events whose trigger time has passed
2. **Update security prices**: Refresh prices for all instruments with new data
3. **Process pending orders**: Attempt to fill any open orders using new prices
4. **Call on_data()**: Deliver the timeslice to the algorithm
5. **Process new orders**: Submit any orders created by the algorithm
6. **Update portfolio**: Recalculate portfolio values and statistics

## Financial Application Notes

- Always check for data existence before accessing — not every slice contains every instrument
- The time frontier ensures backtest fidelity by preventing future data access
- Mixed-resolution subscriptions create more timeslices, increasing computation time
- Cross-exchange strategies must account for stale prices from closed markets
- The processing order (update prices → fill orders → call handler → submit new orders) means your handler sees updated prices but orders from the current handler only execute on the next slice

## Summary

A timeslice is a synchronized snapshot of all available market data at a single point in time. The time frontier advances chronologically, ensuring the algorithm never sees future data. The engine synchronizes data across instruments, resolutions, and exchanges, delivering a consistent view for decision-making. Understanding timeslices is essential for writing correct multi-instrument, multi-resolution strategies.

## Source

- Based on [QuantConnect: Key Concepts — Time Modeling — Timeslices](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/time-modeling/timeslices)
