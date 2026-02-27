# Term Structure Effect in Commodities

## Overview

Long/short commodity futures strategy based on the futures term structure. Goes long contracts in backwardation (positive roll return) and shorts contracts in contango (negative roll return). Selects top and bottom quintiles from 22 commodities across softs, grains, meats, energies, and metals. Monthly rebalancing.

## Academic Reference

- **Paper**: "Tactical Allocation in Commodity Futures Markets: Combining Momentum and Term Structure Signals" — Fuertes, Miffre & Rallis (2010), Journal of Banking and Finance, 34:2530–2548
- **Source**: Quantpedia Strategy #22

## Strategy Logic

### Universe Selection

22 commodity futures: Cocoa, Coffee, Cotton, Orange Juice, Sugar (softs); Corn, Oats, Soybean Meal, Soybean Oil, Soybeans, Wheat (grains); Feeder Cattle, Lean Hogs, Live Cattle (meats); Crude Oil WTI, Heating Oil, Natural Gas, Gasoline (energies); Gold, Palladium, Platinum, Silver (metals).

### Signal Generation

**Annualized roll return**: R = (log(P_near) − log(P_distant)) × 365 / (T_distant − T_near)

Where P_near = nearest contract price, P_distant = distant contract price, T = days to expiration.

- **Positive roll** → backwardation → long opportunity.
- **Negative roll** → contango → short opportunity.

### Entry / Exit Rules

- **Long**: Top 20% (quintile) by roll return (most backwardated).
- **Short**: Bottom 20% by roll return (most contangoed).
- **Exit**: Full liquidation before new monthly positions.

### Portfolio Construction

Equal-weight: 10% per contract (0.1/count). ~100% gross exposure (0.5 long + 0.5 short). 30% margin buffer.

### Rebalancing Schedule

Monthly, first business day, 30 minutes after market open.

## Key Indicators / Metrics

- Annualized roll return (futures term structure signal)
- 90-day futures chain filtering
- Front and near-term contract selection

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2016 – 2018 |
| Initial Capital | $1,000,000 |
| Academic Period | 1997 – 2007 (documented profitability) |
| Recent Finding | Strategy has weakened substantially post-2010 |

Note: "No money-minting magic happened with this strategy" in modern periods. "Massive jumps and volatility's mood swings" degrade performance.

## Data Requirements

- **Asset Classes**: 22 commodity futures
- **Resolution**: Daily
- **Data**: Futures contract prices (bid/ask when last unavailable), expiration dates
- **Lookback**: 90-day rolling window

## Implementation Notes

- Front-month contract selection within 90-day futures chain.
- Bid/ask prices used as fallback when last price unavailable.
- 30% portfolio margin buffer to avoid insufficient buying power.
- Full liquidation before establishing new positions.
- Python on QuantConnect LEAN.

## Risk Considerations

- Academic anomaly (documented 2010) has substantially eroded — market efficiency improvements.
- Commodity futures have "massive jumps and volatility mood swings" complicating execution.
- Roll return signal may be less predictive in modern commodity markets.
- Contract rollovers incur costs not fully captured in backtests.
- Liquidity varies significantly across 22 commodities — small contracts may have wide spreads.
- Margin requirements for 22 simultaneous futures positions are substantial.
- Regime dependency: strategy performance degrades when backwardation/contango becomes less predictive.

## Related Strategies

- [Trading with WTI BRENT Spread](trading-with-wti-brent-spread.md)
- [Momentum Effect Combined with Term Structure in Commodities](../momentum/momentum-effect-combined-with-term-structure-in-commodities.md)
- [Improved Momentum Strategy on Commodities Futures](../momentum/improved-momentum-strategy-on-commodities-futures.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/term-structure-effect-in-commodities)
