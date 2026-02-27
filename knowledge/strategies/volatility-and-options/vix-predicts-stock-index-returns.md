# VIX Predicts Stock Index Returns

## Overview

Uses extreme VIX percentile readings to predict S&P 100 (OEF) returns. When VIX is in the top 10th percentile of its 2-year range, goes long equities (mean reversion from fear). When VIX is in the bottom 10th percentile, goes short (mean reversion from complacency). Full allocation binary positioning.

## Academic Reference

- **Paper**: Quantpedia Premium — "VIX Predicts Stock Index Returns"

## Strategy Logic

### Universe Selection

Single asset: OEF (iShares S&P 100 ETF). Signal source: CBOE VIX Index.

### Signal Generation

Create 20 equally-spaced percentile bins from 504 days (2 years) of historical VIX closes. Compare current VIX reading to these percentiles.

### Entry / Exit Rules

- **Long**: VIX above 90th percentile (highest 2 bins) — extreme fear signals equity buying opportunity.
- **Short**: VIX below 10th percentile (lowest 2 bins) — extreme complacency signals equity sell.
- **Exit**: Rebalance weekly or when signal direction changes.

### Portfolio Construction

100% long OEF or 100% short OEF. Binary positioning.

### Rebalancing Schedule

Weekly, or when signal changes direction.

## Key Indicators / Metrics

- VIX rolling 2-year (504-day) percentile distribution
- 90th percentile threshold (long trigger)
- 10th percentile threshold (short trigger)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Mar 2023 – Mar 2024 |
| Initial Capital | $1,000,000 |
| Warm-up | 504 days |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: US equity ETF (OEF) + VIX Index
- **Resolution**: Daily
- **External Data**: CBOE VIX daily closes
- **Lookback**: 504 days (2 years)

## Implementation Notes

- Modular architecture: AlphaModel generates directional insights.
- EqualWeightingPortfolioConstructionModel for position sizing.
- VIX data via CBOE custom dataset.
- 504-day warm-up period required.
- Python on QuantConnect LEAN.

## Risk Considerations

- Mean reversion assumption — VIX extremes may persist during crisis or prolonged bull markets.
- Full leverage exposure during extreme regimes amplifies risk.
- Single-security concentration (OEF) — no diversification.
- No stop-loss or maximum drawdown limits.
- VIX percentile bins are backward-looking — regime changes alter the distribution.
- Short OEF position during complacency carries unlimited loss potential.

## Related Strategies

- [Exploiting Term Structure of VIX Futures](exploiting-term-structure-of-vix-futures.md)
- [Volatility Effect in Stocks](volatility-effect-in-stocks.md)
- [Sentiment and Style Rotation Effect in Stocks](../momentum/sentiment-and-style-rotation-effect-in-stocks.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/vix-predicts-stock-index-returns)
