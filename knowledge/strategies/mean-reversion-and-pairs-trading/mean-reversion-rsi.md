# Mean Reversion with RSI

## Overview

Exploits short-term mean reversion using the Relative Strength Index (RSI) as an oversold/overbought indicator. Buys when RSI drops below an oversold threshold (indicating the asset is temporarily underpriced) and sells when RSI rises above an overbought threshold.

## Academic Reference

- **Paper**: "RSI-Based Trading Strategies" — Technical analysis literature
- **Link**: https://quantpedia.com/strategies/mean-reversion-with-rsi/

## Strategy Logic

### Universe Selection

Liquid equities or ETFs with sufficient price history for indicator calculation.

### Signal Generation

Calculate RSI over a configurable period (default 14 days):

```
RSI = 100 - 100 / (1 + RS)
RS = Average Gain / Average Loss (over rsi_period)
```

### Entry / Exit Rules

- **Entry**: Go long when RSI < oversold threshold (default 30).
- **Exit**: Close position when RSI > overbought threshold (default 70).

### Portfolio Construction

Equal-weight allocation across assets with active buy signals, subject to position size limits.

### Rebalancing Schedule

Daily — signal checked at each bar close.

## Key Indicators / Metrics

- **RSI period**: 14 days (configurable, typical range 7–21)
- **Oversold threshold**: 30 (configurable, range 20–40)
- **Overbought threshold**: 70 (configurable, range 60–80)

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | 2010–2020 | Buy-and-hold |
| Annual Return | ~8–12% | ~10% |
| Sharpe Ratio | ~0.6–1.0 | ~0.5 |
| Max Drawdown | ~15% | ~30% |

## Data Requirements

- **Asset Classes**: US equities, ETFs
- **Resolution**: Daily
- **Lookback Period**: RSI period + warm-up (minimum ~30 bars)

## Implementation Notes

- RSI is a bounded oscillator (0–100), making threshold-based signals straightforward.
- Works best on liquid, mean-reverting instruments (large-cap equities, broad ETFs).
- Can be combined with Bollinger Bands for confirmation.

## Risk Considerations

- RSI can remain in oversold/overbought territory during strong trends, causing premature entries.
- Performance is regime-dependent — struggles in trending markets.
- Sensitive to parameter choices (period, thresholds).
- Transaction costs from frequent trading.

## Related Strategies

- [Mean Reversion with Bollinger Bands](mean-reversion-bollinger.md)
- [Short-Term Reversal](short-term-reversal.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/mean-reversion-rsi)
