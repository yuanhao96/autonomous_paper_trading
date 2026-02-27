# Momentum Effect Combined with Term Structure in Commodities

## Overview

Merges two quantitative signals — term structure (roll returns from contango/backwardation) and momentum (historical price performance) — to identify long and short positions in commodity futures. Buys high-roll-return winners and shorts low-roll-return losers.

## Academic Reference

- **Paper**: "Momentum Effect Combined with Term Structure in Commodities" — Quantpedia Premium

## Strategy Logic

### Universe Selection

22 commodity futures across multiple sectors:
- **Softs**: Cocoa, coffee, cotton, orange juice, sugar
- **Grains**: Corn, oats, soybean meal, soybean oil, soybeans, wheat
- **Meats**: Feeder cattle, lean hogs, live cattle
- **Energies**: Crude oil WTI, heating oil, natural gas, gasoline
- **Metals**: Gold, palladium, platinum, silver

### Signal Generation

**Step 1 — Roll Return** (term structure signal):
```
Roll Return = (Price_nearest - Price_forward) × 365 / Days_to_expiry
```
Sort into three tertiles; eliminate middle tertile.

**Step 2 — Mean Return** (momentum filter):
21-day historical returns using minute-resolution data. Applied within high/low roll-return portfolios.

### Entry / Exit Rules

1. **High Portfolio**: Contracts with highest roll returns → top 50% by momentum = "High-Winners" (long).
2. **Low Portfolio**: Contracts with lowest roll returns → bottom 50% by momentum = "Low-Losers" (short).
3. **Exit**: All positions liquidated before monthly rebalancing.

### Portfolio Construction

- Long allocation: 0.25 × total equity / number of High-Winners
- Short allocation: 0.25 × total equity / number of Low-Losers

### Rebalancing Schedule

Monthly, at start of each month via scheduled events.

## Key Indicators / Metrics

- Roll return (term structure: contango vs. backwardation)
- 21-day mean return (momentum filter)
- Tertile ranking (roll return)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2016–2017 |
| Initial Capital | $10,000,000 |

*(Detailed Sharpe/return metrics not disclosed.)*

## Data Requirements

- **Asset Classes**: Commodity futures (22 contracts)
- **Resolution**: Minute (for return calculations), daily (for roll returns)
- **Lookback Period**: 21 days (momentum), contract expiry dates (term structure)
- **Data**: FuturesChain for contract navigation, 90-day availability filter

## Implementation Notes

- Uses FuturesChain navigation for contract selection.
- Filters on 90-day contract availability.
- Handles missing price data via bid-ask midpoints.
- Liquidates all positions before monthly rebalancing.
- Python implementation on QuantConnect LEAN.

## Risk Considerations

- Very short backtest period (2016–2017, only 2 years).
- Large initial capital ($10M) may not reflect retail constraints.
- Roll return signal depends on term structure persistence — can shift rapidly.
- Middle tertile eliminated — may miss opportunities in moderately positioned contracts.
- Full liquidation before rebalance adds transaction costs.

## Related Strategies

- [Momentum Effect in Commodities Futures](momentum-effect-in-commodities-futures.md)
- [Term Structure Effect in Commodities](../commodities/term-structure-effect-in-commodities.md)
- [Improved Momentum Strategy on Commodities Futures](improved-momentum-strategy-on-commodities-futures.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/momentum-effect-combined-with-term-structure-in-commodities)
