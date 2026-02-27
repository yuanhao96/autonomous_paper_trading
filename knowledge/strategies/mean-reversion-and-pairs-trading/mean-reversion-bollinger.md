# Mean Reversion with Bollinger Bands

## Overview

Exploits short-term mean reversion by buying when price touches or breaches the lower Bollinger Band (suggesting oversold conditions) and selling at the upper band or moving average (suggesting overbought conditions). Uses volatility-adaptive bands rather than fixed thresholds.

## Academic Reference

- **Paper**: "Bollinger on Bollinger Bands", John Bollinger (2001)
- **Link**: https://www.bollingerbands.com/

## Strategy Logic

### Universe Selection

Liquid equities or ETFs with mean-reverting price behavior.

### Signal Generation

Calculate Bollinger Bands:

```
Middle Band = SMA(Close, period)
Upper Band = Middle Band + k * StdDev(Close, period)
Lower Band = Middle Band - k * StdDev(Close, period)
```

Where `period` is typically 20 and `k` is typically 2.0.

### Entry / Exit Rules

- **Entry**: Go long when Close < Lower Band.
- **Exit**: Close position when Close > Middle Band (or Upper Band for more aggressive targets).

### Portfolio Construction

Equal-weight allocation across assets with active signals.

### Rebalancing Schedule

Daily — signal checked at each bar close.

## Key Indicators / Metrics

- **Bollinger period**: 20 days (configurable, range 10–50)
- **Band width (k)**: 2.0 standard deviations (configurable, range 1.5–3.0)
- **%B indicator**: (Close - Lower) / (Upper - Lower) — position within bands

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | 2010–2020 | Buy-and-hold |
| Annual Return | ~7–11% | ~10% |
| Sharpe Ratio | ~0.5–0.9 | ~0.5 |
| Max Drawdown | ~15% | ~30% |

## Data Requirements

- **Asset Classes**: US equities, ETFs
- **Resolution**: Daily
- **Lookback Period**: Bollinger period + warm-up (~40 bars minimum)

## Implementation Notes

- Bollinger Bands are volatility-adaptive — bands widen in high-vol regimes and narrow in low-vol.
- Implementation often uses RSI as a confirming indicator.
- The strategy implicitly assumes stationarity — works best on range-bound instruments.

## Risk Considerations

- In strong trends, price can "walk the band" — touching the lower band repeatedly during a downtrend.
- Bands based on normal distribution assumptions that may not hold for fat-tailed returns.
- Performance degrades in trending markets or during volatility regime changes.
- Sensitive to period and bandwidth parameters.

## Related Strategies

- [Mean Reversion with RSI](mean-reversion-rsi.md)
- [Short-Term Reversal](short-term-reversal.md)
- [Pairs Trading](pairs-trading.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/mean-reversion-bollinger)
