# The Dynamic Breakout II Strategy

## Overview

Adaptive breakout strategy for forex that dynamically adjusts its lookback period based on market volatility. Uses Bollinger Bands with a variable-length window (20–60 days) — shorter in high volatility, longer in low volatility. Enters on Bollinger Band breakouts confirmed by new highs/lows, exits on MA crossover.

## Academic Reference

- **Paper**: "Building Winning Trading Systems" — George Pruitt, John R. Hill & Michael Russak (2012)
- Original Dynamic Breakout system developed by George Pruitt for Futures Magazine (1996).

## Strategy Logic

### Universe Selection

Forex pairs: EURUSD, GBPUSD tested. Also applicable to futures and equities.

### Signal Generation

**Step 1 — Adaptive lookback**:
- Calculate 30-day standard deviation of closing prices.
- Adjust lookback daily based on volatility change rate (deltavol).
- Constrained to 20–60 day range.

**Step 2 — Bollinger Bands**:
- Upper Band = μ + 2σ (exponential MA).
- Lower Band = μ − 2σ.
- Length matches adaptive lookback period.

### Entry / Exit Rules

- **Long**: Previous close > upper Bollinger Band AND current price > highest high over N-day lookback.
- **Short**: Previous close < lower Bollinger Band AND current price < lowest low over N-day lookback.
- **Exit long**: Price falls below MA of closes over lookback period.
- **Exit short**: Price rises above MA of closes over lookback period.

### Portfolio Construction

Single-asset: fully long (+1.0) or fully short (−1.0). No partial positioning.

### Rebalancing Schedule

Daily signal evaluation.

## Key Indicators / Metrics

- Bollinger Bands (adaptive length, 2σ)
- 30-day volatility (standard deviation)
- Adaptive lookback: 20–60 days
- Highest high / lowest low (N-day)

## Backtest Performance

| Metric | EURUSD | GBPUSD |
|--------|--------|--------|
| Period | 2010–2016 | 2010–2016 |
| Annual Return | 2.3% | Negative |
| Sharpe Ratio | 0.31 | — |
| Max Drawdown | ~14% | ~19% |

Note: Profitable in trending markets (2010–2014), poor in choppy/sideways conditions.

## Data Requirements

- **Asset Classes**: Forex (or futures/equities)
- **Resolution**: Daily
- **Lookback**: 31+ days (30-day volatility calculation)

## Implementation Notes

- Custom Bollinger Bands indicator with adaptive length.
- NumPy for volatility calculations.
- Schedule-based daily signal updates.
- Python on QuantConnect LEAN.

## Risk Considerations

- "Strategy works best in a trending forex market" — underperforms in range-bound conditions.
- ~19% max drawdown on GBPUSD — significant for a single-asset strategy.
- Adaptive lookback may become too tight (short) or too loose (long) depending on regime.
- Single-asset, binary positioning amplifies drawdowns.
- No stop-loss beyond MA exit — can ride significant losses before MA crossover triggers.
- Authors suggest alternative volatility metrics (log returns, stochastic models) for improvement.

## Related Strategies

- [Forex Momentum](../momentum/forex-momentum.md)
- [Combining Mean Reversion and Momentum in Forex Market](combining-mean-reversion-and-momentum-in-forex.md)
- [Asset Class Trend Following](../momentum/asset-class-trend-following.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/the-dynamic-breakout-ii-strategy)
