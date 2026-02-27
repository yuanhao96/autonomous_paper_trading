# Asset Class Momentum

## Overview

A rotational momentum system that compares 12-month performance across five major asset classes (US equities, international equities, bonds, real estate, commodities) and concentrates exposure in the top 3 performers. Unlike passive diversification, this strategy actively selects only top-momentum asset classes.

## Academic Reference

- **Paper**: "Asset Class Momentum (Rotational System)" — Quantpedia

## Strategy Logic

### Universe Selection

Five ETFs representing distinct asset classes:

| ETF | Asset Class |
|-----|-------------|
| SPY | US Equities |
| EFA | International Equities |
| BND | Bonds |
| VNQ | Real Estate (REITs) |
| GSG | Commodities |

### Signal Generation

MomentumPercent (MOMP) indicator with 12-month lookback (252 trading days). Rank all 5 ETFs by momentum.

### Entry / Exit Rules

- **Long**: Top 3 ETFs by 12-month momentum.
- **Exit**: Positions not in top 3 are liquidated at rebalance.

### Portfolio Construction

Equal-weight: 1/3 allocation to each of the 3 selected ETFs.

### Rebalancing Schedule

Monthly, first trading day of each month.

## Key Indicators / Metrics

- MomentumPercent (MOMP): 252-day lookback
- Warm-up period: 12 months + 1 day

## Backtest Performance

| Metric | Value |
|--------|-------|
| Start Date | May 1, 2007 |
| Initial Capital | $100,000 |

*(Detailed Sharpe/return metrics not disclosed.)*

## Data Requirements

- **Asset Classes**: Multi-asset ETFs (5 tickers)
- **Resolution**: Daily
- **Lookback Period**: 252 trading days (12 months)

## Implementation Notes

- Simple, compact implementation — only 5 securities.
- Warm-up period of 12 months + 1 day ensures indicator readiness.
- Monthly rebalance triggered by schedule.
- Python implementation on QuantConnect LEAN.

## Risk Considerations

- Only 3 positions — concentrated factor bet on momentum continuation.
- Rotational system may lag during regime changes or mean-reversion periods.
- No risk management beyond momentum filtering (no stop-losses, no drawdown limits).
- ETF selection represents broad asset classes — misses within-class opportunities.
- Performance depends heavily on the specific ETFs chosen to represent each class.

## Related Strategies

- [Asset Class Trend Following](asset-class-trend-following.md) — same universe, trend filter instead of rotation
- [Sector Momentum](sector-momentum.md)
- [Momentum and Style Rotation Effect](momentum-and-style-rotation-effect.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/asset-class-momentum)
