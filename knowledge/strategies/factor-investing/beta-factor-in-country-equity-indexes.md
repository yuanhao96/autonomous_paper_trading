# Beta Factor in Country Equity Indexes

## Overview

Applies the low-beta anomaly at the country level, using a universe of 35 country equity ETFs. Countries with low market beta tend to deliver higher risk-adjusted returns than high-beta countries, mirroring the well-documented effect in individual stocks. The strategy goes long low-beta country ETFs and short high-beta country ETFs.

## Academic Reference

- **Paper**: Quantpedia — "Beta Factor in Country Equity Indexes"
- **Link**: https://quantpedia.com/

## Strategy Logic

### Universe Selection

A fixed universe of 35 country equity index ETFs representing developed and emerging markets. All ETFs must have sufficient trading history to calculate rolling beta.

### Signal Generation

Beta is calculated for each country ETF relative to the US market (SPY) over a 253-day (1-year) rolling window:

```
Beta = Cov(R_country_ETF, R_SPY) / Var(R_SPY)
```

Where:
- `R_country_ETF` = daily returns of the country equity ETF
- `R_SPY` = daily returns of SPY (S&P 500 ETF)

### Entry / Exit Rules

- **Entry (Long)**: Go long the bottom 25% of country ETFs by beta (approximately 9 ETFs).
- **Entry (Short)**: Go short the top 25% of country ETFs by beta (approximately 9 ETFs).
- **Exit**: Liquidate positions for ETFs that move out of the top/bottom quartile at rebalance.

### Portfolio Construction

Equal-weight allocation within each leg:
- Long portfolio: equal-weight across bottom-quartile beta ETFs.
- Short portfolio: equal-weight across top-quartile beta ETFs.

### Rebalancing Schedule

Monthly. Beta rankings are recalculated and the portfolio is reconstituted at the beginning of each calendar month.

## Key Indicators / Metrics

- **Beta**: 253-day rolling covariance of country ETF returns with SPY returns, divided by SPY variance
- **Market proxy**: SPY (S&P 500 ETF)
- **Quartile breakpoints**: 25th and 75th percentile of cross-sectional beta distribution

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | Jan 2012 – Mar 2018 | SPY |
| Initial Capital | $100,000 | — |

*(Detailed Sharpe/return metrics not disclosed in source.)*

## Data Requirements

- **Asset Classes**: Country equity index ETFs (35 countries)
- **Resolution**: Daily
- **Lookback Period**: 253 trading days (1 year) for beta calculation
- **Market Proxy**: SPY

## Implementation Notes

- The 35 country ETFs must be manually specified as a fixed universe (e.g., EWA, EWC, EWG, EWH, EWJ, EWZ, FXI, etc.).
- A 253-day warm-up period is required before the first signal can be generated.
- Beta calculations use daily close-to-close returns.
- Quartile cutoffs are computed cross-sectionally at each rebalance date.
- Python implementation on QuantConnect LEAN engine.

## Risk Considerations

- Country ETFs carry currency risk in addition to equity market risk.
- Emerging market ETFs may have lower liquidity and higher bid-ask spreads.
- The low-beta anomaly at the country level may be weaker or less persistent than at the stock level.
- Using SPY as the market proxy introduces a US-centric bias; a global market index may be more appropriate.
- Concentrated short positions in high-beta (often emerging market) ETFs can experience sharp rallies.
- Transaction costs and ETF expense ratios are not explicitly modeled.

## Related Strategies

- [Beta Factors in Stocks](beta-factors-in-stocks.md)
- [Fama-French Five Factors](fama-french-five-factors.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/beta-factor-in-country-equity-indexes)
