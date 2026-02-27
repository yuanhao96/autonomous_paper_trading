# Seasonality Effect Based on Same-Calendar Month Returns

## Overview

Exploits documented seasonality patterns by ranking stocks on their same-calendar-month return from the prior year. Goes long the top 5 and shorts the bottom 5 from the 100 most liquid US equities, rebalancing monthly. Academic research documents expected monthly excess returns of ~1.88%.

## Academic Reference

- **Paper**: "Common Factors in Return Seasonalities" — NBER Working Paper w20815
- Documents seasonality patterns across equities, commodities, and country portfolios.

## Strategy Logic

### Universe Selection

1. US equities priced above $5.
2. Top 100 by dollar volume.

### Signal Generation

For each stock, compute the return during the same calendar month in the prior year. Example: August 2019 signal based on August 2018 return.

Monthly return = closing_price_end / closing_price_start.

### Entry / Exit Rules

- **Long**: Top 5 stocks by same-calendar-month return.
- **Short**: Bottom 5 stocks by same-calendar-month return.
- **Exit**: Liquidate positions outside the new monthly selection.

### Portfolio Construction

Equal-weight: 50% long / 50% short.

### Rebalancing Schedule

Monthly, at month end.

## Key Indicators / Metrics

- Same-calendar-month return (12-month lag)
- Dollar volume (liquidity screen)
- Price filter (> $5)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2012 – 2019 (10 years) |
| Sharpe Ratio | 0.128 |
| Benchmark (SPY) Sharpe | 0.773 |
| Expected Monthly Return | 1.88% (academic) |

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily
- **Lookback**: 12+ months (year-over-year comparison)
- **Data**: Daily closing prices, dollar volume

## Implementation Notes

- Coarse universe filters by dollar volume and price.
- Monthly returns computed from closing prices at month boundaries.
- Avoids ordering delisted securities.
- Liquidates positions outside new monthly universe.
- Python on QuantConnect LEAN.

## Risk Considerations

- Sharpe ratio (0.128) significantly underperforms benchmark (0.773) — anomaly may be too weak after transaction costs.
- Single-year lookback for seasonality is noisy — multi-year averaging (5+ years) may improve stability.
- Calendar anomalies may be arbitraged away as they become widely known.
- Monthly turnover of 10 positions generates meaningful transaction costs.
- Small number of positions (5 long, 5 short) increases concentration risk.
- Anomaly strength varies by asset class and time period.

## Related Strategies

- [12 Month Cycle in Cross-Section of Stocks Returns](12-month-cycle-cross-section.md)
- [January Effect in Stocks](january-effect-in-stocks.md)
- [Turn of the Month in Equity Indexes](turn-of-the-month-in-equity-indexes.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/seasonality-effect-based-on-same-calendar-month-returns)
