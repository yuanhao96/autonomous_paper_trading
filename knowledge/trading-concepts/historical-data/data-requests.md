# Data Requests & Responses

## Overview

Algorithms need to request historical data for indicator warmup, lookback analysis, and
feature calculation. Understanding how to efficiently request and process data is critical
for both backtest performance and live trading reliability.

## Request Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| Symbol(s) | Asset(s) to request | SPY, AAPL, EURUSD |
| Resolution | Bar size | Minute, Daily |
| Period / Start-End | Time range | 30 days, or 2020-01-01 to 2020-12-31 |
| Data type | Bar type | Trade bars, quote bars |

Every history request should specify these four dimensions. Omitting any one can lead to
unexpected defaults — for instance, requesting daily data when you intended minute data.

## Request Patterns

### Lookback by Period

- Request the last N bars of data ending at the current algorithm time.
- Example: "Get the last 200 daily bars for SPY."
- The engine automatically adjusts for weekends, holidays, and non-trading days.
- This is the most common pattern for indicator warmup and rolling calculations.

### Lookback by Time Range

- Request all data between a start date and an end date.
- Example: "Get minute data from 2024-01-01 to 2024-06-30."
- Useful for research, feature engineering, and training ML models on fixed windows.
- Be mindful of the data volume — a six-month minute request yields ~600K bars per symbol.

### Multi-Asset Requests

- Request data for multiple securities in a single call.
- Returns synchronized data aligned by timestamp.
- Handle missing data: some assets may not trade on certain dates or at certain times.
- Multi-asset requests are more efficient than looping over individual symbol requests.

## Response Formats

### DataFrame Format

- Rows indexed by timestamp.
- Columns for OHLCV fields (Open, High, Low, Close, Volume).
- Multi-index (symbol, timestamp) for multi-asset requests.
- Ideal for vectorized calculations with libraries like pandas or numpy.

### Object/List Format

- A list of bar objects, each with typed properties (e.g., bar.Close, bar.Volume).
- Easier for event-driven iteration and procedural logic.
- Common in frameworks where each bar triggers a callback function.

## Performance Considerations

- **Request only what you need.** Minimize resolution and period to reduce data volume.
- **Cache reusable data.** If multiple indicators use the same history, request it once.
- **Avoid tick data unless necessary.** Tick data is 10-100x larger than minute data and
  dramatically slows backtests.
- **Pre-compute features during warmup.** Calculate derived values (moving averages,
  z-scores, etc.) as data streams in, rather than re-requesting full history each bar.
- **Batch multi-symbol requests.** A single call for 50 symbols is faster than 50 calls.

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Empty result | Requesting data outside market hours or before listing date | Check the asset's trading calendar and IPO date |
| Resolution mismatch | Requesting minute data for an asset with only daily data | Verify available resolutions for the data source |
| Timezone confusion | Assuming local time when the engine uses UTC (or vice versa) | Always be explicit about timezone in date parameters |
| Insufficient history | Requesting 200 daily bars for a stock listed 3 months ago | Clamp the request to available history |
| Stale data | Caching data without refreshing on new bars | Invalidate cache at each new time step |

## Key Takeaways

1. Always specify symbol, resolution, period, and data type explicitly.
2. Prefer period-based lookbacks for ongoing strategies; use date ranges for research.
3. Optimize for performance by caching, batching, and minimizing resolution.
4. Validate response data before feeding it into indicators or models.

---

Source: Generalized from QuantConnect Historical Data documentation.
