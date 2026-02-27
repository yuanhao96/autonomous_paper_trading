# Combining Momentum Effect with Volume

## Overview

Merges momentum investing with trading volume analysis by selecting stocks from the extreme momentum deciles that also have the highest turnover. High-volume momentum stocks tend to show stronger continuation effects.

## Academic Reference

- **Paper**: "Combining Momentum Effect with Volume" — Quantpedia Premium

## Strategy Logic

### Universe Selection

All NYSE and NASDAQ stocks with fundamental data available.

### Signal Generation

Two metrics combined:

1. **Momentum**: Rate of Change (ROC) with 252-day (12-month) lookback.
2. **Volume/Turnover**: Daily shares traded / basic average shares outstanding.

### Entry / Exit Rules

1. Sort all stocks into deciles by 12-month ROC.
2. Within top decile: select top 1% by turnover → **long positions**.
3. Within bottom decile: select top 1% by turnover → **short positions**.
4. Hold for 3 months; liquidate 3-month-old positions at rebalance.

### Portfolio Construction

Equal-weight within long/short segments. Rolling 3-month portfolios: 1/3 rebalanced monthly across staggered windows. Each stock gets `(1/3) × (1/N)` allocation.

Minimum requirement: 100 stocks with ready ROC indicators.

### Rebalancing Schedule

Monthly, with 3-month holding period (Jegadeesh-Titman overlapping portfolio approach).

## Key Indicators / Metrics

- Rate of Change (ROC): 252-day
- Turnover: shares traded / shares outstanding
- Decile ranking (momentum)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2012 – Aug 2018 |
| Initial Capital | $100,000 |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: US equities (NYSE, NASDAQ)
- **Resolution**: Daily
- **Lookback Period**: 252 days (12 months)
- **Fundamental Data**: Earning reports, basic average shares, daily volume

## Implementation Notes

- `SymbolData` objects maintain individual security metrics.
- ROC updated daily in coarse selection.
- Fine selection calculates turnover and implements decile/tercile sorting.
- Deque structure (maxlen=3) for portfolio history.
- Python on QuantConnect LEAN.

## Risk Considerations

- Very concentrated: top 1% of extreme deciles yields few stocks.
- 3-month holding period may miss momentum shifts.
- Turnover metric depends on accurate shares outstanding data.
- High-turnover stocks may have wider bid-ask spreads.
- Monthly rebalancing with staggered portfolios adds complexity.

## Related Strategies

- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)
- [Momentum and Reversal Combined with Volatility Effect in Stocks](momentum-and-reversal-combined-with-volatility-effect-in-stocks.md)
- [Liquidity Effect in Stocks](../factor-investing/liquidity-effect-in-stocks.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/combining-momentum-effect-with-volume)
