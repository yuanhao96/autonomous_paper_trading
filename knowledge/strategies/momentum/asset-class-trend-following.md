# Asset Class Trend Following

## Overview

A trend-following approach that allocates to asset classes trading above their 10-month simple moving average. When price is above SMA, go long with equal weight; when below, stay in cash. Simple binary trend filter across five major asset classes.

## Academic Reference

- **Paper**: "Asset Class Trend Following" — Quantpedia Screener #16
- **Link**: https://quantpedia.com/Screener/Details/16

## Strategy Logic

### Universe Selection

Five ETFs representing distinct asset classes:

| ETF | Asset Class |
|-----|-------------|
| SPY | US Equities |
| EFA | Foreign Equities |
| BND | Bonds |
| VNQ | Real Estate (REITs) |
| GSG | Commodities |

### Signal Generation

Simple Moving Average (SMA) with 10-month lookback (210 trading days):

```
If Close > SMA(210): Signal = Long
If Close <= SMA(210): Signal = Cash
```

### Entry / Exit Rules

- **Long**: When closing price exceeds the 10-month SMA.
- **Exit**: Positions liquidated when price falls below SMA.
- **Cash**: Held when no securities meet the trend criteria.

### Portfolio Construction

Equal weighting among all securities currently in uptrend. If only 2 of 5 ETFs are above SMA, portfolio is 50% invested, 50% cash.

### Rebalancing Schedule

Daily check (via `on_data` execution).

## Key Indicators / Metrics

- Simple Moving Average (SMA): 210-day (10-month) lookback
- Warm-up period: 10 months

## Backtest Performance

| Metric | Value |
|--------|-------|
| Start Date | May 1, 2007 |
| Initial Capital | $100,000 |

*(Detailed Sharpe/return metrics not disclosed.)*

## Data Requirements

- **Asset Classes**: Multi-asset ETFs (5 tickers)
- **Resolution**: Daily
- **Lookback Period**: 210 trading days (10 months)

## Implementation Notes

- Simple implementation using built-in SMA indicator.
- 10-month warm-up required before live trading.
- Daily evaluation — positions can change any day (not monthly like momentum variant).
- Python implementation on QuantConnect LEAN.

## Risk Considerations

- No drawdown controls beyond the trend filter itself.
- Equal weighting ignores volatility differences between asset classes.
- Whipsaw risk during choppy/sideways markets (frequent SMA crossovers).
- No transaction cost modeling — daily checks may generate excessive trades.
- Binary signal (all-in or all-out) may miss gradual trend changes.
- Cash drag during extended periods below SMA.

## Related Strategies

- [Asset Class Momentum](asset-class-momentum.md) — same universe, rotation instead of trend filter
- [Commodities Futures Trend Following](commodities-futures-trend-following.md)
- [Momentum and State of Market Filters](momentum-and-state-of-market-filters.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/asset-class-trend-following)
