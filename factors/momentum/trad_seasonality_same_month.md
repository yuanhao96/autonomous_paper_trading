# TRAD: Same-Calendar-Month Seasonality

## Formula
(delay(close, 231) - delay(close, 252)) / (delay(close, 252) + 1e-8)

## Interpretation
Return during the same approximate calendar month one year ago (trading days 252 to 231 ago, spanning ~21 trading days). Stocks that performed well in a particular calendar month tend to perform well in the same month the following year. Positive when last year's same-month return was positive.

## Parameters
| Param | Default | Range |
|-------|---------|-------|
| year_offset | 252 | [240, 260] |
| month_length | 21 | [15, 25] |

## Category
momentum

## Source
Traditional strategy: Seasonality Effect Based on Same-Calendar Month Returns (Heston & Sadka 2008)
