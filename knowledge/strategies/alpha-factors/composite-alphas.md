# Composite Alpha Factors

## Overview

Multi-factor combination alphas that blend signals from different categories -- momentum, volatility, volume, and mean reversion -- into a single composite score. These alphas are more complex than single-theme factors and aim to capture multiple market dynamics simultaneously. Derived from the WorldQuant "101 Formulaic Alphas" research.

## Academic Reference

- **Paper**: Kakushadze, Z. (2015). "101 Formulaic Alphas."
- **Journal**: *Wilmott Magazine*, 2016(84), 72–80
- **Link**: https://arxiv.org/abs/1601.00991

## Strategy Logic

### Universe Selection

SPY (S&P 500 ETF). Single-ticker pipeline using daily OHLCV data from yfinance.

### Signal Generation

Each alpha produces a continuous signal value:
- **alpha > 0** → LONG
- **alpha ≤ 0** → FLAT (no position)

### Entry / Exit Rules

- **Entry**: Open a long position when alpha crosses above 0.
- **Exit**: Close position when alpha crosses below 0.
- **Stop-loss**: 2% trailing stop-loss from entry price.

### Portfolio Construction

Single position at 95% of equity. 5% cash reserve for transaction costs.

### Rebalancing Schedule

Daily. Signal recalculated at each bar close.

## Alpha Formulas

### Alpha#055

**Formula**:
```
correlation(close - ts_min(low, 12), sma(volume, 26), 10)
  + delta(close, 3) / delay(close, 3)
  + (close - sma(close, 20)) / stddev(close, 20)
```

**Interpretation**: Three-factor composite:
1. Correlation between channel position (close relative to 12-day low) and smoothed volume -- volume-price channel signal
2. 3-day return -- short-term momentum
3. Z-score deviation from 20-day mean -- mean reversion / trend

Positive when all three components agree bullishly. The correlation term captures whether volume confirms the price's position in its channel, while the return and z-score components add momentum and mean-deviation context.

**Params**: `{"channel_window": 12, "vol_sma": 26, "corr_window": 10, "return_window": 3, "zscore_window": 20}`

---

### Alpha#137

**Formula**:
```
sign(delta(close, 1))
  * (-1 * correlation(high, volume, 10))
  * (1 + sma(high - low, 5) / close)
```

**Interpretation**: Three-factor product:
1. Direction of today's price change (up/down)
2. Negative high-volume correlation -- bearish when highs are correlated with volume (climactic tops)
3. Volatility multiplier (1 + normalized average range)

The sign term sets direction, the correlation term determines conviction (contrarian on high-volume highs), and the volatility multiplier amplifies signals during volatile periods. This alpha effectively says: follow the trend when high-volume action is NOT pushing highs higher (i.e., volume is diverging from highs).

**Params**: `{"corr_window": 10, "range_window": 5}`

---

### Alpha#190

**Formula**:
```
sma(delta(close, 1) / delay(close, 1), 10)
  * (1 - stddev(close, 20) / sma(close, 20))
  * (volume / sma(volume, 20) - 1)
```

**Interpretation**: Three-factor product:
1. Smoothed 10-day average return -- momentum direction
2. Inverse coefficient of variation -- favors low-volatility regimes (quality filter)
3. Relative volume deviation -- amplifies on above-average volume days

Positive when: momentum is positive AND volatility is low AND volume is above average. This is a "quality momentum" signal that only fires when conditions are favorable across multiple dimensions.

**Params**: `{"return_sma": 10, "vol_window": 20, "vol_sma_window": 20}`

## Data Requirements

- **Asset Classes**: US equities (SPY)
- **Resolution**: Daily OHLCV
- **Data Source**: yfinance
- **Lookback Period**: 30-day minimum warmup (longest window is 26 days in Alpha#055)

## Implementation Notes

| Operator | Pandas Equivalent |
|----------|-------------------|
| `delay(x, d)` | `x.shift(d)` |
| `delta(x, d)` | `x.diff(d)` |
| `sma(x, d)` | `x.rolling(d).mean()` |
| `stddev(x, d)` | `x.rolling(d).std()` |
| `correlation(x, y, d)` | `x.rolling(d).corr(y)` |
| `ts_min(x, d)` | `x.rolling(d).min()` |
| `sign(x)` | `np.sign(x)` |
| `log(x)` | `np.log(x)` |
| `abs(x)` | `np.abs(x)` |

**Composite implementation tips**:
- Compute each factor component separately, then combine. This makes debugging easier.
- Guard against division by zero with `+ 1e-8` on denominators.
- Ensure Volume is cast to float before operations: `volume = df['Volume'].astype(float)`.
- Each component may have different scales -- the composite signal is used only for sign (> 0 or ≤ 0), so normalization is not strictly required.

## Risk Considerations

- **Complexity**: Multi-factor alphas are harder to interpret and debug than single-factor ones. When a composite signal fails, it can be difficult to determine which component caused the failure.
- **Overfitting**: Combining multiple factors increases the risk of fitting to noise, especially with short lookback windows.
- **Correlation breakdown**: The interaction between components assumes stable relationships that may break in regime changes.
- **Parameter sensitivity**: More parameters means a larger search space for optimization and greater overfitting risk.
- **Transaction costs**: Daily rebalancing with potentially volatile composite signals may lead to frequent position changes.

## Related Strategies

- [Momentum & Price Alphas](momentum-price-alphas.md)
- [Mean Reversion & RSI Alphas](mean-reversion-rsi-alphas.md)
- [Volume-Price Alphas](volume-price-alphas.md)
- [Volatility Alphas](volatility-alphas.md)
- [Trend & Directional Alphas](trend-directional-alphas.md)
- [Price Channel Alphas](price-channel-alphas.md)

## Source

- Kakushadze, Z. (2015). "101 Formulaic Alphas." *Wilmott Magazine*, 2016(84), 72–80. https://arxiv.org/abs/1601.00991
