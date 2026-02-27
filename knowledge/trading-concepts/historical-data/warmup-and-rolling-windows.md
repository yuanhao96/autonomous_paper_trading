# Warmup & Rolling Windows

## Overview

Algorithms typically need historical data before they can start making decisions. Indicators
need a warmup period; strategies need lookback windows. Two key mechanisms handle this:
algorithm warmup and rolling windows.

## Algorithm Warmup

### What It Is

A pre-trading phase where historical data is fed through the algorithm's data pipeline.
During warmup, indicators receive data and build up their internal state. No orders are
placed, and no trading logic executes. Once warmup completes, the algorithm begins
trading with fully initialized indicators.

### When It's Needed

- Any algorithm using technical indicators (SMA, EMA, RSI, MACD, etc.).
- Strategies that calculate features from a historical lookback window.
- ML models that require a full feature vector on the very first trading bar.

### How to Set Warmup

- **By bar count**: Specify the number of bars to feed before trading begins.
  The engine calculates the required date range automatically, accounting for weekends
  and holidays. Example: "Warm up with 200 daily bars."
- **By time period**: Specify a calendar duration. Example: "Warm up with 30 days."
  This is simpler but less precise — 30 calendar days yields only ~21 trading days.
- **Best practice**: Set warmup >= the longest indicator period in the algorithm.

### Warmup Best Practices

1. **Check indicator readiness.** Before using an indicator's value, verify it has
   received enough data. An unready indicator may return zero or NaN.
2. **Do not place orders during warmup.** Treat warmup as a read-only phase.
3. **Initialize state variables.** Set baseline values for custom algorithm state.
4. **Account for nested indicators.** An indicator depending on another indicator
   needs warmup for the entire chain (e.g., 14-period RSI + 9-period EMA = 23 bars).

## Rolling Windows

### What They Are

Fixed-size FIFO (First In, First Out) data structures that store the most recent N values
of any data point. When a new value is added and the window is full, the oldest value is
automatically dropped. This provides a constant-memory, always-current lookback buffer.

### Common Uses

- Store recent closing prices for custom moving average calculations.
- Track recent highs and lows for channel breakout strategies.
- Maintain a lookback buffer for candlestick pattern detection.
- Store recent indicator values (RSI, MACD signal) for crossover logic.
- Keep a history of portfolio returns for risk calculations (Sharpe, drawdown).

### Implementation Pattern

1. Create a window of size N.
2. On each new bar or data event, add the latest value to the window.
3. The window reports "ready" once it has received N values and is at full capacity.
4. Access elements by index: `[0]` is the most recent, `[N-1]` is the oldest.
5. Never read from the window before it is ready — check its status first.

### Rolling Window vs History Request

| Feature | Rolling Window | History Request |
|---------|---------------|-----------------|
| Speed | Very fast (in-memory) | Slower (data fetch) |
| Data freshness | Always current | Point-in-time snapshot |
| Memory | Fixed (exactly N values) | Varies with request |
| Use case | Ongoing lookback | One-time analysis |
| Setup cost | Requires warmup to fill | Immediate from disk |

Use rolling windows for data needed continuously. Use history requests for one-off
calculations or data that does not need to update each bar.

## Combining Warmup and Rolling Windows

1. **Set warmup period** >= largest rolling window size.
2. **Feed data into rolling windows** during warmup. Each warmup bar updates windows
   just as a live bar would.
3. **Verify readiness.** By the time warmup ends, all rolling windows should be full.
4. **Continue updating.** On each new live bar, add the latest value; the oldest drops
   off automatically.

This ensures your algorithm has a complete lookback buffer from the very first trading bar.

## Key Takeaways

1. Always warm up your algorithm before trading — uninitialized indicators produce garbage.
2. Set warmup to at least the longest indicator period (or longest rolling window size).
3. Use rolling windows for ongoing, fixed-size lookback; use history requests for one-off analysis.
4. Check readiness of both indicators and rolling windows before reading their values.
5. Combine warmup and rolling windows so that everything is initialized on bar one.

---

Source: Generalized from QuantConnect Historical Data documentation.
