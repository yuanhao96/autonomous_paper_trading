# Gaussian Naive Bayes Model

## Overview

Uses a Gaussian Naive Bayes classifier to predict daily return direction for technology stocks. Features are the last 4 daily open-to-close returns; the model predicts positive, negative, or flat next-day returns. Long-only on positive predictions with daily rebalancing.

## Academic Reference

- **Papers**: Lu (2016); Imandoust & Bolandraftar (2014) — Bayes' Theorem for probabilistic classification.

## Strategy Logic

### Universe Selection

Top 10 largest technology sector stocks (MorningStar Technology sector). Monthly universe refresh.

### Signal Generation

**Features**: Last 4 daily open-to-close returns from universe constituents.
**Labels**: Next-day open-to-open return direction (positive, negative, flat).
**Model**: Gaussian Naive Bayes classifier (scikit-learn GaussianNB).

### Entry / Exit Rules

- **Long**: When model predicts positive return direction for next trading day.
- **Exit**: Positions held 1 day; rebalanced daily based on new predictions.
- Long-only — no short positions.

### Portfolio Construction

InsightWeightingPortfolioConstructionModel. Equal-weight: 1/N per predicted security.

### Rebalancing Schedule

Daily. Model retrains whenever universe composition changes.

## Key Indicators / Metrics

- Historical open-to-close returns (4-day feature window)
- Open-to-open returns (forward-looking labels)
- Class means and standard deviations

## Backtest Performance

| Metric | Strategy | SPY Benchmark |
|--------|----------|---------------|
| Sharpe (5yr, 2015–2020) | 0.011 | 0.729 |
| Variance | 0.013 | 0.024 |
| Sharpe (2020 crash) | -1.433 | -1.467 |

## Data Requirements

- **Asset Classes**: US equities (technology sector)
- **Resolution**: Daily
- **Lookback**: 100+ days per security for training
- **Fundamental Data**: Market cap, sector classification

## Implementation Notes

- scikit-learn GaussianNB classifier.
- TradeBarConsolidator manages daily bar aggregation.
- SymbolData objects track per-security training datasets.
- Python on QuantConnect LEAN.

## Risk Considerations

- Sharpe ratio (0.011) is essentially zero — strategy has no meaningful edge.
- Model assumes feature independence and normal distributions — rarely true in financial data.
- Overnight gaps not captured — only intraday open-to-close returns used as features.
- Technology sector concentration increases cyclical risk.
- Daily rebalancing generates significant transaction costs.
- No stop-loss, volatility adjustment, or risk management.

## Related Strategies

- [Gradient Boosting Model](gradient-boosting-model.md)
- [Forecasting Stock Prices using a Temporal CNN Model](forecasting-stock-prices-temporal-cnn.md)
- [SVM Wavelet Forecasting](svm-wavelet-forecasting.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/gaussian-naive-bayes-model)
