# Standardized Unexpected Earnings

## Overview

Exploits the post-earnings-announcement drift (PEAD) anomaly — the tendency for stocks with positive earnings surprises to continue outperforming after the announcement. The strategy computes a Standardized Unexpected Earnings (SUE) score for each stock by comparing current quarterly EPS to the same quarter one year ago, normalized by the historical variability of EPS changes, and goes long stocks with the highest SUE scores.

## Academic Reference

- **Paper**: "Earnings Releases, Anomalies, and the Behavior of Security Returns" — George Foster, Chris Olsen, Terry Shevlin, 1984
- **Link**: https://doi.org/10.2307/2490930

## Strategy Logic

### Universe Selection

1. **Coarse filter**: Select US equities with sufficient price and volume, excluding ETFs.
2. **Data requirement**: Stocks must have at least 8 quarters of EPS history (36-month warm-up period) to compute the SUE denominator.

### Signal Generation

Standardized Unexpected Earnings (SUE) is calculated as:

```
SUE = (EPS_q - EPS_{q-4}) / sigma(EPS changes over 8 quarters)
```

Where:
- `EPS_q` = earnings per share for the current quarter
- `EPS_{q-4}` = earnings per share for the same quarter one year ago
- `sigma` = standard deviation of the last 8 quarterly EPS changes (EPS_q - EPS_{q-4})

Higher SUE indicates a larger positive earnings surprise relative to the stock's historical earnings variability.

### Entry / Exit Rules

- **Entry (Long)**: Go long the top 5% of stocks ranked by SUE score.
- **Exit**: Liquidate positions for stocks that fall out of the top 5% at rebalance.

### Portfolio Construction

Long-only, equal-weight allocation across all stocks in the top 5% SUE bucket.

### Rebalancing Schedule

Monthly. SUE scores are recalculated as new quarterly earnings data becomes available.

## Key Indicators / Metrics

- **SUE score**: Standardized measure of earnings surprise magnitude
- **Quarterly EPS**: Earnings per share (trailing four quarters of changes)
- **EPS change volatility**: Standard deviation of 8 quarterly year-over-year EPS changes

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | Dec 2009 – Sep 2019 | SPY |
| Initial Capital | $100,000 | — |
| Sharpe Ratio | 0.602 | 0.43 |

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily
- **Lookback Period**: 36 months (warm-up for 8 quarters of EPS data)
- **Fundamental Data**: Quarterly earnings per share (EPS)

## Implementation Notes

- Requires a 36-month warm-up period before the first trade can be generated, as 8 quarters of EPS history are needed to compute the standard deviation in the SUE denominator.
- Built using QuantConnect's Algorithm Framework pattern (Alpha model, Universe Selection model, Portfolio Construction model, Execution model).
- EPS data must be point-in-time to avoid look-ahead bias; use as-reported earnings rather than restated figures.
- The strategy recalculates SUE scores monthly but only updates when new quarterly earnings data is released.
- Python implementation on QuantConnect LEAN engine.

## Risk Considerations

- PEAD has been extensively documented and may be partially arbitraged away in liquid large-cap stocks.
- SUE scores are only updated quarterly (when earnings are reported), creating stale signals between reporting periods.
- Equal-weight allocation across the top 5% can result in a large number of positions, increasing transaction costs.
- Earnings restatements and accounting irregularities can produce misleading SUE scores.
- The 36-month warm-up period limits the strategy's ability to trade recently listed stocks.
- Long-only construction leaves the portfolio fully exposed to broad market declines.
- Transaction costs from monthly rebalancing are not explicitly modeled.

## Related Strategies

- [Fama-French Five Factors](fama-french-five-factors.md)
- [Expected Idiosyncratic Skewness](expected-idiosyncratic-skewness.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/standardized-unexpected-earnings)
