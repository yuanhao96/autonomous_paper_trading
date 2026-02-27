# The Momentum Strategy Based on the Low Frequency Component of Forex Market

## Overview

Applies the Hodrick-Prescott (HP) filter to decompose exchange rate time series into trend and cyclical components, then uses short-term momentum on the extracted low-frequency trend. A moving average crossover on the trend component generates buy/sell signals.

## Academic Reference

- **Paper**: "A Momentum Trading Strategy Based on the Low Frequency Component of the Exchange Rate" — Harris & Yilmaz (2009), Journal of Banking & Finance, 33(9):1575–1585

## Strategy Logic

### Universe Selection

Seven currency pairs: EURUSD, USDCAD, USDCHF, EURGBP, USDNOK, USDZAR.

### Signal Generation

**Step 1 — HP Filter decomposition**:

Minimize: `Σ(y_t - x_t)² + λ × Σ(Δ²x_t)²`

Where `λ=100` (calibrated for daily data). Solves: `(I + 2λD'D)x = y` using sparse matrix operations.

**Step 2 — MA(1,2) signal on trend component**:
- **Buy**: Current trend value > previous trend value.
- **Sell**: Current trend value < previous trend value.
- Position: Fully long (+1) or fully short (-1).

### Entry / Exit Rules

- **Long**: When extracted trend is rising.
- **Short**: When extracted trend is falling.
- Daily signal evaluation with immediate execution.

### Portfolio Construction

Full allocation per pair. Separate signal per currency pair.

### Rebalancing Schedule

Daily signal evaluation.

## Key Indicators / Metrics

- Hodrick-Prescott filter (λ=100)
- MA(1,2) on trend component
- 5-year (1,800 observations) training period

## Backtest Performance

| Pair | Sharpe Ratio | Total Trades | Annual Return | Max Drawdown |
|------|-------------|--------------|---------------|--------------|
| EURUSD | -0.309 | 14 | -3.65% | 23.7% |
| EURGBP | **0.480** | 15 | 4.04% | 21.8% |
| USDNOK | 0.210 | 13 | 2.19% | 19.7% |

Period: Jan 2011 – May 2017. Best performer: EURGBP.

## Data Requirements

- **Asset Classes**: Forex (7 pairs)
- **Resolution**: Daily
- **Lookback Period**: 5 years (1,800 observations) for HP filter training
- **Initial Capital**: $100,000

## Implementation Notes

- HP filter implemented via sparse matrix operations.
- 5-year training period before out-of-sample testing.
- Daily signals — few trades generated (13–15 per pair over 6 years).
- Python on QuantConnect LEAN.

## Risk Considerations

- **HP filter end-point problem**: "Designed for full historical datasets; adding new data causes retroactive trend-line adjustments, reducing predictive accuracy."
- High sensitivity to MA lag parameter — changes are non-monotonic.
- Unstable returns across forex pairs — works for some, not others.
- Few total trades (13–15) — difficult to assess statistical significance.
- Large training period requirement (5 years) limits applicability.
- Most pairs show negative or marginal Sharpe ratios.

## Related Strategies

- [Forex Momentum](forex-momentum.md)
- [Combining Mean Reversion and Momentum in Forex Market](../forex/combining-mean-reversion-and-momentum-in-forex.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/the-momentum-strategy-based-on-the-low-frequency-component-of-forex-market)
