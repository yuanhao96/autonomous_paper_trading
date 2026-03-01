# Price Channel Alpha Factors

## Overview

These alphas exploit price channel patterns: Donchian-like breakouts, high/low range ratios, and support/resistance levels derived from rolling price extremes. They capture where the current price sits within its recent trading range, identify breakout events, and measure deviation from channel boundaries.

Sourced from WorldQuant 101 Formulaic Alphas (Kakushadze, 2015).

## Academic Reference

Kakushadze, Z. (2015). "101 Formulaic Alphas." *Wilmott Magazine*, 2016(84), 72--80. arXiv:1601.00991

## Strategy Logic

### Universe Selection

SPY (S&P 500 ETF). Single-ticker daily OHLCV data from yfinance.

### Signal Generation

- Compute the alpha value for each trading day.
- `alpha > 0` --> LONG
- `alpha <= 0` --> FLAT

### Entry/Exit Rules

- **Entry**: Enter LONG when alpha crosses above 0 from below.
- **Exit**: Exit (go FLAT) when alpha crosses below 0 from above.
- **Stop-loss**: 2% trailing stop-loss.

### Portfolio Construction

- Position size: 95% of equity per trade.
- Single position at a time (no pyramiding).

### Rebalancing Schedule

Daily. Signals are recalculated at market close; orders execute at next open.

## Alpha Formulas

### Alpha#028

```
(close - ts_min(low, 12)) / (ts_max(high, 12) - ts_min(low, 12) + 1e-8)
```

**Interpretation**: Price position within the 12-day Donchian channel. A value of 1.0 means the close is at the channel high; 0.0 means at the channel low. Acts as a breakout indicator -- values near 1.0 suggest upside breakout momentum.

**Params**: `{"window": 12}`

### Alpha#047

```
(ts_max(high, 6) - close) / (ts_max(high, 6) - ts_min(low, 6) + 1e-8) * volume / sma(volume, 20)
```

**Interpretation**: Distance from channel high, normalized by channel width, scaled by relative volume. Combines channel position with volume confirmation. High values indicate the price is far from the channel top on above-average volume.

**Params**: `{"channel_window": 6, "vol_sma": 20}`

### Alpha#057

```
-1 * (close - sma(close, 30)) / decay_linear(close / delay(close, 1), 10)
```

**Interpretation**: Deviation from 30-day SMA divided by linearly-weighted recent returns. Contrarian when price deviates from SMA with declining momentum -- reverts toward the mean when the deviation is large but momentum is fading.

**Params**: `{"sma_window": 30, "decay_window": 10}`

### Alpha#072

```
(sma(high, 5) - close) / (sma(high, 5) - sma(low, 5) + 1e-8)
```

**Interpretation**: Where close sits relative to the smoothed high/low channel. Near 0 means the close is near recent highs; near 1 means the close is near recent lows. A fast-reacting channel position indicator.

**Params**: `{"window": 5}`

### Alpha#078

```
(close - ts_min(low, 20)) / (ts_max(high, 20) - ts_min(low, 20) + 1e-8) - 0.5
```

**Interpretation**: 20-day Donchian channel position, centered at zero. Positive values indicate the price is in the upper half of the channel (bullish); negative values indicate the lower half (bearish). Zero-centered for direct use as a signal.

**Params**: `{"window": 20}`

### Alpha#082

```
delay(ts_max(high, 15), 1) < close
```

**Interpretation**: Boolean: did today's close exceed yesterday's 15-day high? Returns true (1) on breakout days. Converts to a 1/0 signal.

**Note**: Result is 1.0 for breakout, 0.0 otherwise. Apply as: `float(close > delay(ts_max(high, 15), 1)) - 0.5` to center at zero.

**Params**: `{"window": 15}`

### Alpha#096

```
ts_max(close, 10) / close - 1 + delta(close, 3) / delay(close, 3)
```

**Interpretation**: Drawdown from 10-day high plus 3-day return. The negative drawdown component is offset by positive momentum recovery. Signals recovery from dips -- positive when the 3-day bounce exceeds the drawdown from the recent high.

**Params**: `{"max_window": 10, "return_window": 3}`

### Alpha#103

```
(close - ts_min(low, 20)) / (close + 1e-8) * 100
```

