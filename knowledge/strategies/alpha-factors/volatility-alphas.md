# Volatility Alpha Factors

## Overview

A collection of 13 formulaic alpha factors focused on **volatility patterns** -- signals derived from price dispersion, range dynamics, and volatility regime changes. These alphas exploit mean-reverting volatility, vol-of-vol effects, and range-based measures to capture opportunities when volatility expands, compresses, or shifts directionally. They range from simple normalized range measures to composite volatility-acceleration indicators, all operating on single-ticker daily OHLCV data.

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

### Alpha#004

- **Formula**: `-1 * ts_rank(low, 9)`
- **Interpretation**: Negative time-series rank of today's low over 9 days. Low when today's low is at the top of its range -- sells strength in lows, buys weakness.
- **Params**: `{"window": 9}`

### Alpha#076

- **Formula**: `stddev(delta(close, 1) / delay(close, 1), 20) - sma(abs(delta(close, 1) / delay(close, 1)), 20)`
- **Interpretation**: Volatility (stddev of returns) minus average absolute return. Positive when return distribution is fat-tailed relative to mean movement.
- **Params**: `{"window": 20}`

### Alpha#097

- **Formula**: `stddev(delta(close, 1), 5) / sma(abs(delta(close, 1)), 5) - 1`
- **Interpretation**: Ratio of return volatility to average absolute return, minus 1. Measures kurtosis-like excess dispersion in recent returns.
- **Params**: `{"window": 5}`

### Alpha#100

- **Formula**: `-1 * stddev(close, 5) / sma(close, 5)`
- **Interpretation**: Negative coefficient of variation over 5 days. Bearish when volatility is high relative to price level. Favors low-volatility regimes.
- **Params**: `{"window": 5}`

### Alpha#109

- **Formula**: `sma(high - low, 10) / sma(high - low, 50) - 1`
- **Interpretation**: Short-term average range relative to longer-term. Positive when recent ranges are wider than usual -- volatility expansion.
- **Params**: `{"fast_window": 10, "slow_window": 50}`

### Alpha#127

- **Formula**: `(close - ts_max(close, 12)) / ts_max(close, 12) + sma(delta(close, 1) / close, 5)`
- **Interpretation**: Distance from 12-day high plus smoothed daily returns. Combination of drawdown depth and recovery momentum.
- **Params**: `{"max_window": 12, "return_sma": 5}`

### Alpha#158

- **Formula**: `sma(high - low, 5) / close`
- **Interpretation**: Normalized 5-day average true range. Raw measure of price volatility as fraction of price.
- **Params**: `{"window": 5}`

### Alpha#160

- **Formula**: `sma(where(close > delay(close, 1), stddev(close, 20), 0), 10)`
- **Interpretation**: Average volatility on up-days over 10 days. High when the stock is volatile on up days -- potentially unstable rallies.
- **Params**: `{"std_window": 20, "sma_window": 10}`

### Alpha#161

- **Formula**: `sma(ts_max(high, 10) - ts_min(low, 10), 5) / close`
- **Interpretation**: Smoothed 10-day price range normalized by current close. ATR-like measure of normalized volatility.
- **Params**: `{"range_window": 10, "smooth_window": 5}`

### Alpha#174

- **Formula**: `stddev(delta(close, 1) / delay(close, 1), 20) / stddev(delta(close, 1) / delay(close, 1), 5) - 1`
- **Interpretation**: Ratio of long-term to short-term return volatility. Positive when recent vol is lower than historical -- vol compression (breakout setup).
- **Params**: `{"long_window": 20, "short_window": 5}`

### Alpha#175

- **Formula**: `sma(abs(high - delay(close, 1)) - abs(low - delay(close, 1)), 10)`
- **Interpretation**: Average directional gap tendency. Positive when highs gap up more than lows gap down -- bullish volatility bias.
- **Params**: `{"window": 10}`

### Alpha#188

