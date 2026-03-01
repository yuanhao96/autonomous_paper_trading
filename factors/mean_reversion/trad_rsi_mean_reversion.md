# TRAD: RSI Mean Reversion

## Formula
sum(where(delta(close, 1) < 0, abs(delta(close, 1)), 0), 14) / (sum(abs(delta(close, 1)), 14) + 1e-8) - 0.5

## Interpretation
Proportion of total absolute price movement that was downward over 14 days, centered at zero. Positive when there have been more down-moves than up-moves (oversold), signaling a mean-reversion buy. Equivalent to an inverted RSI centered at 0.5: when RSI < 50 this is positive. Classic RSI mean-reversion strategy buys oversold conditions.

## Parameters
| Param | Default | Range |
|-------|---------|-------|
| window | 14 | [7, 28] |

## Category
mean_reversion

## Source
Traditional strategy: Mean Reversion with RSI (Wilder 1978)
