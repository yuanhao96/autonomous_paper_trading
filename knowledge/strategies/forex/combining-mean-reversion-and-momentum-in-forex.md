# Combining Mean Reversion and Momentum in Forex Market

## Overview

Combines momentum and mean reversion signals in forex using OLS regression. Predicts monthly currency returns from 3-month momentum and standardized deviation from historical mean. Goes long the pair with the highest predicted return and shorts the lowest. Based on Balvers & Wu's equity framework adapted to FX.

## Academic Reference

- **Paper**: Based on Alina F. Serban's research, adapting Balvers & Wu's equity framework to foreign exchange markets.

## Strategy Logic

### Universe Selection

4 major currency pairs: EURUSD, GBPUSD, USDCAD, USDJPY.

### Signal Generation

OLS regression with two factors:
1. **Momentum**: Price change over preceding 3-month period.
2. **Mean Reversion**: Standardized deviation from historical mean: (price − μ) / σ.

Improvement: "We replace (x − μ) with (x − μ)/σ. This captures the mean reversion factor better than the author's technique."

Regression coefficients:
- Reversal coefficient: 1.0350 (t-stat: −4.074, significant)
- Momentum coefficient: 0.0633 (t-stat: 1.417, not significant)
- R²: 1.4%

### Entry / Exit Rules

- **Long**: Currency pair with highest predicted return.
- **Short**: Currency pair with lowest predicted return.
- **Exception**: If all predicted returns are positive → long only. If all negative → short only.

### Portfolio Construction

Equal-weight long/short. Monthly reconstitution.

### Rebalancing Schedule

Monthly, first trading day at 9:31 AM.

## Key Indicators / Metrics

- 3-month momentum
- Standardized mean deviation
- OLS regression coefficients
- R²: 1.4%

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jun 2013 – Jun 2016 |
| Annual Return | −1.938% |
| Sharpe Ratio | −0.056 |
| Max Drawdown | 19.8% |

## Data Requirements

- **Asset Classes**: Forex (4 pairs)
- **Resolution**: Daily
- **Lookback**: 20 years of daily data (resampled to monthly)
- **Libraries**: OLS regression (statsmodels)

## Implementation Notes

- Five-step process: data retrieval → model training → monthly predictions → ranking → execution.
- 20 years of daily OHLC data resampled to monthly.
- Scheduled events for monthly execution.
- Python on QuantConnect LEAN.

## Risk Considerations

- Negative annual return (−1.938%) and Sharpe (−0.056) — strategy loses money.
- R² of 1.4% means the model explains almost nothing — signals are essentially noise.
- Momentum coefficient is not statistically significant (t-stat: 1.417).
- 4-pair universe is too small for robust cross-sectional analysis.
- 19.8% drawdown on a strategy with negative returns is unacceptable risk/reward.
- Limited sample size relative to original academic paper.

## Related Strategies

- [Forex Momentum](../momentum/forex-momentum.md)
- [Risk Premia in Forex Markets](risk-premia-in-forex-markets.md)
- [The Momentum Strategy Based on the Low Frequency Component of Forex Market](../momentum/momentum-strategy-low-frequency-forex.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/combining-mean-reversion-and-momentum-in-forex-market)
