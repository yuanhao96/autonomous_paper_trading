# Volume-Price Alpha Factors

## Overview

A collection of 25 formulaic alpha factors focused on **volume-price relationships** -- signals derived from the interaction between trading volume and price movements. Volume confirms or denies price trends: strong moves on high volume carry more conviction, while price changes on thin volume may signal fakeouts or exhaustion. These alphas exploit divergences, confirmations, and regime shifts in the volume-price dynamic, all operating on single-ticker daily OHLCV data.

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

### Alpha#005

- **Formula**: `-1 * ts_max(correlation(ts_rank(volume, 5), ts_rank(close, 5), 5), 3)`
- **Interpretation**: Negative peak correlation between volume rank and price rank over recent days. Signals divergence when volume and price decorrelate.
- **Params**: `{"rank_window": 5, "corr_window": 5, "max_window": 3}`

### Alpha#009

- **Formula**: `where(ts_min(delta(close, 1), 5) > 0, delta(close, 1), where(ts_max(delta(close, 1), 5) < 0, delta(close, 1), -1 * delta(close, 1)))`
- **Interpretation**: If all recent daily changes are positive (uptrend), follow momentum. If all negative (downtrend), follow. Otherwise, reverse. Trend vs reversal conditional.
- **Params**: `{"window": 5}`

### Alpha#011

- **Formula**: `(close - low - (high - close)) / (high - low + 1e-8) * volume`
- **Interpretation**: Williams %R-like measure weighted by volume. Measures where close sits in daily range, amplified by volume.
- **Params**: `{}`

### Alpha#029

- **Formula**: `log(sum(where(delta(close, 1) / delay(close, 1) > 0, volume * delta(close, 1) / delay(close, 1), 0), 5) + 1) - log(sum(where(delta(close, 1) / delay(close, 1) < 0, -1 * volume * delta(close, 1) / delay(close, 1), 0), 5) + 1)`
- **Interpretation**: Log ratio of volume-weighted up-moves to volume-weighted down-moves over 5 days. OBV-style money flow indicator.
- **Params**: `{"window": 5}`

### Alpha#040

- **Formula**: `-1 * stddev(high, 10) * correlation(high, volume, 10)`
- **Interpretation**: Negative product of high-price volatility and high-volume correlation. Bearish when highs are volatile and correlated with volume.
- **Params**: `{"window": 10}`

### Alpha#043

- **Formula**: `volume / sma(volume, 20) * delta(close, 1)`
- **Interpretation**: Daily price change scaled by relative volume. Large moves on high relative volume get amplified -- volume-confirmed momentum.
- **Params**: `{"vol_sma": 20}`

### Alpha#060

- **Formula**: `-1 * (close - sma(close, 10)) * (volume / sma(volume, 20))`
- **Interpretation**: Deviation from price SMA, scaled by relative volume. Negative sign = mean reversion on high-volume deviations.
- **Params**: `{"price_sma": 10, "vol_sma": 20}`

### Alpha#068

- **Formula**: `(volume / sma(volume, 15)) * delta(close, 1) * (high - low) / close`
- **Interpretation**: Daily return weighted by relative volume and normalized daily range. Triple confirmation: volume + momentum + range expansion.
- **Params**: `{"vol_sma": 15}`

### Alpha#080

- **Formula**: `delta(volume, 5) / delay(volume, 5) * (-1 * delta(close, 5) / delay(close, 5))`
- **Interpretation**: Volume change rate times negative price change rate. Positive when volume rises but price falls (accumulation) or volume falls and price rises.
- **Params**: `{"window": 5}`

### Alpha#081

- **Formula**: `sma(volume, 10) / volume * (delta(close, 2) / delay(close, 2))`
- **Interpretation**: 2-day return inversely scaled by relative volume. Emphasizes price moves on low volume -- potential fakeout or mean-reversion signal.
- **Params**: `{"vol_sma": 10, "return_window": 2}`

### Alpha#084

- **Formula**: `sign(delta(close, 1)) * sign(delta(volume, 1)) * delta(close, 1)`
- **Interpretation**: Daily price change confirmed by volume direction. Zero when volume moves opposite to price.
- **Params**: `{}`

### Alpha#085

