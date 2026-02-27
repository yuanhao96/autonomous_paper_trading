# January Effect in Stocks

## Overview

Exploits the January Effect anomaly where small-cap stocks exhibit especially strong returns in January. Holds the 10 smallest stocks by market cap during January, then rotates to the 10 largest stocks for the remaining 11 months. Monthly rebalancing with equal-weight allocation.

## Academic Reference

- **Paper**: Quantpedia — "January Effect in Stocks"
- Based on the calendar anomaly that "small-cap stocks returns in January are especially strong."

## Strategy Logic

### Universe Selection

1. Top 1,000 US stocks by dollar volume.
2. Price filter: > $10.
3. Require valid earnings data and positive P/E ratios.

### Signal Generation

Calendar-based signal: switch universe based on current month.

### Entry / Exit Rules

- **January**: Long bottom 10 stocks by market capitalization (small-cap group).
- **February–December**: Long top 10 stocks by market capitalization (large-cap group).
- **Exit**: Full liquidation and reconstitution at monthly rebalance.

### Portfolio Construction

Equal-weight: 10% per position. Long-only.

### Rebalancing Schedule

Monthly, at month start.

## Key Indicators / Metrics

- Market capitalization (primary ranking metric)
- Calendar month (January vs. other months)
- Dollar volume (liquidity filter)
- P/E ratio (data quality filter)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Mar 2023 – Mar 2024 |
| Initial Capital | $1,000,000 |
| Warm-up | 31 days |

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily
- **Fundamental Data**: Market capitalization, EPS, shares outstanding, P/E ratio
- **Warm-up**: 31 days

## Implementation Notes

- Three-module architecture: Universe Selection Model, Alpha Model, Main Algorithm.
- Coarse filter: dollar volume + price > $10.
- Fine filter: valid earnings + positive P/E.
- Monthly long-bias insights with equal-weight portfolio construction.
- Liquidates positions unsupported by active insights.
- Python on QuantConnect LEAN.

## Risk Considerations

- January Effect is one of the most studied anomalies — may be largely arbitraged away.
- 10-stock portfolios are highly concentrated — single-stock events dominate.
- Small-cap stocks in January have wider spreads and lower liquidity.
- Monthly rebalancing incurs transaction costs, especially in small-caps.
- Strategy assumes anomaly persistence — evidence is mixed in recent decades.
- No risk management, stop-loss, or hedging mechanisms.
- Large-cap holdings in non-January months may underperform broader market.

## Related Strategies

- [January Barometer](january-barometer.md)
- [12 Month Cycle in Cross-Section of Stocks Returns](12-month-cycle-cross-section.md)
- [Small Capitalization Stocks Premium Anomaly](../value-and-fundamental/small-capitalization-stocks-premium-anomaly.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/january-effect-in-stocks)
