# Moving Average Crossover

## Overview

A trend-following strategy that generates buy signals when a fast moving average crosses above a slow moving average, and sell signals on the reverse crossover. One of the most fundamental technical analysis strategies, it captures medium-term trends while filtering out short-term noise.

## Academic Reference

- **Paper**: "Technical Analysis of the Financial Markets", John Murphy (1999)
- **Link**: https://quantpedia.com/strategies/moving-average-crossover/

## Strategy Logic

### Universe Selection

Liquid equities, ETFs, or futures with trending behavior.

### Signal Generation

Compute two simple moving averages (SMA) with different periods:

```
Fast_MA = SMA(Close, fast_period)   # e.g., 10 days
Slow_MA = SMA(Close, slow_period)   # e.g., 50 days
```

### Entry / Exit Rules

- **Entry**: Go long when Fast_MA crosses above Slow_MA (golden cross).
- **Exit**: Close position when Fast_MA crosses below Slow_MA (death cross).

### Portfolio Construction

Equal-weight allocation across assets with active long signals.

### Rebalancing Schedule

Daily — crossover checked at each bar close.

## Key Indicators / Metrics

- **Fast period**: 10 days (configurable, range 5–50)
- **Slow period**: 50 days (configurable, range 20–200)
- Can use EMA (exponential) instead of SMA for faster responsiveness.

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | 2000–2020 | Buy-and-hold |
| Annual Return | ~6–10% | ~8% |
| Sharpe Ratio | ~0.4–0.7 | ~0.4 |
| Max Drawdown | ~20% | ~55% |

## Data Requirements

- **Asset Classes**: Equities, ETFs, futures
- **Resolution**: Daily
- **Lookback Period**: slow_period + warm-up bars

## Implementation Notes

- Previous-bar crossover detection required to avoid lookahead bias.
- SMA is straightforward; EMA gives more weight to recent prices.
- Common parameter pairs: 10/50, 20/100, 50/200.

## Risk Considerations

- Whipsaw losses in sideways/choppy markets — frequent false crossovers.
- Lagging indicator — entries and exits are delayed versus actual trend changes.
- Parameter optimization may overfit to historical data.
- Underperforms buy-and-hold in strong bull markets due to delayed re-entry.

## Related Strategies

- [Trend Following](trend-following.md)
- [Ichimoku Clouds in Energy Sector](ichimoku-clouds-in-energy-sector.md)
- [Paired Switching](paired-switching.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/moving-average-crossover)
