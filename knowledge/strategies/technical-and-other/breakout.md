# Breakout Strategy

## Overview

A momentum/trend-following strategy that enters positions when price breaks above a resistance level (recent high) or below a support level (recent low). Captures the beginning of new trends by detecting when price escapes its recent trading range.

## Academic Reference

- **Paper**: "Channel Breakout Revisited", various commodity trading advisors (CTAs)
- **Link**: https://quantpedia.com/strategies/channel-breakout/

## Strategy Logic

### Universe Selection

Liquid equities, ETFs, or futures with sufficient volatility for breakout detection.

### Signal Generation

Compute the recent high-low channel over a lookback period:

```
Upper = max(High, lookback)
Lower = min(Low, lookback)
Range = Upper - Lower
Entry_Upper = Lower + k1 * Range
Entry_Lower = Upper - k2 * Range
```

### Entry / Exit Rules

- **Entry**: Go long when Close > Entry_Upper (upward breakout).
- **Exit**: Close position when Close < Entry_Lower (downward breakout).
- **Variation**: Donchian channel uses simple N-day high/low without the k factors.

### Portfolio Construction

Equal-weight across assets with active breakout signals, subject to position limits.

### Rebalancing Schedule

Daily — breakout conditions checked at each bar close.

## Key Indicators / Metrics

- **Lookback period**: 20 days (configurable, range 10–60)
- **k1 (upper breakout factor)**: 0.5–0.7 (configurable)
- **k2 (lower breakout factor)**: 0.5–0.7 (configurable)
- **ATR**: Average True Range can be used for volatility-adjusted breakout levels

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | 2000–2020 | Buy-and-hold |
| Annual Return | ~8–14% | ~8% |
| Sharpe Ratio | ~0.5–0.8 | ~0.4 |
| Max Drawdown | ~20% | ~55% |

## Data Requirements

- **Asset Classes**: Equities, ETFs, futures, commodities
- **Resolution**: Daily
- **Lookback Period**: lookback period + warm-up

## Implementation Notes

- Classic Turtle Trading system used 20-day and 55-day breakouts.
- The k1/k2 factors control how aggressive the breakout detection is.
- Works best on instruments with clear trending periods.

## Risk Considerations

- Many false breakouts in range-bound markets lead to frequent small losses.
- Strategy relies on a few large winners to compensate for many small losers.
- Breakout timing lag may result in entering after much of the move has occurred.
- Stop-loss placement is critical to manage false breakout risk.

## Related Strategies

- [Dual Thrust Trading Algorithm](dual-thrust-trading-algorithm.md)
- [Dynamic Breakout II Strategy](dynamic-breakout-ii-strategy.md)
- [Trend Following](trend-following.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/breakout)
