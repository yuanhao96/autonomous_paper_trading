# ROA Effect Within Stocks

## Overview

Exploits the profitability anomaly — firms with high Return on Assets (ROA) tend to outperform those with low ROA. The strategy constructs a long-short portfolio based on ROA rankings within size-matched groups, capturing the quality premium while controlling for the size effect.

## Academic Reference

- **Paper**: "ROA Effect Within Stocks" — Quantpedia Screener
- **Link**: https://quantpedia.com/

## Strategy Logic

### Universe Selection

1. Select all stocks listed on NYSE, AMEX, and NASDAQ exchanges.
2. Filter for companies with sales greater than $10 million.
3. Exclude stocks with zero or missing Earnings Per Share (EPS), Price-to-Earnings (PE) ratio, or Return on Assets (ROA).

### Signal Generation

Return on Assets is used as the ranking signal:

```
ROA = Net Income / Total Assets
```

Stocks are first split into two size groups (large cap and small cap) by median market capitalization, then ranked by ROA within each size group independently.

### Entry / Exit Rules

- **Entry (Long)**: Go long the top 10% of stocks by ROA within each size group.
- **Entry (Short)**: Go short the bottom 10% of stocks by ROA within each size group.
- **Exit**: Liquidate positions at each monthly rebalance for stocks that no longer qualify for the top or bottom decile.

### Portfolio Construction

- Equal-weight allocation within each leg (long and short).
- 50/50 capital allocation between the long and short sides.
- Combined portfolio constructed from both large-cap and small-cap sub-portfolios.

### Rebalancing Schedule

Monthly. Recalculate ROA rankings and reconstitute the portfolio at the end of each month.

## Key Indicators / Metrics

- **Return on Assets (ROA)**: Net Income / Total Assets
- **Market Capitalization**: Used for size group assignment (large/small split at median)
- **Sales**: Minimum $10M threshold for universe inclusion
- **EPS / PE Ratio**: Non-zero requirement for quality screening

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | Jan 2015 – Aug 2020 | SPY |
| Initial Capital | $10,000,000 | — |
| Resolution | Daily | — |

*(Detailed Sharpe/return metrics not disclosed in source.)*

## Data Requirements

- **Asset Classes**: US equities (NYSE, AMEX, NASDAQ)
- **Resolution**: Daily prices; quarterly/annual fundamental data
- **Lookback Period**: Most recent fiscal quarter/year for ROA calculation
- **Fundamental Data**: Net Income, Total Assets, Sales, EPS, PE Ratio, Market Capitalization

## Implementation Notes

- Universe selection requires filtering on multiple fundamental fields simultaneously.
- Size-group split at median market cap must be recalculated at each rebalance to reflect current market conditions.
- ROA ranking is performed independently within each size group to avoid large-cap bias.
- Python implementation on QuantConnect LEAN engine using fine universe selection.

## Risk Considerations

- ROA is backward-looking and may not reflect future profitability.
- Monthly rebalancing in a large universe can generate significant transaction costs.
- Short leg may include distressed companies with elevated borrowing costs and short-squeeze risk.
- Strategy performance may weaken during momentum-driven markets where unprofitable, high-growth stocks outperform.
- Accounting manipulation can distort ROA figures, particularly for firms near the screening thresholds.

## Related Strategies

- [Earnings Quality Factor](earnings-quality-factor.md)
- [Accrual Anomaly](accrual-anomaly.md)
- [Asset Growth Effect](asset-growth-effect.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/roa-effect-within-stocks)
