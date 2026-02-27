# Candlestick Patterns

## Overview

Candlestick patterns are specific formations of one or more candlesticks that signal potential price movements. Pattern recognition algorithms output a value of **+1** (bullish), **-1** (bearish), or **0** (no pattern detected). They are best used as confirmation signals alongside other indicators such as volume, moving averages, and support/resistance levels.

## Single Candle Patterns

### Doji
- **Definition:** Open is approximately equal to Close (very small or no real body).
- **Signal:** Indecision in the market; potential reversal when appearing after a strong trend.
- **Variants:**
  - **Standard Doji:** Small body centered between shadows.
  - **Long-Legged Doji:** Long upper and lower shadows, indicating extreme indecision.
  - **Dragonfly Doji:** Long lower shadow, no upper shadow -- bullish reversal signal.
  - **Gravestone Doji:** Long upper shadow, no lower shadow -- bearish reversal signal.

### Hammer / Hanging Man
- **Structure:** Small body at the top of the range, long lower shadow (at least 2x the body length), little or no upper shadow.
- **Hammer:** Appears at the bottom of a downtrend. The long lower shadow shows buyers rejected lower prices -- bullish reversal.
- **Hanging Man:** Appears at the top of an uptrend. Same shape, but warns of potential selling pressure -- bearish reversal.

### Inverted Hammer / Shooting Star
- **Structure:** Small body at the bottom of the range, long upper shadow, little or no lower shadow.
- **Inverted Hammer:** Appears after a downtrend, signaling potential bullish reversal as buyers begin testing higher prices.
- **Shooting Star:** Appears at the top of an uptrend, signaling bearish reversal as sellers reject higher prices.

### Marubozu
- **Structure:** Full-bodied candle with no shadows (or negligibly small ones).
- **Bullish Marubozu:** Strong buying pressure throughout the entire period; opens at low, closes at high.
- **Bearish Marubozu:** Strong selling pressure; opens at high, closes at low.

### Spinning Top
- **Structure:** Small body with both upper and lower shadows of moderate length.
- **Signal:** Indicates indecision and a weakening current trend. Neither buyers nor sellers dominated.

## Two Candle Patterns

### Engulfing
- **Structure:** The second candle's body completely engulfs the first candle's body.
- **Bullish Engulfing:** A small bearish candle followed by a larger bullish candle after a downtrend -- strong bullish reversal.
- **Bearish Engulfing:** A small bullish candle followed by a larger bearish candle after an uptrend -- strong bearish reversal.

### Harami
- **Structure:** The second candle's body is contained entirely within the first candle's body (opposite of engulfing).
- **Bullish Harami:** Large bearish candle followed by a smaller bullish candle -- potential bullish reversal.
- **Bearish Harami:** Large bullish candle followed by a smaller bearish candle -- potential bearish reversal.

### Piercing Line / Dark Cloud Cover
- **Piercing Line (Bullish):** After a downtrend, the second candle opens below the first candle's low and closes above the midpoint of the first candle's body.
- **Dark Cloud Cover (Bearish):** After an uptrend, the second candle opens above the first candle's high and closes below the midpoint of the first candle's body.

### Tweezer Top / Bottom
- **Structure:** Two consecutive candles with matching highs (Tweezer Top) or matching lows (Tweezer Bottom).
- **Signal:** Reversal patterns that form at support or resistance levels, indicating price rejection at a specific level.

## Three Candle Patterns

### Morning Star / Evening Star
- **Structure:** Three candles -- large body, then a small body (often with a gap), then a large body in the opposite direction of the first.
- **Morning Star (Bullish):** Large bearish candle, small-bodied candle (indecision), large bullish candle. Signals a bottom reversal.
- **Evening Star (Bearish):** Large bullish candle, small-bodied candle (indecision), large bearish candle. Signals a top reversal.

### Three White Soldiers / Three Black Crows
- **Three White Soldiers:** Three consecutive bullish candles, each closing higher than the previous, with small or no upper shadows. Strong bullish continuation.
- **Three Black Crows:** Three consecutive bearish candles, each closing lower than the previous, with small or no lower shadows. Strong bearish continuation.

### Abandoned Baby
- **Structure:** A Doji star that gaps away from both the preceding and following candles (gaps on both sides).
- **Signal:** Rare but highly reliable reversal pattern. Bullish when appearing after a downtrend, bearish after an uptrend.

## Multi-Candle Patterns

### Rising / Falling Three Methods
- **Structure:** A large candle in the trend direction, followed by 3-4 small counter-trend candles that stay within the range of the first candle, then a large candle continuing the original trend.
- **Rising Three Methods:** Bullish continuation -- the small bearish candles are a temporary pullback within an uptrend.
- **Falling Three Methods:** Bearish continuation -- the small bullish candles are a temporary rally within a downtrend.

## Pattern Reliability

| Pattern | Type | Reliability | Signal |
|---|---|---|---|
| Engulfing | Reversal | High | Bullish / Bearish |
| Morning / Evening Star | Reversal | High | Bullish / Bearish |
| Abandoned Baby | Reversal | High (rare) | Bullish / Bearish |
| Hammer / Hanging Man | Reversal | Medium-High | Bullish / Bearish |
| Three Soldiers / Crows | Continuation | Medium | Bullish / Bearish |
| Harami | Reversal | Medium | Bullish / Bearish |
| Piercing / Dark Cloud | Reversal | Medium | Bullish / Bearish |
| Doji | Indecision | Medium | Context-dependent |
| Spinning Top | Indecision | Low-Medium | Context-dependent |
| Marubozu | Continuation | Medium | Bullish / Bearish |

## Best Practices

1. **Consider trend context.** A hammer only works as a bullish reversal if it appears after a meaningful downtrend. Patterns without prior trend context are unreliable.
2. **Confirm with volume.** Engulfing and star patterns are significantly more reliable when accompanied by above-average volume on the confirmation candle.
3. **Use higher timeframes.** Patterns on daily or weekly charts are more reliable than those on 1-minute or 5-minute charts due to reduced noise.
4. **Combine with other indicators.** Use candlestick patterns as confirmation alongside trend indicators (moving averages), momentum (RSI, MACD), and support/resistance levels.
5. **Be cautious with gaps in 24-hour markets.** Many patterns (Morning Star, Abandoned Baby) rely on price gaps, which are uncommon in continuously traded markets such as crypto and forex. Adapt pattern criteria accordingly.
6. **Watch for pattern failure.** If price does not follow through in the expected direction within 2-3 bars, the pattern has likely failed. Use stop losses based on the pattern's extremes.

*Source: Generalized from QuantConnect Indicators documentation.*
