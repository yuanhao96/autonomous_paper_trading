# Volatility Effect in Stocks

## Overview

Exploits the low-volatility anomaly by going long the 5 least volatile stocks from the top 50 large-cap US equities. Uses a 252-day rolling standard deviation of daily returns to measure volatility. Equal-weight, long-only with monthly rebalancing.

## Academic Reference

- **Paper**: Quantpedia — "Volatility Effect in Stocks - Long-Only Version"

## Strategy Logic

### Universe Selection

1. US equities with fundamental data, priced above $5.
2. Top 100 by dollar volume.
3. Top 50 by market capitalization (large-cap only).

### Signal Generation

Calculate 252-day rolling standard deviation of daily returns (via RateOfChange indicator and RollingWindow). Rank all 50 stocks by volatility ascending.

### Entry / Exit Rules

- **Long**: 5 stocks with lowest 252-day volatility.
- **Exit**: Liquidate holdings not in the lowest-volatility cohort at monthly rebalance.
- Long-only — no short positions.

### Portfolio Construction

Equal-weight: 20% per position. Maximum 5 concurrent holdings.

### Rebalancing Schedule

Monthly, first trading day.

## Key Indicators / Metrics

- 252-day rolling standard deviation of daily returns
- RateOfChange (ROC) for daily return calculation
- Dollar volume and market capitalization screens

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Dec 2016 – Jun 2018 |
| Initial Capital | $100,000 |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: US equities (large-cap)
- **Resolution**: Daily
- **Lookback**: 252 trading days
- **Fundamental Data**: Market cap, P/E, earnings

## Implementation Notes

- Custom `SymbolData` class manages per-symbol volatility metrics.
- Historical data warming initializes RollingWindow at symbol addition.
- SPY benchmark reference security.
- Python on QuantConnect LEAN.

## Risk Considerations

- Concentrated portfolio (5 holdings) increases idiosyncratic risk.
- Backward-looking volatility may not predict future risk — low-vol stocks can suddenly become high-vol.
- Low-volatility anomaly has attracted significant capital — may be crowded and diminished.
- Large-cap only — misses small-cap low-vol opportunities.
- No risk management beyond the low-vol selection itself.
- Monthly rebalancing may be too slow during market stress.

## Related Strategies

- [Leveraged ETFs with Systematic Risk Management](leveraged-etfs-with-systematic-risk-management.md)
- [VIX Predicts Stock Index Returns](vix-predicts-stock-index-returns.md)
- [Momentum and Reversal Combined with Volatility Effect in Stocks](../momentum/momentum-and-reversal-combined-with-volatility-effect-in-stocks.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/volatility-effect-in-stocks)
