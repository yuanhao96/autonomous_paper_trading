# Time-Series Momentum

## Overview

Exploits the tendency of assets to continue performing in the same direction as their recent past. Unlike cross-sectional momentum (ranking assets against each other), time-series momentum compares each asset's return to zero — going long when the asset's own trailing return is positive.

## Academic Reference

- **Paper**: "Time Series Momentum", Moskowitz, Ooi, Pedersen (2012)
- **Link**: https://pages.stern.nyu.edu/~lpederse/papers/TimeSeriesMomentum.pdf

## Strategy Logic

### Universe Selection

Broad asset classes: equity indices, bonds, currencies, and commodities futures.

### Signal Generation

Compute the trailing return over a lookback period (typically 12 months):

```
Signal = Close_t / Close_{t-lookback} - 1
```

If the signal is positive, go long; if negative, stay flat (or go short in a long-short variant).

### Entry / Exit Rules

- **Entry**: Go long when trailing return > threshold (typically 0).
- **Exit**: Close position when trailing return turns negative.

### Portfolio Construction

Equal-weight or volatility-scaled allocation across assets with positive signals.

### Rebalancing Schedule

Monthly.

## Key Indicators / Metrics

- **Trailing return**: Configurable lookback (60–252 days)
- **Threshold**: Minimum return to trigger entry (default 0)

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | 1985–2009 | Buy-and-hold |
| Annual Return | ~18% | ~10% |
| Sharpe Ratio | ~1.0 | ~0.4 |
| Max Drawdown | ~20% | ~55% |

## Data Requirements

- **Asset Classes**: Equities, futures, forex, commodities
- **Resolution**: Daily
- **Lookback Period**: 60–252 trading days

## Implementation Notes

- Pure price-based signal — no fundamental data required.
- Works across asset classes with consistent parameter settings.
- Implementation uses `MomentumPercent` or simple return calculation.

## Risk Considerations

- Momentum crashes during sharp market reversals.
- Lookback period sensitivity — shorter lookbacks are more responsive but noisier.
- Transaction costs from monthly rebalancing.
- Regime-dependent: underperforms in choppy/sideways markets.

## Related Strategies

- [Time-Series Momentum Effect](time-series-momentum-effect.md)
- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)
- [Dual Momentum](dual-momentum.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/time-series-momentum)
