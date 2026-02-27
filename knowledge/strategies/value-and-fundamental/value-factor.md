# Value Factor

## Overview

Exploits the value premium — the empirical observation that stocks with low valuation ratios (low price-to-book, low price-to-earnings) tend to outperform high-valuation stocks over the long term. One of the original Fama-French factors, the value effect has been documented across markets and time periods.

## Academic Reference

- **Paper**: "The Cross-Section of Expected Stock Returns", Fama and French (1992)
- **Link**: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=227467

## Strategy Logic

### Universe Selection

Broad universe of US equities with available fundamental data (price-to-book, price-to-earnings, or other valuation metrics).

### Signal Generation

Rank stocks by a valuation metric (e.g., book-to-market ratio):

```
Value_Score = Book_Value / Market_Cap  (or E/P, CF/P, etc.)
```

### Entry / Exit Rules

- **Entry**: Go long the top quintile (cheapest) stocks by value score.
- **Exit**: Sell when a stock drops out of the top quintile at rebalance.
- Long-short variant: also short the bottom quintile (most expensive).

### Portfolio Construction

Equal-weight or market-cap-weight within the value portfolio. Typically 20–50 stocks.

### Rebalancing Schedule

Monthly or quarterly.

## Key Indicators / Metrics

- **Book-to-market ratio**: Primary valuation metric
- **Earnings yield (E/P)**: Alternative valuation metric
- **Lookback**: 126 trading days for momentum-based proxy when fundamental data unavailable

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | 1926–2020 | Market portfolio |
| Annual Return | ~12% | ~10% |
| Sharpe Ratio | ~0.5–0.7 | ~0.4 |
| Max Drawdown | ~50% | ~55% |

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily prices + quarterly fundamentals
- **Lookback Period**: Quarterly fundamental updates; 126 days for momentum proxy

## Implementation Notes

- When fundamental data is unavailable (e.g., in a price-only backtest), a momentum-based proxy can be used: positive long-term returns suggest relative value.
- The HML (High Minus Low) factor from Fama-French captures the value premium.
- Combining value with momentum reduces drawdowns (the two factors are negatively correlated).

## Risk Considerations

- Value traps — cheap stocks may be cheap for good reasons (deteriorating fundamentals).
- Extended periods of value underperformance (e.g., 2018–2020 growth dominance).
- Requires fundamental data that may not be available for all universes.
- Size bias — value premium is stronger in small-cap stocks.

## Related Strategies

- [Book-to-Market Value Anomaly](book-to-market-value-anomaly.md)
- [Price-Earnings Anomaly](price-earnings-anomaly.md)
- [Fama-French Five Factors](../factor-investing/fama-french-five-factors.md)
- [G-Score Investing](g-score-investing.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/value-factor)
