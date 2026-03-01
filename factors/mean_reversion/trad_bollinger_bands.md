# TRAD: Bollinger Band Mean Reversion

## Formula
sma(close, 20) - 2 * stddev(close, 20) - close

## Interpretation
Distance between the lower Bollinger Band and the current price. Positive when price is below the lower band (oversold), signaling a mean-reversion buy opportunity. The lower band is defined as the 20-day SMA minus 2 standard deviations.

## Parameters
| Param | Default | Range |
|-------|---------|-------|
| sma_window | 20 | [10, 50] |
| num_std | 2 | [1, 3] |

## Category
mean_reversion

## Source
Traditional strategy: Mean Reversion with Bollinger Bands (Bollinger 1983)
