# TRAD: Trend Following (Price vs 200-Day SMA)

## Formula
close - sma(close, 200)

## Interpretation
Distance of the current price above or below the 200-day simple moving average. Positive when price is above the long-term trend (bullish), negative when below (bearish). The 200-day SMA is the most widely watched trend indicator in equity markets.

## Parameters
| Param | Default | Range |
|-------|---------|-------|
| sma_window | 200 | [100, 300] |

## Category
trend

## Source
Traditional strategy: Trend Following (SMA trend filter)
