# Time Series Momentum Effect

## Overview

Unlike cross-sectional momentum (which compares relative performance across securities), time series momentum focuses purely on the past returns of each individual futures contract. If a contract's excess return over the past 12 months is positive, go long; if negative, go short.

## Academic Reference

- **Paper**: "Time Series Momentum" — Moskowitz, Ooi, Pedersen (2012)
- **Concept**: Time series momentum is related to but distinct from cross-sectional momentum. It exploits individual asset trend persistence rather than relative outperformance.

## Strategy Logic

### Universe Selection

Highly liquid commodity futures traded on CME, ICE, and CBOT. Strategy uses a 12-month RateOfChange indicator to measure momentum.

### Signal Generation

Monthly evaluation of each contract:
- **Positive 12-month excess return** → Go long
- **Negative 12-month excess return** → Go short

### Entry / Exit Rules

- **Long**: When 12-month return is positive.
- **Short**: When 12-month return is negative.
- **Position sizing**: Inversely proportional to the volatility of the security's returns. Historical volatility used (GARCH possible but not implemented).

### Portfolio Construction

All contracts traded simultaneously — each independently long or short based on its own trend signal. Position size scaled by inverse volatility.

### Rebalancing Schedule

Monthly.

## Key Indicators / Metrics

- RateOfChange (252-day / 12-month lookback)
- Historical volatility for position sizing

## Backtest Performance

*(Specific backtest metrics not disclosed in available sources.)*

## Data Requirements

- **Asset Classes**: Commodity futures (multi-exchange)
- **Resolution**: Daily
- **Lookback Period**: 12 months (252 trading days)
- **Additional**: Volatility calculation window

## Implementation Notes

- Uses LEAN's `RateOfChange(period)` indicator per contract.
- Monthly consolidator triggers rebalancing.
- Position quantity = signal direction × (target risk / asset volatility).
- Continuous futures with backward-ratio normalization.

## Risk Considerations

- High portfolio turnover after transaction costs can diminish returns.
- Post-2008 GFC period shows underperformance due to increased asset co-movement.
- Simple trend signals may be arbitraged away by high-frequency participants.
- No cross-sectional diversification benefit — each contract traded independently.
- Inverse volatility sizing can lead to large positions in low-vol contracts during quiet periods.

## Related Strategies

- [Improved Momentum Strategy on Commodities Futures](improved-momentum-strategy-on-commodities-futures.md) — addresses TSMOM weaknesses
- [Commodities Futures Trend Following](commodities-futures-trend-following.md)
- [Momentum Effect in Commodities Futures](momentum-effect-in-commodities-futures.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/time-series-momentum-effect)
