# Trading with WTI BRENT Spread

## Overview

Mean-reversion pairs trade on the WTI-Brent crude oil spread. Uses a 20-day SMA to generate entry signals and a linear regression model to estimate fair value for exits. Monthly regression recalibration with daily trade execution. Dollar-neutral 50/50 positioning.

## Academic Reference

- **Paper**: Quantpedia — "Trading WTI/BRENT Spread"

## Strategy Logic

### Universe Selection

Two crude oil CFDs from OANDA: WTICOUSD (WTI) and BCOUSD (Brent).

### Signal Generation

1. **Spread**: WTI price − Brent price.
2. **20-day SMA**: Simple moving average of the spread.
3. **Fair value**: Linear regression: P_Brent = β × P_WTI + α. Fair value = (1 − β) × P_WTI − α.

### Entry / Exit Rules

- **Long spread**: Spread < 20-day SMA (bet on convergence upward).
- **Short spread**: Spread > 20-day SMA (bet on convergence downward).
- **Exit long**: Spread exceeds fair value.
- **Exit short**: Spread falls below fair value.

### Portfolio Construction

50% allocation per leg: ±0.5 WTI, ±0.5 Brent. Dollar-neutral pairs trade.

### Rebalancing Schedule

Linear regression recalibrated monthly (first trading day). Daily signal evaluation.

## Key Indicators / Metrics

- WTI-Brent spread
- 20-day SMA of spread
- Linear regression fair value (252-day training window)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2018 – Dec 2022 |
| Initial Capital | $100,000 |
| Data Source | OANDA CFD |

## Data Requirements

- **Asset Classes**: Crude oil CFDs (WTI, Brent)
- **Resolution**: Daily
- **Lookback**: 252 days for regression training
- **Libraries**: sklearn LinearRegression

## Implementation Notes

- sklearn LinearRegression for fair value model.
- Monthly recalibration of regression coefficients.
- 20-day SMA for entry signals.
- Charting plots spread deviations and trade signals.
- Python on QuantConnect LEAN.

## Risk Considerations

- WTI-Brent spread can diverge permanently due to structural supply/demand changes (e.g., US shale revolution).
- Linear regression may not capture non-linear or regime-dependent relationships.
- CFD pricing from OANDA may differ from futures pricing — basis risk.
- Monthly regression recalibration may lag during rapid market shifts.
- Spread can widen dramatically during geopolitical events.
- No stop-loss mechanisms.

## Related Strategies

- [Term Structure Effect in Commodities](term-structure-effect-in-commodities.md)
- [Can Crude Oil Predict Equity Returns](can-crude-oil-predict-equity-returns.md)
- [Optimal Pairs Trading](../mean-reversion-and-pairs-trading/optimal-pairs-trading.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/trading-with-wti-brent-spread)
