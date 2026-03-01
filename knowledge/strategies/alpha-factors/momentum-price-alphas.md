# Momentum & Price Alphas

## Overview

A collection of 30 formulaic alpha factors focused on **price momentum** — signals derived primarily from close, open, high, and low prices and their temporal dynamics. These alphas capture short-to-medium-term trends, mean-reversion within momentum regimes, momentum acceleration/deceleration, and smoothed trend indicators. They range from simple percentage returns to multi-layered smoothed composites, all operating on single-ticker daily OHLCV data.

## Academic Reference

- **Paper**: Kakushadze, Z. (2015). "101 Formulaic Alphas." *Wilmott Magazine*, 2016(84), 72-80.
- **Link**: https://arxiv.org/abs/1601.00991

## Strategy Logic

### Universe Selection

- **Ticker**: SPY (S&P 500 ETF)
- **Rationale**: Highly liquid, low spread, representative of broad US equity market.

### Signal Generation

Each alpha formula produces a continuous numeric value from daily OHLCV data. The trading signal is:

- **alpha > 0** --> LONG (buy/hold SPY)
- **alpha <= 0** --> FLAT (no position / sell)

### Entry / Exit Rules

- **Entry**: When alpha value crosses from <= 0 to > 0, enter a LONG position at next open.
- **Exit**: When alpha value crosses from > 0 to <= 0, exit position at next open.
- **Stop-loss**: 2% trailing stop-loss on all positions.

### Portfolio Construction

- **Position size**: 95% of equity deployed when LONG.
- **Cash reserve**: 5% held as buffer for slippage and fees.

### Rebalancing Schedule

- **Frequency**: Daily at market close (signals computed end-of-day, orders execute next open).

## Alpha Formulas

### Alpha#002

- **Formula**: `-1 * delta(log(close), 2)`
- **Interpretation**: Negative 2-day log return -- contrarian short-term reversal on price momentum.
- **Params**: `{"lookback": 2}`

### Alpha#003

- **Formula**: `-1 * correlation(open, volume, 10)`
- **Interpretation**: Negative correlation between opening price and volume over 10 days. When opens rise with falling volume, momentum is suspect.
- **Params**: `{"corr_window": 10}`

### Alpha#014

- **Formula**: `-1 * delta(close, 3) * correlation(close, volume, 10)`
- **Interpretation**: 3-day price change weighted by price-volume correlation. Signals momentum confirmed or denied by volume relationship.
- **Params**: `{"delta_days": 3, "corr_window": 10}`

### Alpha#015

- **Formula**: `-1 * sum(delta(close, 1) * correlation(close, volume, 10), 3) / sum(correlation(close, volume, 10), 3)`
- **Interpretation**: Volume-correlation-weighted average of daily returns over 3 days.
- **Params**: `{"return_window": 3, "corr_window": 10}`

### Alpha#018

- **Formula**: `-1 * stddev(abs(close - open), 5) / (close - open) + delta(close, 10) / close`
- **Interpretation**: Combines intraday range volatility (normalized) with 10-day price momentum.
- **Params**: `{"vol_window": 5, "mom_window": 10}`

### Alpha#019

- **Formula**: `sign(delta(close, 7)) * (-1 * delta(close, 7))`
- **Interpretation**: Negative absolute 7-day price change -- penalizes large moves in either direction, favoring stability.
- **Params**: `{"lookback": 7}`

### Alpha#020

- **Formula**: `-1 * sign(close - delay(close, 7)) * (close - delay(close, 7))`
- **Interpretation**: Same as Alpha#019 with explicit sign decomposition. Negative absolute momentum.
- **Params**: `{"lookback": 7}`

### Alpha#024

- **Formula**: `delta(close, 5) + (delay(close, 5) - delay(close, 10)) / 5`
- **Interpretation**: 5-day price change plus average daily change over days 5-10. Combines short and medium momentum.
- **Params**: `{"short_window": 5, "long_window": 10}`

### Alpha#027

- **Formula**: `sma(close, 6) / close - 1`
- **Interpretation**: Deviation of price from its 6-day moving average. Positive when price is below average (reversion signal within momentum context).
- **Params**: `{"sma_window": 6}`

### Alpha#031

- **Formula**: `(close - sma(close, 12)) / sma(close, 12) + decay_linear(delta(close, 2) / delay(close, 2), 5)`
- **Interpretation**: Price deviation from 12-day SMA plus linearly-weighted 2-day returns.
- **Params**: `{"sma_window": 12, "return_lookback": 2, "decay_window": 5}`