- **Formula**: `ts_rank(volume, 20) * ts_rank(delta(close, 2), 15)`
- **Interpretation**: Product of volume rank and return rank. High when both volume and recent returns are relatively high -- trend confirmation.
- **Params**: `{"vol_rank_window": 20, "return_rank_window": 15}`

### Alpha#094

- **Formula**: `where(delta(close, 1) > 0, volume, -1 * volume) * delta(close, 1) / close`
- **Interpretation**: Signed volume times daily return, normalized by price. Positive on up days with volume, negative on down days.
- **Params**: `{}`

### Alpha#102

- **Formula**: `sma(volume * abs(delta(close, 1)), 10) / (sma(volume, 10) * sma(abs(delta(close, 1)), 10) + 1e-8) - 1`
- **Interpretation**: Ratio of avg(volume x |return|) to avg(volume) x avg(|return|). Measures co-movement between volume and absolute returns -- positive when volume clusters on big-move days.
- **Params**: `{"window": 10}`

### Alpha#111

- **Formula**: `sma(volume * (close - low - high + close) / (high - low + 1e-8), 11) - sma(volume * (close - low - high + close) / (high - low + 1e-8), 20)`
- **Interpretation**: Short vs long SMA of Chaikin-like Accumulation/Distribution. Crossover signal -- positive when recent accumulation exceeds longer-term.
- **Params**: `{"fast_window": 11, "slow_window": 20}`

### Alpha#117

- **Formula**: `ts_rank(volume, 32) * (1 - ts_rank(close + high - low, 16)) * (1 - ts_rank(delta(close, 1) / delay(close, 1), 32))`
- **Interpretation**: High volume rank x low price-range rank x low return rank. Signals when volume is high but price action is subdued -- potential breakout setup.
- **Params**: `{"vol_rank": 32, "price_rank": 16, "ret_rank": 32}`

### Alpha#134

- **Formula**: `delta(close, 12) / delay(close, 12) * volume / sma(volume, 20)`
- **Interpretation**: 12-day return scaled by relative volume. Medium-term momentum confirmed by above-average volume.
- **Params**: `{"return_window": 12, "vol_sma": 20}`

### Alpha#139

- **Formula**: `-1 * correlation(open, volume, 10) * delta(close, 1)`
- **Interpretation**: Daily return weighted by negative open-volume correlation. Contrarian when opens and volume are positively correlated.
- **Params**: `{"corr_window": 10}`

### Alpha#145

- **Formula**: `sma(volume, 5) / sma(volume, 20) - 1`
- **Interpretation**: Relative volume ratio (5-day avg vs 20-day avg). Positive when recent volume exceeds historical -- volume surge indicator.
- **Params**: `{"fast_window": 5, "slow_window": 20}`

### Alpha#150

- **Formula**: `(close * volume - delay(close, 1) * delay(volume, 1)) / (delay(close, 1) * delay(volume, 1) + 1e-8)`
- **Interpretation**: Rate of change of close x volume product. Captures joint price-volume momentum.
- **Params**: `{}`

### Alpha#155

- **Formula**: `sma(volume, 13) * sma(delta(close, 1) / delay(close, 1), 13) - delay(sma(volume, 13) * sma(delta(close, 1) / delay(close, 1), 13), 1)`
- **Interpretation**: Daily change in the product of smoothed volume and smoothed returns. Volume-momentum acceleration.
- **Params**: `{"window": 13}`

### Alpha#168

- **Formula**: `-1 * volume / sma(volume, 20)`
- **Interpretation**: Negative relative volume. Contrarian signal -- bearish when volume spikes (potential panic/euphoria).
- **Params**: `{"window": 20}`

### Alpha#178

- **Formula**: `(volume / sma(volume, 20) - 1) * (1 - (close - low) / (high - low + 1e-8))`
- **Interpretation**: Relative volume surge times proximity to daily low. Positive when volume is high AND price closed near the low -- capitulation/selling climax buy signal.
- **Params**: `{"vol_sma": 20}`

### Alpha#180

- **Formula**: `delta(volume, 3) / delay(volume, 3) - delta(close, 3) / delay(close, 3)`
- **Interpretation**: Volume change rate minus price change rate over 3 days. Positive when volume is increasing faster than price -- accumulation signal.
- **Params**: `{"window": 3}`

### Alpha#191

