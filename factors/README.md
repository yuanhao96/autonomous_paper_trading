# Alpha Factors

A unified collection of individual alpha factor formulas for the stratgen pipeline. Each `.md` file contains exactly one factor with a standardized format.

## Signal Rule

All factors produce a continuous signal value:
- **alpha > 0** → LONG (buy/hold SPY at 95% equity)
- **alpha ≤ 0** → FLAT (no position)
- **Stop-loss**: 2% trailing stop on all positions
- **Rebalancing**: Daily

## Factor Doc Format

```markdown
# WQ-NNN: Short Description

## Formula
-1 * delta(log(close), 2)

## Interpretation
One or two sentences explaining what the formula captures.

## Parameters
| Param | Default | Range |
|-------|---------|-------|
| lookback | 2 | [1, 10] |

## Category
momentum

## Source
WorldQuant Alpha#NNN (Kakushadze 2015)
```

## Operator Reference

These operators appear in alpha formulas. All operate on pandas Series.

| Operator | Meaning | Pandas Equivalent |
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
| `abs(x)` | Absolute value | `np.abs(x)` |
| `where(cond, a, b)` | Conditional | `np.where(cond, a, b)` |
| `returns` | Daily close-to-close return | `close.pct_change()` |
| `SignedPower(x, a)` | sign(x) × \|x\|^a | `np.sign(x) * np.abs(x)**a` |

## Category Index

| Category | Dir | WQ Count | Trad Count | Total | Description |
|----------|-----|----------|------------|-------|-------------|
| Momentum | `momentum/` | 30 | 4 | 34 | Price momentum, returns, trend acceleration |
| Mean Reversion | `mean_reversion/` | 13 | 2 | 15 | Z-scores, RSI-like, oscillators |
| Volume-Price | `volume_price/` | 25 | 0 | 25 | Volume-price divergence, confirmation |
| Volatility | `volatility/` | 13 | 0 | 13 | Range, dispersion, vol regime |
| Trend | `trend/` | 11 | 1 | 12 | Directional, ADX-like, persistence |
| Price Channel | `price_channel/` | 11 | 2 | 13 | Donchian, breakout, support/resistance |
| Composite | `composite/` | 3 | 0 | 3 | Multi-factor blends |

**Total**: 115 factors (106 WorldQuant + 9 traditional)

## Naming Convention

- WorldQuant factors: `wq_NNN.md` (alpha number from Kakushadze 2015)
- Traditional strategy factors: `trad_<name>.md` (converted from knowledge/ docs)

## Source

Kakushadze, Z. (2015). "101 Formulaic Alphas." *Wilmott Magazine*, 2016(84), 72–80. arXiv:1601.00991
