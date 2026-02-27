# Forecasting Stock Prices Using a Temporal CNN Model

## Overview

Uses a Temporal Convolutional Neural Network to predict 5-day directional price movements for AAPL, FB, and MSFT. Input: 15 daily OHLCV bars. Output: UP/DOWN/STATIONARY classification. Trades when confidence exceeds 55%. Requires GPU. Average Sharpe: −0.274 (non-deterministic).

## Academic Reference

- **Paper**: "Temporal Logistic Neural Bag-of-Features for Financial Time series Forecasting leveraging Limit Order Book Data" — Passalis et al. (2019)

## Strategy Logic

### Universe Selection

3 technology stocks: AAPL, FB (Meta), MSFT.

### Signal Generation

**Input**: 15 daily bars × 5 features (OHLCV) per stock.

**Architecture**:
1. Input layer: (15, 5).
2. Conv1D: 30 filters, kernel size 4, ReLU.
3. Temporal split: Lambda layers divide into 3 temporal regions.
4. Parallel Conv1D: 1 filter per temporal segment.
5. Concatenation + flatten.
6. Dense output: 3 nodes, softmax (UP/DOWN/STATIONARY).

**Labels**: 5-bar forward average close vs. current close (>0.01% = UP, <−0.01% = DOWN, else STATIONARY).

**Training**: Adam optimizer, categorical cross-entropy, 20 epochs.

### Entry / Exit Rules

- **Long/Short**: Model confidence > 55% for UP or DOWN.
- **Exit**: Time-based (1–5 day random duration to limit position accumulation).
- Insights expire after holding period.

### Portfolio Construction

InsightWeightingPortfolioConstructionModel. ImmediateExecutionModel. $100,000 capital, margin account.

### Rebalancing Schedule

Model retrains quarterly. Monthly recalibration. Daily signal evaluation.

## Key Indicators / Metrics

- 15-bar OHLCV input window
- 5-bar forward average (prediction target)
- 55% confidence threshold
- 3-class classification (UP/DOWN/STATIONARY)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Average Sharpe (10 runs) | −0.274 |
| Benchmark (QQQ) Sharpe | 0.877 |
| Annual Volatility | 0.139 |
| Note | Non-deterministic results |

## Data Requirements

- **Asset Classes**: US equities (3 tech stocks)
- **Resolution**: Daily (consolidated from minute)
- **Lookback**: 500 daily bars for training; 15 bars for prediction
- **Libraries**: TensorFlow/Keras
- **Compute**: GPU required

## Implementation Notes

- DataFrame construction with rolling averages and labels.
- Iterative slicing into 15-step training windows.
- StandardScaler normalization (flatten → scale → reshape).
- Missing values forward-filled.
- Python on QuantConnect LEAN with TensorFlow/Keras.

## Risk Considerations

- Non-deterministic: "Users should expect to see different results in repeated backtests."
- Negative Sharpe (−0.274) — strategy loses money.
- 55% confidence threshold may be insufficient after transaction costs.
- Look-ahead bias risk: 5-bar future average label requires careful alignment.
- Overfitting potential: 20-epoch training on limited windows with only 3 stocks.
- GPU computational demands limit deployment flexibility.
- Tech-heavy 3-stock universe is extremely concentrated.

## Related Strategies

- [Gaussian Naive Bayes Model](gaussian-naive-bayes-model.md)
- [Gradient Boosting Model](gradient-boosting-model.md)
- [SVM Wavelet Forecasting](svm-wavelet-forecasting.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/forecasting-stock-prices-using-a-temporal-cnn-model)
