# Periods

## Overview

Covers how market data is aggregated into bars of different time periods, the distinction between bar data and tick data, data delivery timing, and fill-forward behavior. Understanding data periods is essential for correct signal generation and avoiding look-ahead bias.

## Bar Data (Period Data)

Bar data represents market activity aggregated over a fixed time period. Each bar has a **start time** and **end time** defining the period it covers.

### Trade Bars (OHLCV)

The most common bar type, aggregating trade activity:

| Field | Description |
|-------|-------------|
| **Open** | First trade price in the period |
| **High** | Highest trade price in the period |
| **Low** | Lowest trade price in the period |
| **Close** | Last trade price in the period |
| **Volume** | Total shares/contracts traded in the period |
| **Time** | Bar start time |
| **EndTime** | Bar end time |

### Quote Bars (Bid/Ask)

Aggregated bid-ask quotes over the period:

| Field | Description |
|-------|-------------|
| **Bid Open/High/Low/Close** | Best bid prices during the period |
| **Ask Open/High/Low/Close** | Best ask prices during the period |
| **Last Bid/Ask Size** | Quote sizes at the end of the period |

Quote bars are important for forex, options, and other instruments where the bid-ask spread is a significant factor.

## Data Resolutions

| Resolution | Period Length | Use Case |
|-----------|-------------|----------|
| **Tick** | No period (point-in-time) | High-frequency, microstructure research |
| **Second** | 1 second | Short-term intraday strategies |
| **Minute** | 1 minute | Intraday trading, most common for algo trading |
| **Hour** | 1 hour | Swing trading, medium-frequency strategies |
| **Daily** | 1 trading day | Position trading, long-term strategies |

### Custom Periods

Most frameworks support consolidating base data into custom periods:
- 5-minute bars from minute data
- 15-minute bars from minute data
- Weekly bars from daily data
- Monthly bars from daily data

This is typically done via **consolidators** that aggregate incoming data into larger bars.

## Data Delivery Timing

**Critical rule**: A bar is delivered to the algorithm only when its period is complete — at the bar's **EndTime**, not its start time.

This prevents look-ahead bias:
- A 1-minute bar spanning 10:00–10:01 is delivered at 10:01
- A daily bar for Monday is delivered at market close (or Tuesday's open)
- The close price is unknown until the bar is complete

### Timeline Example

```
Market opens 9:30 AM

9:30-9:31 bar → delivered at 9:31 (algorithm sees it at 9:31)
9:31-9:32 bar → delivered at 9:32
...
3:59-4:00 bar → delivered at 4:00 (market close)
Daily bar    → delivered at next session open (or midnight)
```

### Weekend/Holiday Data

- Friday's daily bar is typically emitted Saturday at midnight
- Orders placed on stale weekend data become market-on-open orders for Monday
- This avoids executing at stale Friday prices

## Tick Data (Point Data)

Tick data represents individual discrete market events (trades or quotes). Unlike bars:

- **No period**: Time and EndTime are identical
- **Immediate delivery**: Emitted as soon as received
- **Cannot be filled forward**: No interpolation between ticks
- **Higher data volume**: Thousands of ticks per minute for liquid instruments

### Tick Types

| Type | Description |
|------|-------------|
| **Trade tick** | A single executed trade (price, size) |
| **Quote tick** | A bid/ask update (bid price/size, ask price/size) |

## Fill-Forward Behavior

When no trading activity occurs during a bar period, the engine can optionally **fill forward** the last known price:

- A stale bar is created with OHLC = last close price, volume = 0
- This prevents null/missing data issues in the algorithm
- Useful for illiquid instruments or off-hours periods

**Important**: Fill-forward data represents no new information — do not generate signals from fill-forward bars.

## Financial Application Notes

- Always use the bar's EndTime, not start time, for decision-making to avoid look-ahead bias
- Higher resolution data (tick, second) increases computational cost and data storage
- Daily bars are sufficient for most swing/position trading strategies
- Minute bars are the standard for intraday strategy research
- Custom period consolidators are essential for multi-timeframe analysis
- Be aware of fill-forward bars when checking for "new" data

## Summary

Market data can be represented as bars (aggregated over periods) or ticks (individual events). Bars have defined start and end times and are delivered only when complete, preventing look-ahead bias. Standard resolutions range from tick to daily, with custom periods available via consolidation. Fill-forward behavior handles data gaps for illiquid instruments. Correct understanding of data periods and delivery timing is foundational to reliable algorithm development.

## Source

- Based on [QuantConnect: Key Concepts — Time Modeling — Periods](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/time-modeling/periods)
