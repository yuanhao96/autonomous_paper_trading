# TRAD: Moving Average Crossover

## Formula
sma(close, 10) - sma(close, 50)

## Interpretation
Difference between the 10-day and 50-day simple moving averages. Positive when the fast SMA is above the slow SMA (golden cross / uptrend), negative when below (death cross / downtrend). One of the most widely used trend-following signals.

## Parameters
| Param | Default | Range |
|-------|---------|-------|
| fast_window | 10 | [5, 20] |
| slow_window | 50 | [30, 100] |

## Category
momentum

## Source
Traditional strategy: Moving Average Crossover