### Alpha#034

- **Formula**: `(sma(close, 2) / sma(close, 5)) - 1`
- **Interpretation**: Ratio of short-term to medium-term average -- captures accelerating momentum.
- **Params**: `{"fast_window": 2, "slow_window": 5}`

### Alpha#046

- **Formula**: `(delay(close, 20) - delay(close, 10)) / 10 - delta(close, 10) / 10`
- **Interpretation**: Difference between prior momentum (days 10-20) and recent momentum (last 10 days). Momentum deceleration/acceleration.
- **Params**: `{"lookback_near": 10, "lookback_far": 20}`

### Alpha#053

- **Formula**: `-1 * delta((high - close) / (close - low + 1e-8), 9)`
- **Interpretation**: Change in the high-close to close-low ratio over 9 days. Captures shifts in intraday price positioning.
- **Params**: `{"lookback": 9}`

### Alpha#058

- **Formula**: `delta(close, 5) / delay(close, 5)`
- **Interpretation**: Simple 5-day percentage return. Pure short-term momentum.
- **Params**: `{"lookback": 5}`

### Alpha#059

- **Formula**: `delta(close, 10) / delay(close, 10)`
- **Interpretation**: 10-day percentage return. Medium-term momentum signal.
- **Params**: `{"lookback": 10}`

### Alpha#065

- **Formula**: `sma(delta(close, 1), 6) / delta(close, 1)`
- **Interpretation**: Ratio of average daily change to current daily change. Smoothed momentum relative to spot momentum.
- **Params**: `{"sma_window": 6}`

### Alpha#066

- **Formula**: `(close - sma(close, 6)) / sma(close, 6)`
- **Interpretation**: Price deviation from 6-day mean as percentage. Classic mean-deviation momentum.
- **Params**: `{"sma_window": 6}`

### Alpha#071

- **Formula**: `(close - sma(close, 24)) / sma(close, 24) + decay_linear(ts_rank(close, 16), 4)`
- **Interpretation**: 24-day price deviation plus linearly-decayed time-series rank. Combines trend and rank momentum.
- **Params**: `{"sma_window": 24, "rank_window": 16, "decay_window": 4}`

### Alpha#088

- **Formula**: `sma(delta(close, 1), 20) / sma(abs(delta(close, 1)), 20)`
- **Interpretation**: Average daily return divided by average absolute daily return over 20 days. Directional consistency ratio -- high when moves are consistently one-directional.
- **Params**: `{"window": 20}`

### Alpha#089

- **Formula**: `sma(close, 5) - sma(close, 20) + decay_linear(delta(close, 2), 8)`
- **Interpretation**: SMA crossover (5 vs 20) combined with linearly-decayed 2-day changes. Trend plus momentum.
- **Params**: `{"fast_window": 5, "slow_window": 20, "delta_days": 2, "decay_window": 8}`

### Alpha#098

- **Formula**: `delta(sma(close, 10), 5) / delay(sma(close, 10), 5)`
- **Interpretation**: 5-day rate of change of the 10-day SMA. Smoothed momentum acceleration.
- **Params**: `{"sma_window": 10, "roc_window": 5}`

### Alpha#106

- **Formula**: `close / delay(close, 20) - 1`
- **Interpretation**: 20-day simple return. Medium-term momentum.
- **Params**: `{"lookback": 20}`

### Alpha#122

- **Formula**: `sma(sma(sma(log(close), 3), 3), 3)`
- **Interpretation**: Triple-smoothed log price (like TRIX base). Very smooth trend indicator.
- **Params**: `{"smooth_window": 3}`

### Alpha#135

- **Formula**: `delta(close, 5) / delay(close, 5) - delta(close, 20) / delay(close, 20)`
- **Interpretation**: 5-day return minus 20-day return. Short-term momentum relative to longer-term -- momentum acceleration.
- **Params**: `{"short_window": 5, "long_window": 20}`

### Alpha#146

- **Formula**: `sma(delta(close, 1) / delay(close, 1), 5)`
- **Interpretation**: 5-day average of daily returns. Smoothed short-term momentum.
- **Params**: `{"window": 5}`

### Alpha#151

- **Formula**: `close - sma(close, 20)`
- **Interpretation**: Price minus 20-day SMA. Classic trend deviation -- positive above the average.
- **Params**: `{"sma_window": 20}`

