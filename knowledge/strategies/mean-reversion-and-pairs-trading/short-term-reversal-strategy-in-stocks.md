# Short-Term Reversal Strategy in Stocks

## Overview

Long/short market-neutral strategy exploiting short-term price reversals in the top 100 most liquid US large-cap stocks. Goes long the 10 worst monthly performers and shorts the 10 best, rebalancing weekly. Based on De Groot, Huij & Zhou (2012).

## Academic Reference

- **Paper**: De Groot, Huij, & Zhou (2012) — short-term reversal in equities
- **Source**: Quantpedia

## Strategy Logic

### Universe Selection

Top 100 most liquid large-cap stocks by dollar volume.

### Signal Generation

Rate of Change (ROC) indicator with 22-day lookback period. Rank all 100 stocks by ROC.

### Entry / Exit Rules

- **Long**: 10 stocks with lowest ROC (worst performers).
- **Short**: 10 stocks with highest ROC (best performers).
- **Exit**: Positions reset at weekly rebalance; securities removed from universe are immediately liquidated.

### Portfolio Construction

Equal-weight: 50% long / 50% short. 5% per position. Market-neutral design.

### Rebalancing Schedule

Weekly. `Universe.UNCHANGED` returned on non-rebalance days to minimize computation.

## Key Indicators / Metrics

- Rate of Change (ROC): 22-day lookback
- Manual historical warm-up: 23 prior daily close prices
- Dollar volume ranking

## Backtest Performance

| Metric | 5-Year (2016–2021) | 2020 Crash (Feb–Mar) | 2020 Recovery (Mar–Jun) |
|--------|---------------------|----------------------|------------------------|
| Sharpe Ratio | 0.287 | -1.075 | 1.987 |
| Benchmark Sharpe | 0.754 | -1.467 | 7.942 |
| Variance | — | 0.798 | — |

Key finding: Outperforms during crashes but significantly lags during recoveries.

## Data Requirements

- **Asset Classes**: US equities (large-cap)
- **Resolution**: Daily
- **Lookback Period**: 23 days (ROC warm-up)
- **Universe**: Top 100 by dollar volume

## Implementation Notes

- Manual warm-up of ROC indicators using 23 prior daily closes.
- Weekly rebalancing triggered by calendar week change.
- `Universe.UNCHANGED` on non-rebalance days reduces computation.
- Python on QuantConnect LEAN.

## Risk Considerations

- "Significant underperformance relative to benchmark across most periods."
- High variance during volatile markets (0.798 vs. 0.416 benchmark during 2020 crash).
- Market regime dependency — momentum reversals unreliable outside crash periods.
- Transaction costs from weekly turnover of 20 positions not fully accounted for.
- Equal-weighting ignores risk characteristics of individual positions.
- Short availability and borrowing costs not modeled.

## Related Strategies

- [Short Term Reversal](short-term-reversal.md)
- [Short Term Reversal with Futures](short-term-reversal-with-futures.md)
- [Momentum - Short Term Reversal Strategy](../momentum/momentum-short-term-reversal-strategy.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/short-term-reversal-strategy-in-stocks)
