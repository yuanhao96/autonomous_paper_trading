# Trend Indicators

## Overview

Trend indicators identify the direction and strength of price trends. They smooth out price data to reveal the underlying trend, helping traders determine whether to go long, short, or stay flat. Most trend indicators are lagging by nature, since they rely on historical price data, but advanced variants reduce this lag significantly.

## Simple Moving Average (SMA)

- **Formula:** `SMA = (P1 + P2 + ... + Pn) / n`
- **Parameters:** Period (common values: 20, 50, 100, 200)
- **Characteristics:** Equal weight to all data points in the window. Simple to compute but introduces lag proportional to the period length.
- **Signals:** Price above SMA = bullish bias; price below SMA = bearish bias. Golden Cross (50 SMA crosses above 200 SMA) signals a long-term bullish shift. Death Cross (50 SMA crosses below 200 SMA) signals a long-term bearish shift.
- **Use:** Baseline trend filter, dynamic support/resistance levels, crossover systems.

## Exponential Moving Average (EMA)

- **Formula:** `EMA = Close × k + EMA_prev × (1 - k)`, where `k = 2 / (n + 1)`
- **Parameters:** Period (common values: 9, 12, 21, 26, 50)
- **Characteristics:** Assigns exponentially more weight to recent prices. More responsive to new data than SMA, but more prone to whipsaws in choppy markets.
- **Signals:** Same crossover logic as SMA. Often used in pairs (e.g., 12/26 EMA crossover forms the basis of MACD).
- **Use:** Short-term trend detection, MACD construction, signal-line systems.

## Double Exponential Moving Average (DEMA)

- **Formula:** `DEMA = 2 × EMA(n) - EMA(EMA(n))`
- **Parameters:** Period
- **Characteristics:** Reduces the lag inherent in a standard EMA by applying a second EMA and combining them. Reacts faster to price changes while still filtering noise.
- **Signals:** Interpret similarly to EMA — crossovers with price or a slower DEMA indicate trend shifts.
- **Use:** Faster trend following where reduced lag is critical, such as intraday or momentum strategies.

## Hull Moving Average (HMA)

- **Formula:** `HMA = WMA(2 × WMA(n/2) - WMA(n), √n)`
- **Parameters:** Period
- **Characteristics:** Virtually eliminates lag while maintaining smoothness. Uses weighted moving averages (WMA) at multiple scales and a square-root-period final smoothing pass.
- **Signals:** Direction change of HMA itself (slope turning positive/negative) is the primary signal.
- **Use:** Low-latency trend detection. Especially useful when timing entries and exits with minimal delay.

## Average Directional Index (ADX)

- **Formula:** ADX is the smoothed average of the absolute difference between +DI and -DI, divided by their sum, over N periods (typically 14).
- **Parameters:** Period (default: 14)
- **Characteristics:** Measures trend **strength** on a 0-100 scale — it does NOT indicate direction. +DI and -DI provide directional context.
- **Signals:** ADX > 25 = trending market; ADX < 20 = ranging/choppy market. +DI > -DI = uptrend; -DI > +DI = downtrend. Rising ADX = strengthening trend regardless of direction.
- **Use:** Filter out range-bound markets before applying trend-following strategies. Combine with +DI/-DI crossovers for directional entries.

## Ichimoku Cloud (Ichimoku Kinko Hyo)

- **Components:**
  - Tenkan-sen (Conversion Line): `(9-period high + 9-period low) / 2`
  - Kijun-sen (Base Line): `(26-period high + 26-period low) / 2`
  - Senkou Span A: `(Tenkan + Kijun) / 2`, plotted 26 periods ahead
  - Senkou Span B: `(52-period high + 52-period low) / 2`, plotted 26 periods ahead
  - Chikou Span (Lagging Span): Close plotted 26 periods behind
  - Cloud (Kumo): Area between Senkou Span A and Senkou Span B
- **Signals:** Price above cloud = bullish; price below cloud = bearish; price inside cloud = consolidation. Tenkan/Kijun crossover acts as entry signal. Cloud thickness indicates support/resistance strength.
- **Use:** All-in-one trend system providing trend direction, momentum, support/resistance, and forward-looking signals.

## Parabolic SAR (Stop and Reverse)

- **Formula:** `SAR_next = SAR_current + AF × (EP - SAR_current)`
- **Parameters:** AF start (default: 0.02), AF increment (0.02), AF max (0.20)
- **Characteristics:** Plots dots above or below price. The acceleration factor (AF) increases each time a new extreme point (EP) is reached, causing the SAR to converge on price over time.
- **Signals:** Dots below price = uptrend (long); dots above price = downtrend (short). When dots flip sides, a reversal is indicated.
- **Use:** Trailing stop-loss placement, trend reversal detection, time-based exit signals.

## VWAP (Volume Weighted Average Price)

- **Formula:** `VWAP = Cumulative(Price × Volume) / Cumulative(Volume)`
- **Parameters:** Typically resets daily (intraday anchor)
- **Characteristics:** Incorporates volume into the average price calculation. Serves as an institutional benchmark — large funds measure execution quality against VWAP.
- **Signals:** Price above VWAP = bullish intraday bias; price below VWAP = bearish intraday bias. VWAP acts as dynamic support/resistance.
- **Use:** Intraday trend bias, execution benchmarking, mean-reversion targets.

## Arnaud Legoux Moving Average (ALMA)

- **Formula:** Gaussian-weighted moving average centered at an offset within the window.
- **Parameters:** Window (default: 9), Offset (default: 0.85), Sigma (default: 6)
- **Characteristics:** Uses a Gaussian distribution curve to weight prices. The offset parameter shifts the curve to reduce lag, while sigma controls the width (smoothness). Produces a smooth line with minimal lag.
- **Signals:** Slope direction and price crossovers, similar to other moving averages.
- **Use:** Low-lag trend following with tunable smoothness via sigma and offset parameters.

## Vortex Indicator

- **Formula:** `VI+ = Σ|High_current - Low_prev| / Σ TrueRange` and `VI- = Σ|Low_current - High_prev| / Σ TrueRange` over N periods.
- **Parameters:** Period (default: 14)
- **Characteristics:** Captures positive and negative trend movement by comparing current highs/lows to previous lows/highs, normalized by true range.
- **Signals:** VI+ crossing above VI- = bullish trend change; VI- crossing above VI+ = bearish trend change.
- **Use:** Trend reversal detection, directional bias confirmation.

## Summary Comparison

| Indicator | Type | Lag | Best For | Key Strength |
|-----------|------|-----|----------|--------------|
| SMA | Moving Average | High | Long-term trend filtering | Simplicity, stability |
| EMA | Moving Average | Medium | Short/medium-term trends | Responsiveness to recent data |
| DEMA | Moving Average | Low | Fast trend following | Reduced lag over EMA |
| HMA | Moving Average | Very Low | Timing entries/exits | Near-zero lag with smoothness |
| ADX | Trend Strength | Medium | Trend vs. range detection | Quantifies trend strength |
| Ichimoku | Composite System | Mixed | Complete trend analysis | All-in-one trend framework |
| Parabolic SAR | Trailing Stop | Low | Trend reversals, exits | Built-in stop-loss mechanism |
| VWAP | Volume-Weighted | N/A (resets) | Intraday bias | Institutional benchmark |
| ALMA | Moving Average | Low | Tunable smoothing | Configurable lag/smoothness |
| Vortex | Directional | Medium | Trend reversals | Captures rotational movement |

---

*Source: Generalized from QuantConnect Indicators documentation and standard technical analysis references.*
