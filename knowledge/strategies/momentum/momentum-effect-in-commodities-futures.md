# Momentum Effect in Commodities Futures

## Overview

Exploits the momentum effect in commodity futures by ranking contracts based on 12-month returns and establishing long positions in top performers while shorting laggards. Commodity futures are excellent portfolio diversifiers and serve as inflation hedges.

## Academic Reference

- **Paper**: "Momentum Effect in Commodities" — Quantpedia
- **Link**: https://quantpedia.com/strategies/momentum-effect-in-commodities/

## Strategy Logic

### Universe Selection

10 CME commodity futures across dairy, meats, and forestry:
- **Dairy**: Cash-settled butter, cheese, Class III/IV milk, dry whey, nonfat dry milk
- **Meats**: Live cattle, feeder cattle, lean hogs
- **Forestry**: Random length lumber

Contract mapping: Largest open interest, backward-ratio adjustment. Data source: Quandl continuous futures.

### Signal Generation

Rate of Change (ROC) indicator with 252-day (12-month) lookback:
```
ROC = (Price_t - Price_{t-252}) / Price_{t-252}
```

### Entry / Exit Rules

- **Long**: Top 25% (quintile) of contracts by 12-month ROC.
- **Short**: Bottom 25% (quintile) of contracts by 12-month ROC.
- **Exit**: Automatically liquidates positions no longer in trading quintiles at rebalance.

### Portfolio Construction

Equal-weighted within each quintile:
```
Allocation per contract = 0.5 / number_of_futures_in_quintile
```

Leverage: 1x.

### Rebalancing Schedule

Monthly, triggered at month-end.

## Key Indicators / Metrics

- Rate of Change (ROC): 252-day lookback
- Open interest (contract mapping)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2015–2018 |
| Initial Capital | $100,000 |

*(Detailed Sharpe/return metrics not disclosed.)*

## Data Requirements

- **Asset Classes**: Commodity futures (CME)
- **Resolution**: Daily (updated version uses minute for fill quality)
- **Lookback Period**: 252 days (12 months)
- **Data Source**: Quandl continuous futures

## Implementation Notes

- `WarmUpIndicator()` method used before trading.
- `SymbolData` class stores symbol metadata (mapped contract, multiplier).
- Updated version uses minute resolution to avoid stale fills, PEP8 styling, quantity validation, security initializer.

## Risk Considerations

- No explicit drawdown limits or volatility adjustments.
- Momentum-only signal — no mean reversion filters.
- Fixed monthly rebalancing regardless of market conditions.
- Concentrated in specific commodity sectors (dairy, meats, forestry).
- Liquidity risk in some dairy futures contracts.

## Related Strategies

- [Improved Momentum Strategy on Commodities Futures](improved-momentum-strategy-on-commodities-futures.md)
- [Momentum Effect Combined with Term Structure in Commodities](momentum-effect-combined-with-term-structure-in-commodities.md)
- [Commodities Futures Trend Following](commodities-futures-trend-following.md)
- [Time Series Momentum Effect](time-series-momentum-effect.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/momentum-effect-in-commodities-futures)
