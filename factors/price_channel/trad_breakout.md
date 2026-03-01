# TRAD: Channel Breakout

## Formula
(close - ts_min(low, 20)) / (ts_max(high, 20) - ts_min(low, 20) + 1e-8) - 0.5

## Interpretation
Normalized position of the current close within the 20-day Donchian channel, centered at zero. Positive when the close is in the upper half of the channel (bullish breakout territory), negative when in the lower half. A classic breakout/trend-following signal.

## Parameters
| Param | Default | Range |
|-------|---------|-------|
| window | 20 | [10, 60] |

## Category
price_channel

## Source
Traditional strategy: Breakout Strategy (Donchian channel breakout)