- **Formula**: `(high - low) / sma(high - low, 20) - 1`
- **Interpretation**: Today's range relative to average range. Positive on range expansion days -- potential breakout or trend day.
- **Params**: `{"window": 20}`

### Alpha#189

- **Formula**: `sma(abs(delta(close, 1)), 5) / sma(abs(delta(close, 1)), 20) - 1`
- **Interpretation**: Short-term average absolute return relative to longer-term. Volatility acceleration indicator -- positive when recent moves are bigger than usual.
- **Params**: `{"fast_window": 5, "slow_window": 20}`

## Data Requirements

- **Asset Classes**: US equity ETF (SPY)
- **Resolution**: Daily OHLCV bars
- **Data Source**: yfinance (with local Parquet cache when needed)
- **Lookback Period**: Minimum 30 trading days for warmup (longest window is 50 days in Alpha#109, plus buffer for nested operations)
- **Fields Used**: `open`, `high`, `low`, `close`, `volume`

## Implementation Notes

All alpha formulas use a small set of time-series operators. The table below maps each operator to its pandas/numpy equivalent for implementation in the `backtesting.py` framework:

| Operator | Pandas / NumPy Equivalent |
|----------|--------------------------|
| `delay(x, d)` | `x.shift(d)` |
| `delta(x, d)` | `x.diff(d)` |
| `sma(x, d)` | `x.rolling(d).mean()` |
| `stddev(x, d)` | `x.rolling(d).std()` |
| `ts_rank(x, d)` | `x.rolling(d).apply(lambda s: s.rank().iloc[-1] / len(s))` |
| `ts_max(x, d)` | `x.rolling(d).max()` |
| `ts_min(x, d)` | `x.rolling(d).min()` |
| `where(cond, x, y)` | `np.where(cond, x, y)` or `pd.Series(np.where(cond, x, y), index=x.index)` |
| `abs(x)` | `np.abs(x)` or `x.abs()` |
| `sign(x)` | `np.sign(x)` |

Each alpha should be implemented as a function that takes a pandas DataFrame with columns `['Open', 'High', 'Low', 'Close', 'Volume']` and returns a pandas Series of signal values. The `backtesting.py` strategy class then converts the signal to position sizing using the threshold rule (alpha > 0 --> LONG at 95% equity).

Division by zero should be guarded with `+ 1e-8` in denominators where range or return differences could be zero (e.g., `sma(high - low, d)` could theoretically be zero on perfectly flat days).

## Risk Considerations

- **Volatility regime transitions**: Volatility signals can whipsaw during transitions between low-vol and high-vol regimes. A strategy that profits from mean-reverting volatility will suffer when volatility shifts to a persistently higher (or lower) level, generating repeated false signals before adapting.
- **Crisis-period breakdown**: Mean-reverting volatility assumptions may not hold during crisis periods (e.g., 2008, 2020 COVID crash). In these environments, volatility can trend upward for extended periods, and alphas that short high volatility will accumulate losses.
- **Gap risk**: ATR-like and range-based measures (Alpha#158, Alpha#161, Alpha#188) capture intraday price ranges but may not adequately capture overnight gap risk. Large gap moves can trigger stop-losses before the alpha signal has a chance to react.
- **Alpha decay**: These formulas are publicly documented (Kakushadze, 2015) and widely known in the quantitative trading community. Signal strength may degrade over time as more participants trade on the same signals.
- **Transaction costs from daily rebalancing**: Daily signal recomputation means frequent position changes. Each flip between LONG and FLAT incurs bid-ask spread and potential slippage, which can erode returns -- especially for volatility alphas that oscillate near zero during calm markets.

## Related Strategies

- [Momentum & Price Alphas](momentum-price-alphas.md) -- complementary alpha theme
- [Mean Reversion & RSI Alphas](mean-reversion-rsi-alphas.md) -- related mean-reversion signals

## Source

- Kakushadze, Z. (2015). "101 Formulaic Alphas." arXiv:1601.00991
