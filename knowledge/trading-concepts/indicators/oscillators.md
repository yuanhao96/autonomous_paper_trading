# Oscillators & Other Indicators

## Overview

Oscillators are bounded or unbounded indicators that fluctuate around a central value or between fixed levels. They are particularly useful in ranging markets for identifying overbought/oversold conditions and potential reversal points. Unlike trend-following indicators, oscillators excel at signaling when a move is overextended and likely to reverse.

## Commodity Channel Index (CCI)

Measures how far the current price deviates from its statistical mean.

- **Formula:** `CCI = (Typical Price - SMA(TP, n)) / (0.015 * Mean Deviation)`
- **Typical Price:** `(High + Low + Close) / 3`
- **Parameters:** Lookback period `n` (default: 20). The constant 0.015 ensures roughly 75% of values fall between -100 and +100.
- **Signals:** CCI > +100 indicates overbought / strong upward momentum; CCI < -100 indicates oversold / strong downward momentum. Zero-line crossovers identify trend direction shifts. CCI can also be used for trend identification — sustained readings above +100 suggest a strong uptrend.

## Fisher Transform

Converts prices into a Gaussian normal distribution to create sharp, unambiguous turning points.

- **Formula:**
  - Normalize price to range [-1, +1]: `x = 2 * ((Price - Min) / (Max - Min)) - 1`
  - `Fisher = 0.5 * ln((1 + x) / (1 - x))`
- **Parameters:** Lookback period for min/max normalization (default: 10).
- **Signals:** Sharp peaks and troughs generate clear reversal signals. Crossovers of the Fisher line with its signal line (1-bar lag) indicate entries. The Fisher Transform produces more responsive and less ambiguous signals than RSI due to the Gaussian normalization.

## Awesome Oscillator (AO)

Measures market momentum by comparing recent momentum to a broader momentum baseline.

- **Formula:** `AO = SMA(Midpoint, 5) - SMA(Midpoint, 34)`
- **Midpoint:** `(High + Low) / 2`
- **Parameters:** Fast SMA period (default: 5), Slow SMA period (default: 34).
- **Signals:**
  - **Zero-line cross:** AO crossing above zero is bullish; crossing below is bearish.
  - **Twin peaks:** Two peaks on the same side of zero with a pullback between them — the second peak being higher (bullish) or lower (bearish) than the first signals continuation.
  - **Saucer:** Three consecutive bars where the histogram changes direction near zero, signaling a brief momentum dip before continuation.

## Balance of Power (BOP)

Measures the strength of buyers versus sellers by evaluating where the close falls relative to the open within the bar range.

- **Formula:** `BOP = (Close - Open) / (High - Low)`
- **Parameters:** Often smoothed with a moving average (e.g., 14-period SMA).
- **Range:** -1 to +1.
- **Signals:** BOP > 0 indicates buyers dominating; BOP < 0 indicates sellers dominating. Sustained readings near extremes indicate strong directional conviction. Divergence from price can precede reversals.

## Detrended Price Oscillator (DPO)

Removes the trend component from price to isolate underlying cycles.

- **Formula:** `DPO = Close - SMA(Close, n) shifted back (n/2 + 1) periods`
- **Parameters:** Lookback period `n` (default: 20).
- **Signals:** DPO peaks and troughs identify cycle turning points. The oscillator is not anchored to current time — it is shifted backward to align with the cycle it measures. Useful for estimating cycle length and timing entries within cyclical patterns.

## Coppock Curve

A long-term momentum indicator originally designed for monthly charts to identify major market bottoms.

- **Formula:** `Coppock = WMA(10, ROC(14) + ROC(11))`
- **Parameters:** WMA period (default: 10), Long ROC period (default: 14), Short ROC period (default: 11).
- **Signals:** A buy signal is generated when the Coppock Curve turns upward from below zero. Originally intended only for buy signals on monthly data, though some traders also use downward turns from above zero as sell signals. Best suited for long-term position timing.

## Hurst Exponent

A statistical measure that characterizes the long-term memory of a time series, indicating whether it is trending, mean-reverting, or random.

- **Values:**
  - `H > 0.5`: Trending (persistent) — the series tends to continue in its current direction. Favor trend-following strategies.
  - `H = 0.5`: Random walk — no exploitable pattern. The series has no memory.
  - `H < 0.5`: Mean-reverting (anti-persistent) — the series tends to reverse direction. Favor mean-reversion strategies.
- **Parameters:** Window length for estimation (varies; typically 100+ bars for stability).
- **Use:** The Hurst Exponent is a regime classifier rather than a signal generator. It determines which class of strategy (trend-following vs. mean-reversion) is appropriate for current market conditions.

## Hilbert Transform

Decomposes price into instantaneous phase and amplitude components to identify dominant cycles adaptively.

- **Key Outputs:**
  - **Instantaneous Trendline:** An adaptive moving average derived from the dominant cycle period.
  - **Dominant Cycle Period:** The current prevailing cycle length in bars, updated dynamically.
  - **Phase and Amplitude:** Cycle phase position and strength at each bar.
- **Parameters:** Internally adaptive — no fixed user parameters required.
- **Signals:** Phase crossovers indicate cycle turning points. The dominant cycle period can be fed into other indicators (e.g., RSI, Stochastic) to make their lookback periods adaptive. Trend mode vs. cycle mode determination based on phase behavior.

## Squeeze Momentum

Combines Bollinger Band width relative to Keltner Channels to detect volatility compression, then uses momentum to determine breakout direction.

- **Squeeze Detection:** Bollinger Bands (20, 2.0) contract inside Keltner Channels (20, 1.5) — this signals a "squeeze" (low-volatility compression).
- **Squeeze Release:** When Bollinger Bands expand back outside Keltner Channels, the squeeze "fires" and a directional move is expected.
- **Momentum Histogram:** Typically the linear regression value of (Close - midline of Donchian Channel) over the lookback period.
- **Parameters:** BB period/multiplier (default: 20/2.0), KC period/multiplier (default: 20/1.5), momentum length (default: 20).
- **Signals:** Enter in the direction of the momentum histogram when the squeeze fires. Rising histogram = bullish momentum; falling histogram = bearish momentum. The squeeze setup identifies periods of energy buildup before explosive moves.

## Summary Comparison

| Indicator | Type | Range | Default Period | Primary Use |
|-----------|------|-------|----------------|-------------|
| CCI | Unbounded | Unbounded (typically -300 to +300) | 20 | Overbought/oversold, trend strength |
| Fisher Transform | Unbounded | Unbounded (sharp peaks) | 10 | Sharp reversal detection |
| Awesome Oscillator | Unbounded | Unbounded | 5/34 | Momentum direction and shifts |
| Balance of Power | Bounded | -1 to +1 | 14 (smoothed) | Buyer/seller dominance |
| DPO | Unbounded | Unbounded | 20 | Cycle identification |
| Coppock Curve | Unbounded | Unbounded | 10/14/11 | Long-term bottom detection |
| Hurst Exponent | Bounded | 0 to 1 | 100+ | Regime classification |
| Hilbert Transform | Adaptive | Varies | Adaptive | Cycle period, adaptive parameters |
| Squeeze Momentum | Hybrid | Unbounded histogram | 20 | Volatility breakout direction |

---

*Source: Generalized from QuantConnect Indicators documentation.*
