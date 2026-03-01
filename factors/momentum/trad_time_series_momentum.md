# TRAD: 12-Month Time-Series Momentum

## Formula
close / delay(close, 252) - 1

## Interpretation
12-month (252 trading days) return. Positive when the asset has risen over the past year, capturing time-series momentum. One of the most robust and well-documented momentum signals across asset classes. Go long when trailing return is positive.

## Parameters
| Param | Default | Range |
|-------|---------|-------|
| lookback | 252 | [63, 504] |

## Category
momentum

## Source
Traditional strategy: Time-Series Momentum (Moskowitz, Ooi, Pedersen 2012)