- **Formula**: `correlation(sma(volume, 20), low, 5) + (high + low) / 2 - close`
- **Interpretation**: Correlation of smoothed volume with lows plus midpoint-close deviation. Multi-factor: volume-low relationship plus intraday positioning.
- **Params**: `{"vol_sma": 20, "corr_window": 5}`

## Data Requirements

- **Asset Classes**: US equity ETF (SPY)
- **Resolution**: Daily OHLCV bars
- **Data Source**: yfinance (with local Parquet cache when needed)
- **Lookback Period**: Minimum 30 trading days for warmup (longest window is 32 days in Alpha#117, plus buffer for nested operations)
- **Fields Used**: `open`, `high`, `low`, `close`, `volume`

## Implementation Notes

All alpha formulas use a small set of time-series operators. The table below maps each operator to its pandas/numpy equivalent for implementation in the `backtesting.py` framework:

| Operator | Pandas / NumPy Equivalent |
|----------|--------------------------|
| `delay(x, d)` | `x.shift(d)` |
| `delta(x, d)` | `x.diff(d)` |
| `sma(x, d)` | `x.rolling(d).mean()` |
| `sum(x, d)` | `x.rolling(d).sum()` |
| `correlation(x, y, d)` | `x.rolling(d).corr(y)` |
| `stddev(x, d)` | `x.rolling(d).std()` |
| `ts_rank(x, d)` | `x.rolling(d).apply(lambda s: s.rank().iloc[-1] / len(s))` |
| `ts_min(x, d)` | `x.rolling(d).min()` |
| `ts_max(x, d)` | `x.rolling(d).max()` |
| `sign(x)` | `np.sign(x)` |
| `log(x)` | `np.log(x)` |
| `abs(x)` | `np.abs(x)` |
| `where(cond, x, y)` | `np.where(cond, x, y)` |

Each alpha should be implemented as a function that takes a pandas DataFrame with columns `['Open', 'High', 'Low', 'Close', 'Volume']` and returns a pandas Series of signal values. The `backtesting.py` strategy class then converts the signal to position sizing using the threshold rule (alpha > 0 --> LONG at 95% equity).

Division by zero should be guarded with `+ 1e-8` in denominators where high-low differences, close-to-close differences, or volume values could be zero.

For volume-price alphas specifically, ensure that `Volume` is cast to float before arithmetic operations, as yfinance may return integer volume data which can cause silent overflow in products like `volume * delta(close, 1)`.

## Risk Considerations

- **Volume-price signals are noisier in low-liquidity periods**: During holidays, early closes, or market disruptions, volume data can be anomalous. Alphas that depend on relative volume ratios (e.g., Alpha#043, Alpha#145, Alpha#168) may produce spurious signals when volume is abnormally low.
- **SPY generally has consistent volume so some volume signals may be less discriminating**: SPY is one of the most liquid instruments globally, with relatively stable daily volume. Volume-based signals that rely on significant volume variation (e.g., Alpha#117, Alpha#178) may generate weaker signals on SPY compared to less liquid securities where volume fluctuations are more pronounced.
- **Correlation measures require sufficient lookback for stability**: Alphas using `correlation()` (e.g., Alpha#005, Alpha#040, Alpha#139, Alpha#191) need enough data points within the rolling window to produce statistically meaningful values. Short correlation windows (5 days) are noisy and can flip sign frequently, leading to excessive trading.
- **Overfitting to historical patterns**: With 25 alpha variants on a single ticker, there is significant risk of selecting alphas that performed well historically by chance. Out-of-sample validation and walk-forward testing are essential.
- **Alpha decay**: These formulas are publicly documented (Kakushadze, 2015) and widely known in the quantitative trading community. Signal strength may degrade over time as more participants trade on the same signals, compressing the available edge.
- **Transaction costs from daily rebalancing**: Daily signal recomputation means frequent position changes. Each flip between LONG and FLAT incurs bid-ask spread and potential slippage, which can erode returns -- especially for lower-conviction alphas that oscillate around zero.

## Related Strategies

- [Momentum & Price Alphas](momentum-price-alphas.md) -- complementary price-only momentum signals
- [Mean Reversion & RSI Alphas](mean-reversion-rsi-alphas.md) -- complementary mean-reversion alpha theme

## Source

- Kakushadze, Z. (2015). "101 Formulaic Alphas." arXiv:1601.00991
