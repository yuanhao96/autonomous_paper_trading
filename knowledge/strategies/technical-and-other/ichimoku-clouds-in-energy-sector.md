# Ichimoku Clouds in the Energy Sector

## Overview

Applies Ichimoku Cloud crossover signals to the 10 largest US energy stocks. Goes long when the Chikou Span crosses above the cloud top, and short when it crosses below the cloud bottom. Equal-weight with daily signal evaluation. Benchmarked against XLE.

## Academic Reference

- **Paper**: Gurrib (2020) — analyzing predictive power of Ichimoku Clouds for US energy sector stocks.

## Strategy Logic

### Universe Selection

10 largest US energy sector companies by market capitalization. Monthly dynamic universe refresh. Benchmark: XLE (Energy Select Sector SPDR).

### Signal Generation

Ichimoku Cloud with three components:
- **Chikou Span** (lagging line)
- **Senkou Span A** (cloud top/bottom boundary)
- **Senkou Span B** (cloud top/bottom boundary)

### Entry / Exit Rules

- **Long**: Chikou Span crosses the top of the cloud from below.
- **Short**: Chikou Span crosses the bottom of the cloud from above.
- Daily insights emitted with 1-day duration to maintain positions.

### Portfolio Construction

EqualWeightingPortfolioConstructionModel. ImmediateExecutionModel.

### Rebalancing Schedule

Monthly universe refresh. Daily signal updates.

## Key Indicators / Metrics

- Ichimoku Cloud (Chikou Span, Senkou Span A/B)
- Indicator warm-up: 26+ periods
- Market capitalization (universe selection)

## Backtest Performance

| Metric | Strategy | XLE Benchmark |
|--------|----------|---------------|
| Sharpe (2015–2020) | -0.31 | -0.083 |
| Annual Std Dev | 0.223 | — |
| Sharpe (2020 crash) | 176.524 | -0.902 |

Exceptional crash performance but underperforms across most periods.

## Data Requirements

- **Asset Classes**: US equities (energy sector)
- **Resolution**: Daily
- **Warm-up**: 26+ periods (Ichimoku)
- **Fundamental Data**: Market capitalization

## Implementation Notes

- Coarse/fine universe selection for energy sector filtering.
- Dynamic universe refresh monthly eliminates look-ahead bias.
- Daily Ichimoku signal evaluation.
- Python on QuantConnect LEAN.

## Risk Considerations

- Underperforms XLE benchmark over 5-year period (Sharpe −0.31 vs. −0.083).
- Energy sector concentration — highly cyclical with oil price dependency.
- Exceptional 2020 crash performance (Sharpe 176) unlikely to repeat — driven by oil price war.
- Ichimoku parameters designed for Japanese equity markets — may not transfer well.
- Daily 1-day insights create high turnover and transaction costs.
- No risk management beyond Ichimoku signals.

## Related Strategies

- [Dual Thrust Trading Algorithm](dual-thrust-trading-algorithm.md)
- [Asset Class Trend Following](../momentum/asset-class-trend-following.md)
- [Sector Momentum](../momentum/sector-momentum.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/ichimoku-clouds-in-the-energy-sector)
