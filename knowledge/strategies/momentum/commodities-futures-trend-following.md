# Commodities Futures Trend Following

## Overview

A monthly-rebalanced trend following strategy on commodity futures based on the 2014 paper "Two Centuries of Trend Following." Buys when prices go up and sells when prices go down, using an exponential moving average crossover with volatility-adjusted position sizing.

## Academic Reference

- **Paper**: "Two Centuries of Trend Following" — Lempérière et al. (2014)
- **Key Finding**: Demonstrated "statistically significant systematic excess returns" across commodities, currencies, stock indices, and bonds over two centuries.

## Strategy Logic

### Universe Selection

Seven commodity futures:
- Wheat, corn, live cattle, crude oil WTI, natural gas, sugar 11, copper

Daily resolution, continuous futures with backward-ratio normalization and open-interest mapping.

### Signal Generation

Trend signal formula:

```
s_n(t) = (p(t-1) - EMA_n(t-1)) / σ_n(t-1)
```

Where:
- `p(t-1)` = previous month's close
- `EMA_n(t-1)` = exponential moving average with 5-month decay
- `σ_n(t-1)` = volatility as EMA of absolute monthly price changes (5-month decay)

### Entry / Exit Rules

Position quantity:
```
Quantity = sign(signal) × momentum / |volatility|
```

Leverage: 3x applied to position sizing.

### Portfolio Construction

`SymbolData` class tracks per security: EMA (5-period), Momentum (1-period absolute changes), Volatility (EMA of momentum, 5-period), contract multiplier. Position quantity divided by contract multiplier.

### Rebalancing Schedule

Monthly, at month-end.

## Key Indicators / Metrics

- Exponential Moving Average (5-month decay)
- Momentum (1-period absolute changes)
- Volatility (EMA of absolute changes, 5-period)

## Backtest Performance

| Metric | Strategy | SPY |
|--------|----------|-----|
| Period | Jan 2010 – Jan 2020 | Same |
| Sharpe Ratio | **-0.131** | 0.805 |
| Information Ratio | -0.767 | — |
| Alpha | 0.003 | — |

**Key finding**: Strategy underperformed significantly in 2010–2020 despite historical success. Authors note "trend information no longer provides extra information for alpha profit generation" due to technological advancement and market efficiency since the 1960s–70s.

## Data Requirements

- **Asset Classes**: Commodity futures (7 contracts)
- **Resolution**: Daily OHLC
- **Lookback Period**: 150 days warm-up
- **Data**: Monthly consolidation capability

## Implementation Notes

- Monthly consolidators per security update indicators.
- 150-day warm-up to initialize indicators before trading.
- `SymbolData` stores contract multiplier and mapped contract pointer.
- Python implementation on QuantConnect LEAN.

## Risk Considerations

- Significant underperformance in modern markets (Sharpe -0.131 vs. SPY 0.805).
- Simple trend signals absorbed "in milliseconds by the more efficient market."
- 3x leverage amplifies losses during trend failures.
- Only 7 commodity contracts — limited diversification.
- No drawdown controls or stop-losses.
- Monthly rebalancing may be too slow for modern trend-following.

## Related Strategies

- [Asset Class Trend Following](asset-class-trend-following.md)
- [Time Series Momentum Effect](time-series-momentum-effect.md)
- [Momentum Effect in Commodities Futures](momentum-effect-in-commodities-futures.md)
- [Improved Momentum Strategy on Commodities Futures](improved-momentum-strategy-on-commodities-futures.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/commodities-futures-trend-following)
