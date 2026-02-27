# Fama-French Five Factors

## Overview

Implements the Fama-French five-factor model, which explains stock returns through five systematic risk factors: market risk (MKT), size (SMB), value (HML), profitability (RMW), and investment (CMA). The strategy ranks a broad universe of stocks by fundamental metrics corresponding to each factor and constructs a long-short portfolio based on composite factor scores.

## Academic Reference

- **Paper**: "A Five-Factor Asset Pricing Model" — Eugene F. Fama & Kenneth R. French, 2015
- **Link**: https://doi.org/10.1016/j.jfineco.2014.10.010

## Strategy Logic

### Universe Selection

1. **Coarse filter**: Select top 200 US equities by dollar volume, excluding stocks trading below $5 and ETFs.
2. **Fine filter**: Retain stocks with available fundamental data for all five factor metrics.

### Signal Generation

Each stock is ranked across five fundamental metrics corresponding to the five factors:

| Factor | Metric | Interpretation |
|--------|--------|----------------|
| MKT | Market beta | Systematic market risk exposure |
| SMB | Book value | Small firms tend to outperform large firms |
| HML | Total equity | High book-to-market firms outperform low |
| RMW | Operating profit margin | Robust profitability outperforms weak |
| CMA | Total assets growth | Conservative investment outperforms aggressive |

A composite score is computed by averaging the percentile ranks across all five metrics.

### Entry / Exit Rules

- **Entry (Long)**: Go long the top 5 stocks by composite factor score.
- **Entry (Short)**: Go short the bottom 5 stocks by composite factor score.
- **Exit**: Liquidate positions for stocks that fall out of the top/bottom 5 at rebalance.

### Portfolio Construction

Equal-weight allocation across 10 positions (5 long, 5 short). Each position receives approximately 10% of portfolio capital.

### Rebalancing Schedule

Monthly. The portfolio is reconstituted at the beginning of each calendar month based on updated fundamental rankings.

## Key Indicators / Metrics

- **Book Value**: Proxy for size factor (SMB)
- **Total Equity**: Proxy for value factor (HML)
- **Operating Profit Margin**: Proxy for profitability factor (RMW)
- **Return on Equity (ROE)**: Supporting profitability measure
- **Total Assets Growth**: Proxy for investment factor (CMA)

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | Jan 2010 – Aug 2019 | SPY |
| Initial Capital | $100,000 | — |
| Annual Return | ~6.8% | — |
| Max Drawdown | 19.8% | — |

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily
- **Lookback Period**: Point-in-time fundamental data (quarterly)
- **Fundamental Data**: Morningstar (book value, total equity, operating profit margin, ROE, total assets growth)

## Implementation Notes

- Universe selection uses QuantConnect's coarse/fine fundamental selection pipeline with a 200-stock universe.
- Factor scores are computed at each rebalance by ranking all universe constituents on each metric and averaging percentile ranks.
- Warm-up period should cover at least one quarter of fundamental data to ensure all metrics are populated.
- Python implementation on QuantConnect LEAN engine.

## Risk Considerations

- Fundamental data is reported with a lag; point-in-time data is essential to avoid look-ahead bias.
- Concentrated portfolio (10 positions) introduces significant idiosyncratic risk.
- Factor premia can experience prolonged drawdowns (e.g., the value factor underperformed for much of the 2010s).
- Short positions carry unlimited loss potential and borrowing costs.
- Transaction costs from monthly rebalancing and short-selling fees are not explicitly modeled.

## Related Strategies

- [Beta Factors in Stocks](beta-factors-in-stocks.md)
- [Expected Idiosyncratic Skewness](expected-idiosyncratic-skewness.md)
- [Standardized Unexpected Earnings](standardized-unexpected-earnings.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/fama-french-five-factors)
