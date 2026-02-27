# Small Capitalization Stocks Premium Anomaly

## Overview

Exploits the small-cap premium by going long the 10 smallest stocks by market capitalization from a universe of companies under $2 billion. Equal-weighted with annual rebalancing. Targets "young companies with significant growth potential."

## Academic Reference

- **Paper**: Quantpedia — "Small Capitalization Stocks Premium Anomaly"
- **Foundation**: Fama & French size factor (SMB) literature

## Strategy Logic

### Universe Selection

1. All US equities with fundamental data (MorningStar).
2. Market capitalization < $2 billion.
3. Price filter: > $5.

### Signal Generation

Rank all qualifying stocks by market capitalization ascending. Select the 10 smallest.

### Entry / Exit Rules

- **Long**: Equal-weight the 10 smallest-cap stocks.
- **Exit**: Liquidate positions removed from selection at annual rebalance.
- No short positions.

### Portfolio Construction

Equal-weight: 10% allocation per stock. `PortfolioTarget` objects used for systematic rebalancing.

### Rebalancing Schedule

Annual, at the beginning of each calendar year.

## Key Indicators / Metrics

- Market capitalization (primary selection criterion)
- Price filter (> $5)
- Fundamental data availability (MorningStar)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2016 – Jul 2019 |
| Initial Capital | $100,000 |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: US equities (small-cap, < $2B market cap)
- **Resolution**: Daily
- **Fundamental Data**: Market capitalization
- **Data Source**: MorningStar US fundamental data

## Implementation Notes

- Coarse selection filters by `has_fundamental_data` and price > $5.
- Fine selection filters by market cap < $2B, sorts ascending, takes bottom 10.
- `PortfolioTarget` objects for position sizing.
- Liquidation and rebalancing logic designed to avoid margin calls.
- PEP8 compliant. Python on QuantConnect LEAN.

## Risk Considerations

- "The risk of failure is greater with small-cap stocks than with large-cap and mid-cap stocks."
- 10-stock portfolio is extremely concentrated — single-stock events dominate returns.
- Small-cap stocks have wider bid-ask spreads and lower liquidity — execution slippage is significant.
- Annual rebalancing is very slow — small-cap stocks can move dramatically within a year.
- Survivorship bias is particularly acute for small-cap stocks (many delist or go bankrupt).
- No risk management, stop-loss, or sector diversification controls.
- Small-cap premium may have diminished as it became widely known and traded.

## Related Strategies

- [Price Earnings Anomaly](price-earnings-anomaly.md)
- [Fama-French Five Factors](../factor-investing/fama-french-five-factors.md)
- [Liquidity Effect in Stocks](../factor-investing/liquidity-effect-in-stocks.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/small-capitalization-stocks-premium-anomaly)
