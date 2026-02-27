# SVM Wavelet Forecasting

## Overview

Combines wavelet decomposition with Support Vector Regression (SVR) to forecast forex prices. Decomposes 152 daily closing prices using Symlets-10 wavelets, applies SVR to each component, reconstructs the forecast, and trades when predicted change exceeds ±0.5%. Uses 20× leverage.

## Academic Reference

- **Paper**: "SVR-wavelet adaptive model for forecasting financial time series" — Raimundo & Okamoto (2018), IEEE INFOCT

## Strategy Logic

### Universe Selection

Forex pairs: EURJPY (primary), GBPUSD, AUDCAD, NZDCHF. Brokerage: OANDA.

### Signal Generation

**Step 1 — Wavelet decomposition**: Decompose 152-point daily close series using `pywt.wavedec()` with Symlets-10 wavelets (3 decomposition levels).

**Step 2 — Denoising**: Apply thresholding (threshold = 0.5) to detail coefficients.

**Step 3 — SVR forecasting**: Fit SVR via GridSearchCV (C=[0.05–10], ε=[0.001–0.1]) to each decomposed component. Forecast one step ahead.

**Step 4 — Reconstruction**: `pywt.waverec()` to aggregate component forecasts.

**Percent change**: (forecasted_value / current_close) − 1.

### Entry / Exit Rules

- **Long**: Predicted change > +0.5%.
- **Short**: Predicted change < −0.5%.
- **Exit**: Daily rebalancing with new forecasts.

### Portfolio Construction

Position weight = absolute predicted percent change. Custom 20× leverage model. Portfolio normalized when total weights exceed 1.

### Rebalancing Schedule

Daily. One signal per security per day.

## Key Indicators / Metrics

- Symlets-10 wavelet decomposition (3 levels)
- SVR with GridSearchCV hyperparameter optimization
- 152-bar rolling window
- ±0.5% prediction threshold

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Mar 2023 – Mar 2024 |
| Sharpe Ratio | 0.553 |
| Benchmark (SPY) Sharpe | 0.463 |

## Data Requirements

- **Asset Classes**: Forex (4 pairs)
- **Resolution**: Daily
- **Lookback**: 152 daily bars minimum
- **Libraries**: PyWavelets (pywt), scikit-learn (SVR, GridSearchCV)

## Implementation Notes

- Four files: `main.py` (orchestration), `alpha.py` (signal generation), `SVMWavelet.py` (wavelet+SVR core), `portfolio.py` (leveraged construction).
- `pywt.wavedec()` / `pywt.waverec()` for decomposition/reconstruction.
- Previous insights cancelled before new signal emission.
- Python on QuantConnect LEAN.

## Risk Considerations

- 20× leverage amplifies drawdowns dramatically — unsuitable for live trading without extreme care.
- Model assumes past wavelet decomposition patterns persist — may fail during regime changes.
- SVR hyperparameter sensitivity — grid search may overfit to training window.
- 152-bar minimum data requirement limits applicability to newer instruments.
- One-step-ahead forecasts may not capture multi-period moves.
- Authors suggest testing alternative wavelet families and adaptive thresholds.

## Related Strategies

- [Gaussian Naive Bayes Model](gaussian-naive-bayes-model.md)
- [Gradient Boosting Model](gradient-boosting-model.md)
- [The Dynamic Breakout II Strategy](../forex/dynamic-breakout-ii-strategy.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/svm-wavelet-forecasting)
