# Volume Indicators

## Overview

Volume indicators analyze trading volume to confirm price trends, detect reversals, and measure buying/selling pressure. Volume often precedes price — rising volume on price moves confirms the move; declining volume suggests the move may be weakening. These indicators are essential for validating signals from price-based indicators.

## On-Balance Volume (OBV)

A cumulative running total that adds or subtracts volume based on price direction.

- **Formula:**
  - If Close > Close_prev: `OBV = OBV_prev + Volume`
  - If Close < Close_prev: `OBV = OBV_prev - Volume`
  - If Close = Close_prev: `OBV = OBV_prev`
- **Parameters:** None (cumulative from first bar).
- **Signals:** Rising OBV confirms an uptrend; falling OBV confirms a downtrend. OBV divergence from price (e.g., price makes new high but OBV does not) signals a potential reversal. OBV breakouts from a range can precede price breakouts.

## Volume Weighted Average Price (VWAP)

The average price weighted by volume, used as an intraday institutional benchmark.

- **Formula:** `VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)`
- **Typical Price:** `(High + Low + Close) / 3`
- **Parameters:** Resets at the start of each trading session (daily).
- **Signals:** Price above VWAP suggests bullish intraday bias; price below VWAP suggests bearish bias. Institutional traders use VWAP to gauge execution quality. VWAP bands (standard deviations) act as dynamic support/resistance levels.

## Accumulation/Distribution Line (A/D)

Measures the cumulative flow of money into or out of a security by relating close position within the bar range to volume.

- **Formula:**
  - Money Flow Multiplier: `((Close - Low) - (High - Close)) / (High - Low)`
  - Money Flow Volume: `Multiplier * Volume`
  - A/D Line: `Previous A/D + Money Flow Volume`
- **Parameters:** None (cumulative).
- **Signals:** Rising A/D Line indicates accumulation (buying pressure); falling A/D Line indicates distribution (selling pressure). Divergence between A/D Line and price suggests the trend may reverse.

## Chaikin Money Flow (CMF)

A bounded version of the A/D concept, averaging money flow over a fixed window.

- **Formula:** `CMF = Sum(Money Flow Volume, n) / Sum(Volume, n)`
- **Parameters:** Lookback period `n` (default: 20).
- **Range:** -1 to +1.
- **Signals:** CMF > 0 indicates net buying pressure; CMF < 0 indicates net selling pressure. Values above +0.25 or below -0.25 represent strong conviction. Zero-line crossovers signal shifts in money flow direction.

## Chaikin Oscillator

Applies the MACD concept to the Accumulation/Distribution Line to measure momentum of money flow.

- **Formula:** `Chaikin Oscillator = EMA(3, A/D Line) - EMA(10, A/D Line)`
- **Parameters:** Fast EMA period (default: 3), Slow EMA period (default: 10).
- **Signals:** Positive values indicate accelerating accumulation; negative values indicate accelerating distribution. Crossovers of the zero line generate buy/sell signals. Divergence from price warns of potential trend changes.

## Force Index

Combines price change magnitude with volume to quantify the force behind a price move.

- **Formula:** `Force Index = (Close - Close_prev) * Volume`
- **Parameters:** Typically smoothed with an EMA — 2-period for short-term, 13-period for intermediate signals.
- **Signals:** Positive values indicate buyers in control; negative values indicate sellers in control. Zero-line crossovers of the smoothed Force Index signal trend direction changes. Spikes indicate strong conviction moves.

## Money Flow Index (MFI)

A volume-weighted RSI that incorporates both price and volume to measure buying/selling pressure.

- **Formula:**
  - Typical Price: `(High + Low + Close) / 3`
  - Raw Money Flow: `Typical Price * Volume`
  - Money Flow Ratio: `Sum(Positive MF, n) / Sum(Negative MF, n)`
  - `MFI = 100 - (100 / (1 + Money Flow Ratio))`
- **Parameters:** Lookback period `n` (default: 14).
- **Range:** 0 to 100.
- **Signals:** MFI > 80 indicates overbought conditions; MFI < 20 indicates oversold conditions. Divergence between MFI and price is a strong reversal signal. Volume confirmation makes MFI more reliable than RSI alone in many contexts.

## Volume Profile

A histogram showing the distribution of traded volume at each price level over a specified period.

- **Key Levels:**
  - **Point of Control (POC):** The price level with the highest traded volume — acts as a magnet for price.
  - **Value Area:** The price range containing approximately 70% of total volume, bounded by Value Area High (VAH) and Value Area Low (VAL).
  - **High Volume Nodes (HVN):** Price levels with significant volume concentration — tend to act as support/resistance and cause price consolidation.
  - **Low Volume Nodes (LVN):** Price levels with minimal volume — price tends to move quickly through these zones.
- **Parameters:** Time period for aggregation (session, week, custom range).
- **Signals:** Rejection from POC or Value Area edges provides trade entries. LVN zones identify areas where price is likely to accelerate. Developing Value Area shifts indicate intraday directional bias.

## Summary Comparison

| Indicator | Type | Range | Default Period | Primary Use |
|-----------|------|-------|----------------|-------------|
| OBV | Cumulative | Unbounded | N/A | Trend confirmation, divergence |
| VWAP | Cumulative | Unbounded | Intraday (resets daily) | Execution benchmark, intraday bias |
| A/D Line | Cumulative | Unbounded | N/A | Money flow direction |
| CMF | Bounded | -1 to +1 | 20 | Buying/selling pressure strength |
| Chaikin Osc | Unbounded | Unbounded | 3/10 EMA | Money flow momentum |
| Force Index | Unbounded | Unbounded | 13 EMA | Move conviction |
| MFI | Bounded | 0–100 | 14 | Volume-weighted overbought/oversold |
| Volume Profile | Distribution | N/A | Session/custom | Support/resistance, value areas |

---

*Source: Generalized from QuantConnect Indicators documentation.*
