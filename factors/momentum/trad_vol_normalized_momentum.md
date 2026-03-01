# TRAD: Volatility-Normalized Momentum

## Formula
(close / delay(close, 252) - 1) / (stddev(delta(close, 1) / delay(close, 1), 252) + 1e-8)

## Interpretation
12-month return divided by 12-month return volatility. A Sharpe-ratio-like momentum signal that adjusts for risk. Positive when trailing risk-adjusted return is positive. Normalizing by volatility reduces whipsaws in high-volatility environments.

## Parameters
| Param | Default | Range |
|-------|---------|-------|
| lookback | 252 | [63, 504] |

## Category
momentum

## Source
Traditional strategy: Time-Series Momentum Effect with volatility scaling (Moskowitz et al. 2012)
