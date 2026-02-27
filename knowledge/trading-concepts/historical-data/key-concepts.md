# Historical Data — Key Concepts

## Overview

Historical data is the foundation of algorithmic trading — used for backtesting strategies,
training models, calculating indicators, and making informed decisions. Understanding how to
access, process, and use historical data correctly is essential for building robust trading
systems.

## Data Types

### Price Data

| Type | Fields | Use |
|------|--------|-----|
| Trade Bar (OHLCV) | Open, High, Low, Close, Volume | Most common, standard charts |
| Quote Bar | Bid OHLC, Ask OHLC, Bid/Ask Size | Market microstructure |
| Tick Data | Price, Quantity, Exchange | High-frequency analysis |
| Renko Bar | Fixed price movement bricks | Noise filtering |

**Trade bars** aggregate individual trades into time-based intervals. Each bar captures the
first trade (open), highest trade (high), lowest trade (low), last trade (close), and total
shares/contracts traded (volume) within the interval.

**Quote bars** capture the best bid and ask over each interval. They are essential for
strategies that depend on spread analysis or need to model realistic fill prices.

**Tick data** represents every individual trade or quote update. It provides the highest
granularity but generates enormous data volumes.

### Time Resolutions

| Resolution | Bar Duration | Data Points/Year (approx.) | Use Case |
|-----------|-------------|----------------------------|----------|
| Tick | Single trade | Millions | HFT, microstructure |
| Second | 1 second | ~23.4M | Short-term intraday |
| Minute | 1 minute | ~98K | Intraday strategies |
| Hour | 1 hour | ~1,638 | Swing trading |
| Daily | 1 day | ~252 | Most strategies |
| Weekly | 1 week | ~52 | Long-term analysis |
| Monthly | 1 month | 12 | Asset allocation |

Choosing the right resolution is a tradeoff between granularity and computational cost.
Most strategies operate at daily or minute resolution. Higher resolutions (tick, second)
require significantly more storage and processing power.

### Alternative Data

- Fundamental data (earnings, revenue, balance sheet)
- Sentiment data (news, social media)
- Economic indicators (GDP, CPI, unemployment)
- Satellite/geospatial data
- Options flow data
- Insider trading filings

## Data Quality Considerations

- **Survivorship bias**: Only including currently existing securities. Historical datasets
  should include delisted companies to avoid inflated backtest returns.
- **Look-ahead bias**: Using data that was not available at the time of the trade decision.
  Always ensure data timestamps reflect when the data was actually accessible.
- **Split/dividend adjustments**: Raw prices reflect actual traded prices; adjusted prices
  account for corporate actions. Using the wrong type leads to false signals.
- **Corporate actions**: Mergers, spinoffs, delistings, and name changes can create
  discontinuities in price series that must be handled correctly.
- **Data gaps**: Missing bars can occur due to trading halts, exchange outages, or low
  liquidity. Strategies should handle gaps gracefully rather than assuming continuous data.

## Data Normalization

| Mode | Description | When to Use |
|------|-------------|-------------|
| Raw | Actual traded prices, no adjustments | Order fill simulation |
| Adjusted | Prices adjusted for splits and dividends | Indicator calculation |
| Total Return | Adjusted for splits, includes dividend reinvestment | Performance measurement |

**Important**: Use raw data for backtesting order fills so that limit/stop prices match
actual historical prices. Use adjusted data for technical indicators so that moving averages
and other calculations are not distorted by splits or dividends.

## Data Storage Formats

- **CSV**: Simple, portable, human-readable. Common for daily data.
- **Parquet**: Columnar, compressed, fast reads. Preferred for large datasets.
- **HDF5**: Hierarchical, supports complex data structures. Good for tick data.
- **Database (SQL/NoSQL)**: Queryable, supports concurrent access. Best for production.

## Key Takeaways

1. Match your data resolution to your strategy timeframe — do not over-fetch.
2. Always account for survivorship and look-ahead bias in backtests.
3. Understand the difference between raw and adjusted prices and use each appropriately.
4. Validate data quality before trusting backtest results.
5. Consider storage format tradeoffs as your dataset grows.

---

Source: Generalized from QuantConnect Historical Data documentation.