**Interpretation**: Distance from 20-day low as a percentage of current price. Large values indicate the price has rallied far from support -- potential resistance level or trend continuation depending on context.

**Params**: `{"window": 20}`

### Alpha#126

```
(close + high + low) / 3 - sma((close + high + low) / 3, 20)
```

**Interpretation**: Typical price (pivot point) minus its 20-day SMA. Measures pivot-point deviation from trend. Positive when the current pivot is above the average pivot -- indicates near-term bullishness.

**Params**: `{"sma_window": 20}`

### Alpha#133

```
ts_rank(high - low, 20) - ts_rank(delta(close, 1), 20)
```

**Interpretation**: Range rank minus return rank over a 20-day window. High when today's range is historically wide but the return is historically modest -- signals potential reversal from range expansion without directional follow-through.

**Params**: `{"window": 20}`

### Alpha#177

```
(ts_max(high, 20) - close) / (ts_max(high, 20) - ts_min(low, 20) + 1e-8)
```

**Interpretation**: Distance from the 20-day channel top, normalized by channel width. Near 0 means close is near the high (bullish breakout territory); near 1 means close is near the low (bearish). Inverse of Alpha#078.

**Params**: `{"window": 20}`

## Data Requirements

- **Source**: yfinance (`yf.download`)
- **Ticker**: SPY
- **Frequency**: Daily OHLCV (Open, High, Low, Close, Volume)
- **Minimum warmup period**: 30 days (longest lookback across all alphas is 20--30 days)
- **Fields used**: `open`, `high`, `low`, `close`, `volume`

## Implementation Notes

Operator-to-pandas mapping for translating alpha formulas into code:

| Alpha Operator | Pandas Implementation | Description |
|---|---|---|
| `delay(x, d)` | `x.shift(d)` | Lag the series by `d` periods |
| `delta(x, d)` | `x.diff(d)` | Difference: `x - x.shift(d)` |
| `sma(x, d)` | `x.rolling(d).mean()` | Simple moving average over `d` periods |
| `ts_min(x, d)` | `x.rolling(d).min()` | Rolling minimum over `d` periods |
| `ts_max(x, d)` | `x.rolling(d).max()` | Rolling maximum over `d` periods |
| `decay_linear(x, d)` | `x.rolling(d).apply(lambda w: np.dot(w, np.arange(1, d+1)) / np.sum(np.arange(1, d+1)))` | Linearly-weighted rolling sum (recent values weighted more) |
| `ts_rank(x, d)` | `x.rolling(d).rank(pct=True).iloc[-1]` or `x.rolling(d).apply(lambda w: pd.Series(w).rank(pct=True).iloc[-1])` | Percentile rank of the current value within the rolling window |

- Add `1e-8` to denominators to prevent division by zero.
- All rolling windows use `min_periods=window` to avoid partial-window artifacts during warmup.
- Boolean alphas (e.g., Alpha#082) should be converted to float and centered at zero (subtract 0.5) for consistent signal generation.

## Risk Considerations

- **False breakouts**: Channel breakout strategies suffer from false breakouts in ranging/sideways markets, leading to whipsaw losses.
- **Lagging signals**: Donchian channels inherently lag in fast-moving markets. By the time a breakout is confirmed, much of the move may already be priced in.
- **Volume anomalies**: Volume-weighted channel signals (e.g., Alpha#047) may give conflicting or unreliable readings when volume is unusually high or low (e.g., around holidays, earnings, or index rebalancing events).
- **Daily rebalancing friction**: Daily signal recalculation and rebalancing creates transaction costs that can erode returns, especially for alphas with frequent signal changes.
- **Regime sensitivity**: Channel-based alphas tend to perform well in trending markets but poorly in mean-reverting or choppy regimes.

## Related Strategies

- [Momentum & Price Alphas](momentum-price-alphas.md)
- [Mean-Reversion & RSI Alphas](mean-reversion-rsi-alphas.md)
- [Volume-Price Alphas](volume-price-alphas.md)
- [Volatility Alphas](volatility-alphas.md)
- [Trend & Directional Alphas](trend-directional-alphas.md)
- [Composite Alphas](composite-alphas.md)

## Source

Kakushadze, Z. (2015). "101 Formulaic Alphas." *Wilmott Magazine*, 2016(84), 72--80. Available at: https://arxiv.org/abs/1601.00991
