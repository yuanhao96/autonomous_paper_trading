# TRAD: Dual Thrust Range Breakout

## Formula
close - open - 0.5 * where(ts_max(high, 4) - ts_min(close, 4) > ts_max(close, 4) - ts_min(low, 4), ts_max(high, 4) - ts_min(close, 4), ts_max(close, 4) - ts_min(low, 4))

## Interpretation
Distance of the close above the dynamic breakout threshold. The threshold is the open price plus half the "range" (the larger of HH-LC or HC-LL over the last 4 days). Positive when the close exceeds the breakout cap, indicating an upward range breakout. Originally an intraday algorithm, adapted here for daily bars.

## Parameters
| Param | Default | Range |
|-------|---------|-------|
| range_window | 4 | [2, 10] |
| k_factor | 0.5 | [0.3, 0.8] |

## Category
price_channel

## Source
Traditional strategy: Dual Thrust Trading Algorithm
