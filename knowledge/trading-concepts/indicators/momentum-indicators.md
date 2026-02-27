# Momentum Indicators

## Overview

Momentum indicators measure the speed and magnitude of price changes over a given period. They help identify overbought/oversold conditions, gauge trend strength, and detect potential reversals through divergence. Most are oscillators bounded within a fixed range, making them useful for mean-reversion signals.

## Relative Strength Index (RSI)

**Formula**: `RSI = 100 - (100 / (1 + RS))`, where `RS = Average Gain / Average Loss` over N periods.
**Default period**: 14. **Overbought**: >70. **Oversold**: <30.

- Bullish divergence: price makes lower low while RSI makes higher low
- Bearish divergence: price makes higher high while RSI makes lower high
- Centerline crossover: RSI crossing above 50 suggests bullish momentum; below 50 suggests bearish

## MACD (Moving Average Convergence Divergence)

- **MACD Line** = `EMA(12) - EMA(26)`
- **Signal Line** = `EMA(9) of MACD Line`
- **Histogram** = `MACD Line - Signal Line`

Defaults: fast=12, slow=26, signal=9. MACD is unbounded and has no fixed overbought/oversold levels.
- Signal line crossover: MACD crossing above Signal Line is bullish; below is bearish
- Zero-line crossover indicates momentum direction shift
- Histogram expansion/contraction shows strengthening/weakening momentum

## Stochastic Oscillator

- `%K = ((Close - Lowest Low) / (Highest High - Lowest Low)) x 100`
- `%D = SMA(3) of %K`

**Default period**: 14. **Overbought**: >80. **Oversold**: <20.
- %K crossing above %D in oversold territory is a buy signal (and vice versa)
- Divergence between stochastic and price warns of potential reversals

## Stochastic RSI

**Formula**: `StochRSI = (RSI - Lowest RSI) / (Highest RSI - Lowest RSI)`
**Default**: RSI period=14, Stochastic period=14. Scaled 0 to 1. Overbought >0.80, Oversold <0.20.
- More sensitive than standard RSI — generates earlier signals but with more noise
- Best used with a smoothing line to filter whipsaws

## Rate of Change (ROC)

**Formula**: `ROC = ((Close - Close_n) / Close_n) x 100`
**Default period**: 12. Unbounded — no fixed overbought/oversold levels.
- Positive ROC = upward momentum; negative = downward momentum
- Zero-line crossovers signal momentum shifts; divergence warns of weakening trends

## Momentum Indicator (MOM)

**Formula**: `MOM = Close - Close_n`
**Default period**: 10. The simplest momentum measure — raw price difference over N bars.
- Rising MOM = accelerating price; falling MOM = decelerating price
- Zero-line crossover signals direction change
- Not normalized, so absolute values depend on asset price (unlike ROC)

## Commodity Channel Index (CCI)

**Formula**: `CCI = (Typical Price - SMA) / (0.015 x Mean Deviation)`, where `Typical Price = (H + L + C) / 3`.
**Default period**: 20. **Overbought**: >+100. **Oversold**: <-100.
- The 0.015 constant ensures ~70-80% of values fall between -100 and +100
- CCI crossing above +100 then falling back below can signal short entries
- Effective for detecting cyclical price patterns

## Williams %R

**Formula**: `%R = ((Highest High - Close) / (Highest High - Lowest Low)) x -100`
**Default period**: 14. **Overbought**: >-20. **Oversold**: <-80.
- Mathematically the inverse of Stochastic %K, scaled to a negative range (-100 to 0)
- Useful for timing entries when combined with a trend filter

## Aroon Oscillator

- `Aroon Up = ((N - periods since N-period high) / N) x 100`
- `Aroon Down = ((N - periods since N-period low) / N) x 100`
- `Aroon Oscillator = Aroon Up - Aroon Down`

**Default period**: 25. Range: -100 to +100.
- Oscillator > 0: bullish (recent highs more recent than recent lows)
- Values near +100 or -100 indicate strong trends; crossovers signal trend changes

## Ultimate Oscillator

Weighted average of buying pressure across three timeframes:
- `BP = Close - Min(Low, Previous Close)`, `TR = Max(High, Previous Close) - Min(Low, Previous Close)`
- `UO = 100 x ((4 x Avg7) + (2 x Avg14) + Avg28) / 7`

**Defaults**: periods 7, 14, 28. **Overbought**: >70. **Oversold**: <30.
- Multi-timeframe design reduces false signals common in single-period oscillators
- Divergence-based signals are its primary use case

## Summary Comparison

| Indicator | Range | Overbought | Oversold | Primary Use |
|-----------|-------|------------|----------|-------------|
| RSI | 0-100 | >70 | <30 | Overbought/oversold, divergence |
| MACD | Unbounded | N/A | N/A | Trend momentum, crossovers |
| Stochastic | 0-100 | >80 | <20 | Overbought/oversold, timing |
| Stochastic RSI | 0-1 | >0.80 | <0.20 | Sensitive momentum shifts |
| ROC | Unbounded | N/A | N/A | Momentum direction, divergence |
| Momentum | Unbounded | N/A | N/A | Simple momentum measurement |
| CCI | Unbounded | >+100 | <-100 | Cyclical trend detection |
| Williams %R | -100-0 | >-20 | <-80 | Timing entries, inverse stochastic |
| Aroon Osc. | -100-100 | N/A | N/A | Trend direction and strength |
| Ultimate Osc. | 0-100 | >70 | <30 | Multi-timeframe confirmation |

*Source: Generalized from QuantConnect Indicators documentation.*
