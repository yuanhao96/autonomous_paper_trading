# Gradient Boosting Model

## Overview

Uses LightGBM gradient boosting to predict 10-minute SPY returns from technical indicator features (RSI, MACD, Bollinger Bands at multiple scales). Trains monthly on 4 weeks of minute data, trades intraday with a 5% cost threshold. Model significantly underperforms benchmark.

## Academic Reference

- **Paper**: Zhou et al. (2013) — claimed "annualized Sharpe ratio greater than 20" (not replicated in this implementation)

## Strategy Logic

### Universe Selection

Single asset: SPY (S&P 500 ETF). Minute-level data.

### Signal Generation

**Features** (technical indicators at multiple scales):
- RSI: periods 14k (k = 0.5 to 5)
- MACD: periods 12k/26k with 9-period signal
- Bollinger Bands: normalized as (close − middle) / (2 × σ)

**Model**: LightGBM with 20 decision stumps (max depth 1), learning rate 0.1.

**Prediction**: 10-minute forward return.

### Entry / Exit Rules

- **Long**: Predicted return > 5% cost threshold (2% commission + 3% spread).
- **Short**: Predicted return < −5%.
- **Flat**: Predicted return within ±5% threshold.
- **Exit**: 10-minute holding period. No overnight positions (scheduled liquidation).

### Portfolio Construction

InsightWeightingPortfolioConstructionModel. Equal-weight. ImmediateExecutionModel.

### Rebalancing Schedule

Model retrains monthly (end of month, previous 4 weeks of data). Signals generated intraday.

## Key Indicators / Metrics

- RSI, MACD, Bollinger Bands (multi-scale features)
- 10-minute forward return prediction
- 5% cost threshold

## Backtest Performance

| Metric | Strategy | SPY Benchmark |
|--------|----------|---------------|
| Sharpe (5yr, 2015–2020) | -0.649 | 0.691 |
| Variance | 0.004 | 0.024 |
| Sharpe (2020 crash) | -2.688 | -1.467 |
| Sharpe (2020 recovery) | -2.083 | 7.942 |

"Throughout a 5 year backtest, the model underperforms the SPY with its current parameter set."

## Data Requirements

- **Asset Classes**: US equity ETF (SPY)
- **Resolution**: Minute
- **Lookback**: 4 weeks of minute data per training cycle
- **Libraries**: LightGBM

## Implementation Notes

- Training data cleaning removes last 10 minutes of each trading day.
- Custom PNL loss functions tested but found ineffective.
- Feature engineering creates multiple scaled variations per indicator.
- Scheduled events prevent overnight holds.
- Python on QuantConnect LEAN.

## Risk Considerations

- Negative Sharpe ratio (−0.649) — strategy loses money on a risk-adjusted basis.
- 5% cost threshold is extremely high — few trades pass, reducing sample size.
- Model with depth-1 stumps may be too simple for complex market microstructure.
- Monthly retraining may not capture rapid regime changes.
- Academic claim of Sharpe > 20 was not reproduced — likely overfit or unrealistic assumptions.
- No stop-loss beyond scheduled overnight liquidation.

## Related Strategies

- [Gaussian Naive Bayes Model](gaussian-naive-bayes-model.md)
- [Forecasting Stock Prices using a Temporal CNN Model](forecasting-stock-prices-temporal-cnn.md)
- [SVM Wavelet Forecasting](svm-wavelet-forecasting.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/gradient-boosting-model)