### Alpha#152

- **Formula**: `sma(delay(sma(delta(close, 1) / delay(close, 1), 12), 1), 5)`
- **Interpretation**: 5-day average of yesterday's 12-day average return. Double-smoothed lagged momentum.
- **Params**: `{"inner_window": 12, "lag": 1, "outer_window": 5}`

### Alpha#153

- **Formula**: `sma(close, 3) - sma(close, 12)`
- **Interpretation**: 3-day vs 12-day SMA difference. Short-term trend crossover signal.
- **Params**: `{"fast_window": 3, "slow_window": 12}`

### Alpha#169

- **Formula**: `sma(delta(close, 1), 10) - sma(delta(close, 1), 5)`
- **Interpretation**: Difference between 10-day and 5-day average daily change. Momentum trend slope.
- **Params**: `{"slow_window": 10, "fast_window": 5}`

### Alpha#173

- **Formula**: `decay_linear(delta(close, 5) / delay(close, 5), 10)`
- **Interpretation**: Linearly-decayed 5-day returns over 10 days. Recent momentum weighted more heavily.
- **Params**: `{"return_window": 5, "decay_window": 10}`

## Data Requirements

- **Asset Classes**: US equity ETF (SPY)
- **Resolution**: Daily OHLCV bars
- **Data Source**: yfinance (with local Parquet cache when needed)
- **Lookback Period**: Minimum 30 trading days for warmup (longest window is 24 days in Alpha#071, plus buffer for nested operations)
- **Fields Used**: `open`, `high`, `low`, `close`, `volume`

## Implementation Notes

All alpha formulas use a small set of time-series operators. The table below maps each operator to its pandas/numpy equivalent for implementation in the `backtesting.py` framework:

| Operator | Pandas / NumPy Equivalent |
|----------|--------------------------|
| `delay(x, d)` | `x.shift(d)` |
| `delta(x, d)` | `x.diff(d)` |
| `sma(x, d)` | `x.rolling(d).mean()` |
| `correlation(x, y, d)` | `x.rolling(d).corr(y)` |
| `stddev(x, d)` | `x.rolling(d).std()` |
| `decay_linear(x, d)` | `x.rolling(d).apply(lambda s: np.dot(s, np.arange(1, d+1)) / np.arange(1, d+1).sum())` |
| `ts_rank(x, d)` | `x.rolling(d).apply(lambda s: s.rank().iloc[-1] / len(s))` |
| `sign(x)` | `np.sign(x)` |
| `log(x)` | `np.log(x)` |

Each alpha should be implemented as a function that takes a pandas DataFrame with columns `['Open', 'High', 'Low', 'Close', 'Volume']` and returns a pandas Series of signal values. The `backtesting.py` strategy class then converts the signal to position sizing using the threshold rule (alpha > 0 --> LONG at 95% equity).

When implementing `decay_linear`, the weights are `[1, 2, ..., d]` (most recent observation gets the highest weight), normalized by dividing by the sum `d*(d+1)/2`.

Division by zero should be guarded with `+ 1e-8` in denominators where close-to-close or close-to-low differences could be zero (see Alpha#053 for an example).

## Risk Considerations

- **Momentum crashes**: Price momentum strategies are vulnerable to sharp reversals during market regime changes (e.g., the 2009 momentum crash). Many of these alphas will simultaneously flip to FLAT during a crash, but exit signals may lag.
- **Overfitting to historical patterns**: With 30 alpha variants on a single ticker, there is significant risk of selecting alphas that performed well historically by chance. Out-of-sample validation and walk-forward testing are essential.
- **Transaction costs from daily rebalancing**: Daily signal recomputation means frequent position changes. Each flip between LONG and FLAT incurs bid-ask spread and potential slippage, which can erode returns -- especially for lower-conviction alphas that oscillate around zero.
- **Alpha decay**: These formulas are publicly documented (Kakushadze, 2015) and widely known in the quantitative trading community. Signal strength may degrade over time as more participants trade on the same signals, compressing the available edge.

## Related Strategies

- [Mean Reversion & RSI Alphas](mean-reversion-rsi-alphas.md) -- complementary alpha theme
- [Volume-Price Alphas](volume-price-alphas.md) -- volume-based signals that can be combined with momentum
- [Trend & Directional Alphas](trend-directional-alphas.md) -- related directional signals

## Source

- Kakushadze, Z. (2015). "101 Formulaic Alphas." arXiv:1601.00991
