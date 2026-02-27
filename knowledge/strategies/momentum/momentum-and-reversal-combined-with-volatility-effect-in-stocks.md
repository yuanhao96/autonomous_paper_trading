# Momentum and Reversal Combined with Volatility Effect in Stocks

## Overview

Merges momentum and reversal tactics with realized volatility analysis. Focuses on the highest-volatility quintile of stocks, then goes long recent winners and short recent losers within that group. Uses staggered 6-month holding periods (1/6 rebalanced monthly).

## Academic Reference

- **Paper**: "Momentum and Reversal Combined with Volatility Effect in Stocks" — Quantpedia #155

## Strategy Logic

### Universe Selection

1. NYSE, AMEX, NASDAQ stocks priced above $5.
2. Top 50% by market capitalization (shares × price).
3. Must have fundamental data.

### Signal Generation

**Volatility** (6-month lookback, excluding final 5 trading days):
```
σ = √(Σ(Rᵢ - R_avg)² / (n-1)) × √252   (annualized)
```

**Return** (6-month lookback, excluding final 5 days):
- Realized return over same period.
- 5-day exclusion reduces microstructure bias.

### Entry / Exit Rules

1. Rank filtered universe by annualized volatility → select top 20% (highest volatility quintile).
2. Within high-volatility group, rank by 6-month return.
3. **Long**: Top 20% by return (within high-vol group).
4. **Short**: Bottom 20% by return (within high-vol group).

### Portfolio Construction

Equal-weight within long/short buckets. Staggered 6-month holding: maintains 6 overlapping portfolios, 1/6 rebalanced each month.

### Rebalancing Schedule

Monthly (Jegadeesh-Titman approach), with 6-month holding period.

## Key Indicators / Metrics

- Annualized realized volatility (6-month window, 5-day exclusion)
- 6-month realized return (5-day exclusion)
- Market capitalization (size filter)
- Quintile double-sort (volatility then return)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2014 – Aug 2018 |
| Initial Capital | $100,000 |
| Resolution | Daily |
| Warm-up | 6 months |

## Data Requirements

- **Asset Classes**: US equities (NYSE, AMEX, NASDAQ)
- **Resolution**: Daily
- **Lookback Period**: 120 trading days (6 months)
- **Fundamental Data**: Market cap, price

## Implementation Notes

- `SymbolData` class: deque (max 120 days) for price history, computes volatility and return.
- Coarse selection: daily price updates, fundamental screening.
- Fine selection: market cap sorting.
- Scheduled monthly rebalance.
- Security initializer prevents trading errors.

## Risk Considerations

- Focuses on high-volatility stocks — inherently riskier universe.
- Double-sort reduces universe size significantly — potential for few holdings.
- 5-day exclusion window is somewhat arbitrary.
- Staggered 6-month portfolios add implementation complexity.
- Momentum in high-vol stocks may experience sharper reversals.
- Transaction costs from monthly turnover in volatile names.

## Related Strategies

- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)
- [Momentum - Short Term Reversal Strategy](momentum-short-term-reversal-strategy.md)
- [Volatility Effect in Stocks](../volatility-and-options/volatility-effect-in-stocks.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/momentum-and-reversal-combined-with-volatility-effect-in-stocks)
