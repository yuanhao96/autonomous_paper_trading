# Trend Following

## Overview

A systematic strategy that identifies and follows established price trends across assets. Goes long assets in uptrends and exits (or shorts) assets in downtrends. Trend following is one of the most robust and widely-used quantitative strategies, particularly in managed futures.

## Academic Reference

- **Paper**: "A Century of Evidence on Trend-Following Investing", Hurst, Ooi, Pedersen (2017)
- **Link**: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2993026

## Strategy Logic

### Universe Selection

Diversified pool of liquid futures, ETFs, or equities across asset classes.

### Signal Generation

Trend identified via moving average crossover or trailing return:

```
Approach 1: Fast_MA > Slow_MA → uptrend
Approach 2: Return(Close, lookback) > 0 → uptrend
```

### Entry / Exit Rules

- **Entry**: Go long when the trend indicator signals an uptrend.
- **Exit**: Close position when trend reverses (fast MA crosses below slow MA, or trailing return turns negative).

### Portfolio Construction

Equal-weight or risk-parity allocation across assets with positive trend signals. Volatility scaling optional.

### Rebalancing Schedule

Monthly or weekly.

## Key Indicators / Metrics

- **Fast MA period**: 20 days (configurable)
- **Slow MA period**: 200 days (configurable)
- **Alternative**: Price vs 200-day SMA as simple trend filter

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | 1880–2016 | Buy-and-hold |
| Annual Return | ~11% | ~8% |
| Sharpe Ratio | ~0.7 | ~0.4 |
| Max Drawdown | ~25% | ~80% |

## Data Requirements

- **Asset Classes**: Multi-asset (equities, bonds, commodities, currencies)
- **Resolution**: Daily
- **Lookback Period**: Slow MA period + warm-up

## Implementation Notes

- Trend following has worked across centuries and asset classes.
- Can be implemented with moving averages, breakout rules, or time-series momentum signals.
- Risk management through position sizing (e.g., volatility targeting) is critical.

## Risk Considerations

- Extended periods of underperformance in trendless markets (e.g., 2011–2013).
- Whipsaw losses during choppy markets erode returns.
- Requires patience — strategy may have low win rate but large average winners.
- Crowding in popular trend signals can reduce effectiveness.

## Related Strategies

- [Moving Average Crossover](moving-average-crossover.md)
- [Asset Class Trend Following](../momentum/asset-class-trend-following.md)
- [Commodities Futures Trend Following](../momentum/commodities-futures-trend-following.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/trend-following)
