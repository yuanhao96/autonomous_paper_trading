# Expected Idiosyncratic Skewness

## Overview

Exploits the empirical finding that stocks with low expected idiosyncratic skewness earn higher average returns than stocks with high expected idiosyncratic skewness. Investors overpay for lottery-like payoffs (positive skewness), creating a return premium for stocks with less skewed return distributions. The strategy uses a two-stage regression approach to predict idiosyncratic skewness and goes long stocks with the lowest predicted values.

## Academic Reference

- **Paper**: "Expected Idiosyncratic Skewness" — Brian Boyer, Todd Mitton, Keith Vorkink, 2009
- **Link**: https://doi.org/10.1093/rfs/hhp041

## Strategy Logic

### Universe Selection

1. **Coarse filter**: Select US equities with sufficient price and volume, excluding ETFs.
2. **Data requirement**: Stocks must have enough history to run Fama-French regressions and compute residual skewness.

### Signal Generation

A two-stage procedure:

**Stage 1 — Estimate Realized Idiosyncratic Skewness**:
- Run Fama-French three-factor regressions for each stock over a trailing window:
  ```
  R_i - R_f = alpha + beta_MKT * MKT + beta_SMB * SMB + beta_HML * HML + epsilon
  ```
- Extract residuals (`epsilon`) and compute the skewness of the residual distribution for each stock.

**Stage 2 — Predict Expected Idiosyncratic Skewness**:
- Run a cross-sectional regression of realized idiosyncratic skewness on lagged firm characteristics (e.g., past skewness, volatility, momentum, size).
- Use the fitted values as the predicted (expected) idiosyncratic skewness for each stock.

### Entry / Exit Rules

- **Entry (Long)**: Go long the bottom 5% of stocks ranked by predicted idiosyncratic skewness (lowest expected skewness).
- **Exit**: Liquidate positions for stocks that move out of the bottom 5% at rebalance.

### Portfolio Construction

Value-weighted within the long portfolio. Stocks are weighted proportionally to their market capitalization.

### Rebalancing Schedule

Monthly. Fama-French regressions and cross-sectional predictions are updated at each rebalance.

## Key Indicators / Metrics

- **Idiosyncratic skewness**: Third moment of Fama-French residuals
- **Fama-French three factors**: MKT, SMB, HML (for residual extraction)
- **Predicted skewness**: Fitted values from cross-sectional regression
- **Fama-French alpha differential**: 1.00% per month between low- and high-skewness portfolios

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | Jul 2009 – Jul 2019 | SPY |
| Initial Capital | $100,000 | — |
| Sharpe Ratio | 0.947 | 0.87 |
| FF Alpha Differential | 1.00%/month | — |

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily
- **Lookback Period**: Sufficient history for Fama-French regressions (typically 60+ trading days per window)
- **Factor Data**: Fama-French three-factor returns (MKT, SMB, HML), available from Kenneth French's data library
- **Fundamental Data**: Market capitalization (for value-weighting)

## Implementation Notes

- Fama-French factor returns must be sourced externally or constructed from portfolio sorts.
- The two-stage regression procedure is computationally intensive for large universes; consider parallelization.
- Residual skewness estimation requires a sufficiently long window to be statistically meaningful.
- The cross-sectional prediction model should use lagged (not contemporaneous) variables to avoid look-ahead bias.
- Python implementation on QuantConnect LEAN engine.

## Risk Considerations

- Skewness estimates are noisy, particularly over short windows, leading to imprecise signal generation.
- The strategy is long-only and does not hedge market exposure; it will underperform in broad market declines.
- Value-weighting concentrates risk in large-cap stocks, potentially reducing the skewness premium.
- The Fama-French alpha differential may not persist out-of-sample or in different market regimes.
- Transaction costs from monthly rebalancing of a potentially large portfolio are not explicitly modeled.
- Factor data availability and timeliness can introduce implementation challenges.

## Related Strategies

- [Fama-French Five Factors](fama-french-five-factors.md)
- [Standardized Unexpected Earnings](standardized-unexpected-earnings.md)
- [Beta Factors in Stocks](beta-factors-in-stocks.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/expected-idiosyncratic-skewness)
