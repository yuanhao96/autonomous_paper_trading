# Dual Thrust Trading Algorithm

## Overview

Intraday breakout strategy that calculates a dynamic range from the prior 4 days' highs, lows, and closes, then enters long when price breaks above (open + K₁ × range) and short when price breaks below (open − K₂ × range). Reversal system: positions flip on opposite signals. Originally developed by Michael Chalek.

## Academic Reference

- **Paper**: "Dual Thrust Intraday Strategy" — Gang Wei (May 2012)
- Original system developed by Michael Chalek for Futures Magazine (1996).

## Strategy Logic

### Universe Selection

Primary: SPY (S&P 500 ETF). Also applicable to futures and forex.

### Signal Generation

**Range calculation**: Range = max(HH − LC, HC − LL)

Where over N=4 days: HH = highest high, HC = highest close, LC = lowest close, LL = lowest low.

**Thresholds**:
- Cap (buy trigger) = Open + K₁ × Range
- Floor (sell trigger) = Open − K₂ × Range
- Default: K₁ = K₂ = 0.5

### Entry / Exit Rules

- **Long**: Price breaks above cap line.
- **Short**: Price breaks below floor line.
- **Reversal**: If holding opposite position, liquidate first then reverse.

### Portfolio Construction

80% allocation per position. Single-asset.

### Rebalancing Schedule

Daily. Thresholds recalculated at market open.

## Key Indicators / Metrics

- 4-day historical high/low/close
- Opening price
- Dynamic range metric
- K₁, K₂ parameters (default 0.5)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2004 – Aug 2017 |
| Sharpe Ratio | -0.17 |
| Max Drawdown | 41.1% |
| Initial Capital | $100,000 |

## Data Requirements

- **Asset Classes**: US equity ETF (SPY) or futures/forex
- **Resolution**: Hourly (intraday execution)
- **Lookback**: 4 days (OHLC)

## Implementation Notes

- `history(4, Resolution.DAILY)` for range data retrieval.
- Scheduled events for daily signal computation at market open.
- Reversal system: liquidate opposite position before new entry.
- Python on QuantConnect LEAN.

## Risk Considerations

- Negative Sharpe (−0.17) with 41.1% max drawdown — poor risk-adjusted performance.
- "Works better in trending market but will trigger fake buy and sell signals in volatile markets."
- K₁ and K₂ parameters need dynamic adjustment for different market regimes.
- No stop-loss or position sizing controls in basic version.
- Single-asset concentration.
- Reversal system can whipsaw in range-bound markets.
- Authors suggest adding technical indicators and dynamic parameter adjustment.

## Related Strategies

- [Ichimoku Clouds in the Energy Sector](ichimoku-clouds-in-energy-sector.md)
- [The Dynamic Breakout II Strategy](../forex/dynamic-breakout-ii-strategy.md)
- [Commodities Futures Trend Following](../momentum/commodities-futures-trend-following.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/dual-thrust-trading-algorithm)
