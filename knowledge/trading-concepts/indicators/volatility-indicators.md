# Volatility Indicators

## Overview

Volatility indicators measure the degree of price variation over time. High volatility means large price swings; low volatility means small, stable price movements. These indicators are essential for position sizing, stop-loss placement, identifying breakout conditions, and adapting strategy parameters to changing market regimes. Unlike trend indicators, volatility indicators are non-directional — they measure magnitude of movement, not its direction.

## Bollinger Bands

- **Formula:**
  - Middle Band: `SMA(Close, 20)`
  - Upper Band: `SMA(Close, 20) + 2 × σ(Close, 20)`
  - Lower Band: `SMA(Close, 20) - 2 × σ(Close, 20)`
- **Derived Metrics:**
  - Bandwidth: `(Upper - Lower) / Middle` — quantifies band spread
  - %B: `(Price - Lower) / (Upper - Lower)` — locates price within bands (0 = lower band, 1 = upper band)
- **Parameters:** Period (default: 20), Standard deviation multiplier (default: 2)
- **Signals:**
  - Squeeze: Bands narrow significantly, indicating low volatility and a potential breakout.
  - Band Walk: Price persistently hugs the upper or lower band during strong trends — this is NOT a reversal signal.
  - Mean Reversion: Price touching outer bands and reversing toward the middle band in range-bound markets.
- **Use:** Breakout detection via squeeze, mean-reversion entries, dynamic overbought/oversold levels.

## Average True Range (ATR)

- **Formula:**
  - True Range: `max(High - Low, |High - Close_prev|, |Low - Close_prev|)`
  - ATR: `SMA(True Range, 14)` or EMA smoothing variant
- **Parameters:** Period (default: 14)
- **Characteristics:** Non-directional — purely measures volatility magnitude. Accounts for gaps by including the previous close in the true range calculation. Higher ATR = more volatile; lower ATR = less volatile.
- **Signals:** Rising ATR indicates increasing volatility (often accompanies trend starts or panic selling). Falling ATR indicates decreasing volatility (consolidation phases).
- **Use:**
  - Position sizing: `Risk per trade / ATR = number of units`
  - Stop-loss placement: `Entry ± N × ATR` (commonly N = 1.5 to 3.0)
  - Volatility filter: Only trade when ATR is within an acceptable range.

## Keltner Channels

- **Formula:**
  - Middle: `EMA(Close, 20)`
  - Upper: `EMA(Close, 20) + 2 × ATR(10)`
  - Lower: `EMA(Close, 20) - 2 × ATR(10)`
- **Parameters:** EMA period (default: 20), ATR period (default: 10), ATR multiplier (default: 2)
- **Characteristics:** Similar concept to Bollinger Bands but uses ATR instead of standard deviation for the channel width. This produces smoother, more stable bands since ATR is less sensitive to single-bar outliers.
- **Signals:** Price closing outside channels indicates strong momentum. Bollinger Bands fitting inside Keltner Channels is a popular squeeze detection method (TTM Squeeze).
- **Use:** Squeeze setups combined with Bollinger Bands, trend-following channel breakouts, volatility-adjusted support/resistance.

## Normalized ATR (NATR)

- **Formula:** `NATR = (ATR / Close) × 100`
- **Parameters:** ATR period (default: 14)
- **Characteristics:** Expresses ATR as a percentage of the current price. This normalization allows meaningful volatility comparison across different assets regardless of their price level. A $500 stock and a $5 stock can be compared directly.
- **Signals:** Same interpretation as ATR, but on a percentage scale.
- **Use:** Cross-asset volatility comparison, universe filtering (e.g., exclude assets with NATR > 5%), regime detection across portfolios.

## Choppiness Index (CHOP)

- **Formula:** `CHOP = 100 × LOG10(Σ ATR(1, n) / (Highest_High_n - Lowest_Low_n)) / LOG10(n)`
- **Parameters:** Period (default: 14)
- **Characteristics:** Ranges from 0 to 100. Measures whether the market is trending or moving sideways (choppy). Based on the ratio of total ATR movement to the net directional range.
- **Signals:**
  - High values (> 61.8): Market is choppy/consolidating — avoid trend-following strategies.
  - Low values (< 38.2): Market is trending — trend-following strategies should perform well.
- **Use:** Strategy selection filter (trend vs. mean-reversion), regime classification, avoiding false breakouts in choppy markets.

## Donchian Channel

- **Formula:**
  - Upper: `Highest High over N periods`
  - Lower: `Lowest Low over N periods`
  - Middle: `(Upper + Lower) / 2`
- **Parameters:** Period (default: 20)
- **Characteristics:** One of the simplest volatility/breakout indicators. Channel width directly reflects the price range over the lookback period. Foundation of the famous Turtle Trading system.
- **Signals:** Price breaking above the upper channel = bullish breakout. Price breaking below the lower channel = bearish breakout. Narrowing channel = decreasing volatility.
- **Use:** Breakout entry systems (buy N-period high, sell N-period low), trailing stop via opposite channel band, volatility measurement via channel width.

## Standard Deviation

- **Formula:** `σ = √(Σ(x - μ)² / n)` where μ is the mean of the dataset
- **Parameters:** Period (default: 20, matching Bollinger Bands)
- **Characteristics:** Fundamental statistical measure of dispersion from the mean. Forms the mathematical basis for Bollinger Bands and many other volatility indicators. Can be applied to price, returns, or any time series.
- **Signals:** Rising standard deviation = increasing price dispersion = higher volatility. Falling standard deviation = price clustering = lower volatility and potential breakout setup.
- **Use:** Direct volatility measurement, Bollinger Band construction, z-score calculations for mean-reversion strategies, risk normalization.

## Acceleration Bands

- **Formula:**
  - Upper Band: `SMA(High × (1 + width_factor))`
  - Lower Band: `SMA(Low × (1 - width_factor))`
  - Width factor is derived from: `((High - Low) / ((High + Low) / 2)) × multiplier`
- **Parameters:** Period (default: 20), multiplier for width factor
- **Characteristics:** Dynamic bands that widen and narrow based on the ratio of the high-low range to the midpoint price. They adapt more aggressively to volatility changes than Bollinger Bands.
- **Signals:** Price closing outside bands signals strong directional momentum. Price returning inside bands signals a potential reversal or consolidation.
- **Use:** Breakout confirmation, momentum detection, adaptive volatility envelopes.

## Summary Comparison

| Indicator | Output | Directional | Best For | Key Strength |
|-----------|--------|-------------|----------|--------------|
| Bollinger Bands | Band envelope | No | Squeeze/breakout detection | Adaptive width via std dev |
| ATR | Single value | No | Position sizing, stops | Universal volatility measure |
| Keltner Channels | Band envelope | No | Squeeze setups with BB | Smoother bands via ATR |
| NATR | Percentage | No | Cross-asset comparison | Price-normalized volatility |
| Choppiness Index | Oscillator (0-100) | No | Trend vs. chop classification | Regime detection |
| Donchian Channel | Band envelope | No | Breakout systems | Simplicity, Turtle Trading |
| Standard Deviation | Single value | No | Statistical analysis | Foundation for other indicators |
| Acceleration Bands | Band envelope | No | Momentum breakouts | Aggressive volatility adaptation |

---

*Source: Generalized from QuantConnect Indicators documentation and standard technical analysis references.*
