# Short Term Reversal with Futures

## Overview

Applies short-term reversal to 8 CME futures contracts (4 currency, 4 equity index). Combines volume and open interest signals to identify contracts likely to reverse, going long the worst weekly performer and short the best from a filtered subset.

## Academic Reference

- **Paper**: Quantpedia — "Short Term Reversal with Futures"
- **Source**: quantpedia.com/Screener/Details/71

## Strategy Logic

### Universe Selection

8 CME continuous futures contracts:
- **Currencies**: CHF, GBP, CAD, EUR
- **Equity Indexes**: NASDAQ-100 E-mini, Russell 2000 E-mini, S&P 500 E-mini, Dow 30 E-mini

Open interest-based continuous contract mapping.

### Signal Generation

Combine two weekly signals:

1. **Volume Reversal**: Identify contracts in the bottom 50% of weekly volume changes.
2. **Open Interest Reversal**: Identify contracts in the top 50% of weekly open interest changes.

Select contracts at the intersection of both groups.

### Entry / Exit Rules

- **Long**: Contract with the lowest weekly return from the filtered group.
- **Short**: Contract with the highest weekly return from the filtered group.
- **Exit**: Liquidate non-target positions at weekly rebalance; manage rollovers on contract changes.

### Portfolio Construction

30% portfolio allocation per position (long and short). Contract multiplier adjustment for order sizing.

### Rebalancing Schedule

Weekly (Wednesday-to-Wednesday intervals).

## Key Indicators / Metrics

- Rate of Change (ROC): period 1, tracking volume, open interest, and price changes
- TradeBarConsolidator: weekly price consolidation
- OpenInterestConsolidator: weekly open interest consolidation
- Warm-up: 14 days

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2019 – 2020 |
| Resolution | Daily (extended market hours) |

## Data Requirements

- **Asset Classes**: CME futures (4 currency + 4 equity index)
- **Resolution**: Daily with extended market hours
- **Data**: OHLCV bars and open interest values
- **Warm-up**: 14 days

## Implementation Notes

- Custom `SymbolData` class manages weekly consolidators for volume, open interest, and prices.
- State flags indicate indicator readiness.
- Automated contract rollover handling via symbol-changed events.
- Python on QuantConnect LEAN.

## Risk Considerations

- No explicit stop-loss or volatility controls.
- Small universe (8 contracts) limits diversification — single contract events dominate.
- Volume and open interest signals may be noisy on a weekly basis.
- Futures leverage amplifies both gains and losses.
- Weekly rebalancing generates rollover costs.
- Currency and equity index futures have very different volatility profiles — treating them equally may be suboptimal.

## Related Strategies

- [Short Term Reversal](short-term-reversal.md)
- [Short-Term Reversal Strategy in Stocks](short-term-reversal-strategy-in-stocks.md)
- [Momentum Effect in Commodities Futures](../momentum/momentum-effect-in-commodities-futures.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/short-term-reversal-with-futures)
