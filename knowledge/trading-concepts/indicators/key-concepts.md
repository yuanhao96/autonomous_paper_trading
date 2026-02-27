# Technical Indicators — Key Concepts

## Overview

Technical indicators transform raw market data (price, volume, open interest) into numerical values that help detect trading opportunities. They are mathematical calculations based on historical price, volume, or open interest data. Indicators distill complex market behavior into actionable signals that can be consumed by algorithmic trading strategies.

## Categories of Indicators

- **Leading indicators**: Attempt to predict future price movements before they occur (RSI, Stochastic, Williams %R)
- **Lagging indicators**: Confirm trends already in motion, reacting after price has moved (moving averages, MACD)
- **Coincident indicators**: Move in tandem with price action in real time (Bollinger Bands, volume)

## Indicator Types

| Type | Description | Examples |
|------|-------------|----------|
| Trend | Identify direction and strength of a trend | SMA, EMA, ADX, Ichimoku Cloud |
| Momentum | Measure the speed and magnitude of price change | RSI, MACD, Stochastic, ROC |
| Volatility | Measure price dispersion and range expansion/contraction | Bollinger Bands, ATR, Keltner Channels |
| Volume | Analyze trading volume to confirm or question price moves | VWAP, OBV, Chaikin Money Flow |
| Oscillator | Bounded indicators used for overbought/oversold detection | CCI, Fisher Transform, Williams %R |

## Data Inputs

- **OHLCV bars** — Open, High, Low, Close, Volume (the most common input)
- **Quote data** — Bid/ask prices and sizes
- **Trade ticks** — Individual trade executions
- **Custom data sources** — Sentiment scores, order flow metrics, alternative data

## Warmup Period

Most indicators require a minimum number of historical data points before they produce valid (stable) values. Acting on indicator output before warmup completes leads to unreliable signals.

Common warmup requirements:

| Indicator | Warmup Needed |
|-----------|---------------|
| SMA(20) | 20 bars |
| EMA(20) | ~20 bars (exponential decay approaches zero weight) |
| RSI(14) | 15 bars (14 periods + 1 for initial calculation) |
| Bollinger Bands(20, 2) | 20 bars |
| MACD(12, 26, 9) | 34 bars (26 + 9 - 1) |
| ADX(14) | 28 bars (2 x period) |

Always ensure your strategy waits for all indicators to be fully warmed up before generating trade signals.

## Automatic vs Manual Updates

- **Automatic**: The indicator subscribes to a data stream and receives every new bar as it arrives. This is the most common mode — the platform handles the plumbing.
- **Manual**: You explicitly choose when and what data to feed into the indicator. This is useful for custom timeframes, alternative data sources, or when you need to compute an indicator over a non-standard series.

## Indicator Composition

Indicators can be chained or composed to create higher-order signals. The output of one indicator becomes the input of another. Examples:

- **RSI of a moving average** — Smooths price before measuring momentum
- **Bollinger Bands of RSI** — Detects when RSI itself is at extremes relative to its own history
- **EMA of MACD histogram** — Smooths the MACD histogram for cleaner divergence detection
- **ATR-based trailing stop** — Uses volatility to dynamically adjust stop distance

Composition is powerful but increases warmup requirements (sum of all component warmups).

## Common Signal Patterns

- **Crossover**: One indicator line crosses another (e.g., fast MA crosses above slow MA for a bullish signal)
- **Divergence**: Price makes a new high/low but the indicator does not — suggests weakening momentum
  - *Bullish divergence*: Price makes lower low, indicator makes higher low
  - *Bearish divergence*: Price makes higher high, indicator makes lower high
- **Overbought/Oversold**: Bounded indicators reaching extreme levels signal potential mean reversion
- **Breakout**: Price moves beyond an indicator boundary (e.g., closing outside Bollinger Bands)
- **Convergence**: Multiple indicators aligning in the same direction increases signal confidence

## Best Practices

1. **Combine indicators from different categories** — Use a trend indicator with a momentum indicator and a volume indicator for confirmation across dimensions.
2. **Avoid redundancy** — Do not stack RSI + Stochastic + Williams %R; they all measure momentum and will produce correlated signals.
3. **Match parameters to your timeframe** — A 200-period SMA is meaningful on daily bars but noisy on 1-minute bars.
4. **Respect the warmup period** — Never act on indicator values before the indicator is fully ready.
5. **Backtest indicator combinations** — Validate that your signals have an edge on historical data before deploying live.
6. **Guard against overfitting** — The more parameters you optimize, the higher the risk that performance is curve-fitted to historical noise.
7. **Use multiple timeframes** — An indicator signal on a higher timeframe carries more weight than the same signal on a lower timeframe.
8. **Monitor for regime changes** — Indicators that work in trending markets may fail in ranging markets and vice versa.

## Key Takeaways

- Indicators are tools, not oracles. No single indicator is sufficient on its own.
- Understanding *what* an indicator measures is more important than memorizing its formula.
- The best algorithmic strategies use a small number of complementary, well-understood indicators.
- Always validate with backtesting and forward testing before committing capital.

---

*Source: Generalized from QuantConnect Indicators documentation.*
