# Mean Reversion & RSI Alpha Factors

## Overview

This document collects 13 formulaic alpha factors from the WorldQuant "101 Alphas" universe that share a common theme: **mean reversion and oscillator-type signals**. Each alpha captures some notion of price overextension (overbought/oversold) and bets on reversion to a local mean or equilibrium level.

These factors originate from WorldQuant's systematic alpha research program, which distills decades of quantitative trading intuition into compact, formulaic expressions that operate on standard OHLCV data. The alphas selected here are those most naturally suited to single-instrument mean-reversion trading on a daily timeframe.

## Academic Reference

- **Kakushadze, Z. (2015)**. "101 Formulaic Alphas." *Wilmott Magazine*, 2016(84), 72-80. Also available as SSRN working paper (SSRN #2701346).
- The paper presents 101 real-life quantitative trading alphas expressed as closed-form formulas using standard price/volume operators. The alphas were used in production at WorldQuant LLC.

## Strategy Logic

### Universe Selection

- **Instrument**: SPY (S&P 500 ETF)
- **Rationale**: Highly liquid, tight spreads, well-suited for daily rebalancing. Mean-reversion dynamics are well-documented in broad equity indices over short horizons.

### Signal Generation

Each alpha formula produces a continuous scalar value for each trading day. The trading signal is derived by thresholding at zero:

- **alpha > 0** --> LONG
- **alpha <= 0** --> FLAT (no position)

### Entry/Exit Rules

- **Entry**: Enter a LONG position when the alpha value crosses above 0 from below (or on the first day the alpha is positive).
- **Exit**: Exit the position (go FLAT) when the alpha value crosses below 0 from above (or equals 0).
- No short positions are taken in the base configuration.

### Portfolio Construction

- **Position size**: 95% of portfolio equity when LONG.
- **Cash reserve**: 5% maintained for transaction costs and margin of safety.

### Rebalancing Schedule

- **Frequency**: Daily, at market close.
- Signals are computed from end-of-day OHLCV data; orders are placed for the next trading day's open.

## Alpha Formulas

### Alpha#023

**Formula**: `where(sma(high, 20) < high, -1 * delta(high, 2), 0)`

**Interpretation**: If today's high exceeds the 20-day average high (overextension), short the 2-day high change. Mean reversion from overbought highs.

**Params**: `{"sma_window": 20, "delta_days": 2}`

---

### Alpha#052

**Formula**: `delta(ts_min(low, 5), 5) / 5 - delta(close, 5) / 5`

**Interpretation**: Difference between the rate of change of 5-day lows and 5-day close change. Positive when lows are rising faster than closes -- reversion from oversold.

**Params**: `{"window": 5}`

---

### Alpha#063

**Formula**: `sma(close - sma(close, 20), 5) / stddev(close, 20)`

**Interpretation**: Smoothed deviation from 20-day mean, normalized by volatility. Z-score-like mean reversion signal.

**Params**: `{"mean_window": 20, "smooth_window": 5, "std_window": 20}`

---

### Alpha#067

**Formula**: `(close - ts_min(close, 24)) / (ts_max(close, 24) - ts_min(close, 24) + 1e-8) - 0.5`

**Interpretation**: Stochastic oscillator variant over 24 days, centered at zero. Above 0 = upper half of range, below 0 = lower half.

**Params**: `{"window": 24}`

---

### Alpha#079

**Formula**: `delta(close, 3) / delay(close, 3) + sign(delta(close, 3)) * stddev(close, 20) / close`

**Interpretation**: 3-day return adjusted by volatility. Penalizes large moves -- mean reversion in volatile conditions.

**Params**: `{"return_window": 3, "vol_window": 20}`

---

### Alpha#086

**Formula**: `(close - sma(close, 10)) / stddev(close, 10)`

**Interpretation**: Classic z-score: deviation from 10-day mean divided by standard deviation. Core mean-reversion signal.

**Params**: `{"window": 10}`

---

### Alpha#110

**Formula**: `sma(high - low, 10) / close - (high - low) / close`

**Interpretation**: Average normalized range minus current normalized range. Positive when current range is narrow (contraction -- expect expansion).

**Params**: `{"window": 10}`

---

### Alpha#112

**Formula**: `(sma(close, 12) - close) / (stddev(close, 12) + 1e-8)`

**Interpretation**: Inverted z-score (positive when price is below average). Direct mean reversion -- buy when cheap relative to recent range.

**Params**: `{"window": 12}`

---

### Alpha#128

**Formula**: `where((close - ts_min(close, 14)) / (ts_max(close, 14) - ts_min(close, 14) + 1e-8) > 0.7, -1 * delta(close, 3) / close, delta(close, 3) / close)`

**Interpretation**: When price is in the top 30% of its 14-day range (overbought), flip the 3-day return signal. RSI-style reversal.

**Params**: `{"range_window": 14, "overbought_threshold": 0.7, "return_window": 3}`

---

### Alpha#129

**Formula**: `sum(where(delta(close, 1) < 0, abs(delta(close, 1)), 0), 12) / sum(abs(delta(close, 1)), 12) - 0.5`

**Interpretation**: Proportion of total absolute movement that was downward, over 12 days, centered at 0.5. Similar to RSI but centered -- negative means more up days (overbought), positive means more down days (oversold reversal signal).

**Params**: `{"window": 12}`

---

### Alpha#162

**Formula**: `(sma(close, 12) - close) / sma(close, 12) + sma(delta(close, 1) / delay(close, 1), 12)`

**Interpretation**: Mean reversion component (distance from SMA) plus momentum component (average return). Balances reversion with trend confirmation.

**Params**: `{"sma_window": 12, "return_window": 12}`

---

### Alpha#164

**Formula**: `-1 * (close / sma(close, 20) - 1) / stddev(close / sma(close, 20), 20)`

**Interpretation**: Negative z-score of the price-to-SMA ratio. Strong mean reversion: sells when price is extended above average, buys when below.

**Params**: `{"sma_window": 20, "std_window": 20}`

---

### Alpha#167

**Formula**: `sum(where(delta(close, 1) > 0, delta(close, 1), 0), 14) / sum(where(delta(close, 1) > 0, delta(close, 1), -1 * delta(close, 1)), 14) - 0.5`

**Interpretation**: RSI-like ratio of up-moves to total moves over 14 days, centered at zero. Direct RSI mean-reversion signal.

**Params**: `{"window": 14}`

## Data Requirements

- **Data type**: Daily OHLCV (Open, High, Low, Close, Volume)
- **Source**: yfinance (via `yf.download()`)
- **Lookback period**: Approximately 30 trading days of history required for the longest rolling windows (Alpha#067 uses a 24-day window; combined with smoothing/delta operations, ~30 days ensures all alphas are fully warmed up).
- **Minimum data**: At least 30 rows of daily OHLCV data before the first valid signal.

## Implementation Notes

The alpha formulas use a compact operator notation. The following table maps each operator to its pandas/numpy equivalent:

| Operator | Pandas/Numpy Equivalent | Description |
|----------|------------------------|-------------|
| `delay(x, d)` | `x.shift(d)` | Lagged value, d periods ago |
| `delta(x, d)` | `x.diff(d)` | Difference: x - delay(x, d) |
| `sma(x, d)` | `x.rolling(d).mean()` | Simple moving average over d periods |
| `stddev(x, d)` | `x.rolling(d).std()` | Rolling standard deviation over d periods |
| `ts_min(x, d)` | `x.rolling(d).min()` | Rolling minimum over d periods |
| `ts_max(x, d)` | `x.rolling(d).max()` | Rolling maximum over d periods |
| `sum(x, d)` | `x.rolling(d).sum()` | Rolling sum over d periods |
| `where(cond, a, b)` | `np.where(cond, a, b)` | Conditional: a if cond else b |
| `sign(x)` | `np.sign(x)` | Sign function: -1, 0, or +1 |
| `abs(x)` | `x.abs()` or `np.abs(x)` | Absolute value |

All operators assume a pandas Series as input and return a pandas Series of the same length. NaN values from rolling window warm-up periods should be forward-filled or dropped before signal generation.

## Risk Considerations

- **Trending market failure**: Mean-reversion strategies systematically lose money in strong trending markets. When SPY enters a sustained bull or bear trend, these alphas will generate counter-trend signals that accumulate losses. Consider pairing with a trend filter (e.g., price above/below 200-day SMA) to disable mean-reversion signals during strong trends.
- **Extended overbought/oversold conditions**: Signals can remain in overbought or oversold territory for extended periods. A stock at z-score +3 can go to +5 before reverting. The alphas do not have built-in stop-losses at the formula level -- the pipeline's stop-loss mechanism provides this protection.
- **Stationarity assumption**: Z-score normalization (used by Alpha#063, #086, #112, #164) assumes that the mean and standard deviation of price returns are stationary over the lookback window. This assumption breaks down during regime changes (e.g., volatility spikes, structural breaks), leading to miscalibrated signals.
- **Parameter sensitivity**: Rolling window lengths (10, 12, 14, 20, 24 days) were chosen from the original paper and may not be optimal for SPY specifically. The optimize stage of the pipeline can tune these.
- **Transaction costs**: Daily rebalancing generates significant turnover. With 13 alphas, some may flip signals frequently, increasing trading costs. Consider signal smoothing or minimum holding period constraints.
