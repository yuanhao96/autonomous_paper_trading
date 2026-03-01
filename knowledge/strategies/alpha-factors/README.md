# WorldQuant Alpha Factors

## Overview

A curated set of **106 formulaic alpha factors** adapted from the WorldQuant "101 Formulaic Alphas" research (Kakushadze, 2015) and extended alpha sets. Each alpha is a mathematical formula that produces a trading signal from daily OHLCV data.

**Original source**: Kakushadze, Z. (2015). "101 Formulaic Alphas." *Wilmott Magazine*, 2016(84), 72–80. arXiv:1601.00991

## Filtering Criteria

The original set contains 191 alphas. Only **106 are compatible** with our single-ticker daily OHLCV pipeline (`backtesting.py` + `yfinance`). The following were excluded:

| Reason | Count | Examples |
|--------|-------|---------|
| `RANK` (cross-sectional ranking) | ~50 | Requires universe of stocks to rank across |
| `VWAP` (volume-weighted avg price) | ~25 | Not available in standard OHLCV feeds |
| `AMOUNT` (dollar volume) | ~15 | Requires intraday trade data |
| `IndNeutralize` (industry neutralization) | ~8 | Requires sector/industry classification |
| Benchmark returns / `cap` | ~5 | Requires market-cap or benchmark data |

## Signal Interpretation

All alphas produce a continuous signal value. For our pipeline:
- **alpha > 0** → LONG signal
- **alpha ≤ 0** → FLAT (no position)

## Operator Reference

These operators appear throughout the alpha formulas:

| Operator | Meaning | Pandas equivalent |
|----------|---------|-------------------|
| `delay(x, d)` | Value of x, d days ago | `x.shift(d)` |
| `delta(x, d)` | x − delay(x, d) | `x.diff(d)` |
| `correlation(x, y, d)` | Rolling correlation over d days | `x.rolling(d).corr(y)` |
| `covariance(x, y, d)` | Rolling covariance over d days | `x.rolling(d).cov(y)` |
| `ts_min(x, d)` | Rolling minimum over d days | `x.rolling(d).min()` |
| `ts_max(x, d)` | Rolling maximum over d days | `x.rolling(d).max()` |
| `ts_rank(x, d)` | Percentile rank over d days | `x.rolling(d).apply(lambda s: s.rank().iloc[-1]/len(s))` |
| `ts_argmax(x, d)` | Days since max in last d days | `x.rolling(d).apply(lambda s: s.argmax())` |
| `ts_argmin(x, d)` | Days since min in last d days | `x.rolling(d).apply(lambda s: s.argmin())` |
| `stddev(x, d)` | Rolling standard deviation | `x.rolling(d).std()` |
| `sum(x, d)` | Rolling sum over d days | `x.rolling(d).sum()` |
| `product(x, d)` | Rolling product over d days | `x.rolling(d).apply(np.prod)` |
| `sma(x, d)` | Simple moving average | `x.rolling(d).mean()` |
| `decay_linear(x, d)` | Linearly-weighted moving average | `x.rolling(d).apply(lambda s: np.dot(s, np.arange(1,d+1))/np.arange(1,d+1).sum())` |
| `sign(x)` | Sign function (−1, 0, +1) | `np.sign(x)` |
| `log(x)` | Natural logarithm | `np.log(x)` |
| `returns` | Daily close-to-close return | `close.pct_change()` |
| `SignedPower(x, a)` | sign(x) × |x|^a | `np.sign(x) * np.abs(x)**a` |

## Index

| # | Theme | Alphas | File |
|---|-------|--------|------|
| 1 | Momentum & Price | 30 | [momentum-price-alphas.md](momentum-price-alphas.md) |
| 2 | Mean Reversion & RSI | 13 | [mean-reversion-rsi-alphas.md](mean-reversion-rsi-alphas.md) |
| 3 | Volume-Price | 25 | [volume-price-alphas.md](volume-price-alphas.md) |
| 4 | Volatility | 13 | [volatility-alphas.md](volatility-alphas.md) |
| 5 | Trend & Directional | 11 | [trend-directional-alphas.md](trend-directional-alphas.md) |
| 6 | Price Channels | 11 | [price-channel-alphas.md](price-channel-alphas.md) |
| 7 | Composite | 3 | [composite-alphas.md](composite-alphas.md) |

### Excluded (Future Reference)

| # | Theme | Alphas | File |
|---|-------|--------|------|
| — | Multi-Asset (excluded) | 85 | [excluded-multi-asset-alphas.md](excluded-multi-asset-alphas.md) |

The excluded doc lists all 85 incompatible alphas with their original formulas, incompatible operations, and a migration path for when the pipeline supports multi-asset strategies.
