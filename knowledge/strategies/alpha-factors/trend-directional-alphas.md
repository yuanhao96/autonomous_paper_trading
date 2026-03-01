# Trend & Directional Alpha Factors

## Overview

These alphas measure trend strength, directional movement, and persistence. They include ADX-like measures, directional indicators, and trend-following signals derived from price action. Sourced from the WorldQuant 101 Formulaic Alphas (Kakushadze, 2015).

## Academic Reference

Kakushadze, Z. (2015). "101 Formulaic Alphas." *Wilmott Magazine*, 2016(84), 72--80. arXiv:1601.00991

## Strategy Logic

### Universe Selection

SPY (S&P 500 ETF). Single-ticker daily OHLCV data from yfinance.

### Signal Generation

- alpha > 0 --> LONG
- alpha <= 0 --> FLAT

### Entry/Exit Rules

- **Entry**: When alpha crosses above 0.
- **Exit**: When alpha crosses below 0.
- **Stop-loss**: 2% trailing stop.

### Portfolio Construction

95% position size (5% cash reserve).

### Rebalancing Schedule

Daily. Signals are recalculated at market close; orders executed at next open.

## Alpha Formulas

### Alpha#021

```
sma(close, 8) / close - 1 + sma(delta(close, 1), 8) / close
```

**Interpretation**: Price deviation from 8-day SMA plus smoothed daily change normalized by price. Combines trend position with trend velocity.

**Params**: `{"sma_window": 8, "delta_sma": 8}`

### Alpha#038

```
-1 * ts_rank(close, 10) + ts_rank(close / open, 10)
```

**Interpretation**: Rank of intraday returns minus rank of close level. Favors days where intraday performance is strong relative to overall price level positioning.

**Params**: `{"window": 10}`

### Alpha#049

```
where(delta(close, 1) > 0, delta(close, 1), 0) - where(delta(close, 1) < 0, delta(close, 1), 0)
```

**Interpretation**: Sum of absolute up and down moves (always positive). Simplifies to `abs(delta(close, 1))`. Measures total daily movement magnitude regardless of direction.

**Params**: `{}`

### Alpha#050

```
sma(where(delta(close, 1) > 0, 1, -1), 10)
```

**Interpretation**: Running average of up/down day indicators. +1 for each up day, -1 for each down day, averaged over 10 days. Directional consistency measure.

**Params**: `{"window": 10}`

### Alpha#051

```
where(sum(where(delta(close, 1) > 0, 1, 0), 12) >= 8, delta(close, 1), -1 * delta(close, 1))
```

**Interpretation**: If 8 or more of the last 12 days were up (strong uptrend), follow today's change. Otherwise, reverse it. Trend persistence conditional.

**Params**: `{"count_window": 12, "threshold": 8}`

### Alpha#069

```
delta(sma(close, 5), 5) / delay(sma(close, 5), 5)
```

**Interpretation**: 5-day rate of change of the 5-day SMA. Smoothed trend acceleration -- positive when the moving average is rising.

**Params**: `{"sma_window": 5, "roc_window": 5}`

### Alpha#093

```
sum(where(delta(close, 1) > 0, delta(close, 1), 0), 15) / sum(where(delta(close, 1) < 0, abs(delta(close, 1)), 0), 15) - 1
```

**Interpretation**: Ratio of total up-moves to total down-moves over 15 days, minus 1. Positive when up-move magnitude exceeds down-moves -- bullish directional bias.

**Params**: `{"window": 15}`

### Alpha#116

```
ts_rank(sma(delta(close, 1) / delay(close, 1), 10), 20)
```

**Interpretation**: Time-series rank of 10-day average return over 20 days. Measures where current smoothed momentum sits in its recent history.

**Params**: `{"return_sma": 10, "rank_window": 20}`

### Alpha#118

```
sum(where(high - delay(high, 1) > delay(low, 1) - low, high - delay(high, 1), 0), 14) / sum(where(delay(low, 1) - low > high - delay(high, 1), delay(low, 1) - low, 0), 14) - 1
```

**Interpretation**: ADX-like directional indicator: ratio of positive directional moves to negative directional moves over 14 days. Based on Wilder's +DI / -DI concept.

**Params**: `{"window": 14}`

### Alpha#147

```
sma(delta(close, 1) / delay(close, 1), 20) / stddev(delta(close, 1) / delay(close, 1), 20)
```

**Interpretation**: Information ratio / Sharpe-like measure over 20 days. Mean return divided by return volatility -- reward-to-risk trending signal.

**Params**: `{"window": 20}`

### Alpha#187

```
sum(where(delta(close, 1) > 0, 1, 0), 20) / 20 - 0.5 + sma(delta(close, 1), 10) / close
```

**Interpretation**: Win rate (fraction of up days) over 20 days, centered at 0.5, plus smoothed daily change. Combines directional consistency with trend magnitude.

**Params**: `{"count_window": 20, "sma_window": 10}`

## Data Requirements

- **Source**: yfinance
- **Ticker**: SPY
- **Frequency**: Daily OHLCV
- **Minimum warmup**: 50 days (longest rolling window is 20; extra buffer for nested operators)

## Implementation Notes

Operator-to-pandas mapping for translating alpha formulas into code:

| Operator | Pandas / NumPy Equivalent | Example |
|----------|---------------------------|---------|
| `delay(x, d)` | `x.shift(d)` | `close.shift(1)` |
| `delta(x, d)` | `x.diff(d)` | `close.diff(1)` |
| `sma(x, d)` | `x.rolling(d).mean()` | `close.rolling(8).mean()` |
| `ts_rank(x, d)` | `x.rolling(d).rank(pct=True)` | `close.rolling(10).rank(pct=True)` |
| `stddev(x, d)` | `x.rolling(d).std()` | `ret.rolling(20).std()` |
| `sum(x, d)` | `x.rolling(d).sum()` | `up.rolling(15).sum()` |
| `where(cond, x, y)` | `np.where(cond, x, y)` | `np.where(delta > 0, 1, -1)` |
| `abs(x)` | `np.abs(x)` | `np.abs(close.diff(1))` |
| `sign(x)` | `np.sign(x)` | `np.sign(delta)` |

## Risk Considerations

- **Lag**: Trend-following signals are late by construction. Smoothing (SMA, rolling sums) introduces lag that delays entries and exits relative to the true turning point.
- **Whipsaws**: In ranging or choppy markets, these alphas will generate frequent false signals as the alpha oscillates around zero.
- **Noise on single stocks**: ADX-like measures (e.g., Alpha#118) were designed for cross-sectional ranking across many instruments. Applied to a single ticker (SPY), they can be noisy.
- **Transaction costs**: Daily rebalancing creates friction. Frequent signal flips erode returns through spread and commission costs.

## Related Strategies

- [Momentum & Price Alphas](momentum-price-alphas.md)
- [Mean-Reversion & RSI Alphas](mean-reversion-rsi-alphas.md)
- [Volume-Price Alphas](volume-price-alphas.md)
- [Volatility Alphas](volatility-alphas.md)
- [Price Channel Alphas](price-channel-alphas.md)
- [Composite Alphas](composite-alphas.md)

## Source

Kakushadze, Z. (2015). "101 Formulaic Alphas." *Wilmott Magazine*, 2016(84), 72--80. Available at: https://arxiv.org/abs/1601.00991
