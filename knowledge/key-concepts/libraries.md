# Libraries

## Overview

Covers the essential Python libraries for algorithmic trading: data manipulation, numerical computing, statistics, machine learning, visualization, and specialized trading libraries. Knowing which library to use for each task is a fundamental skill.

## Core Scientific Stack

### NumPy

The foundation for numerical computing in Python.

| Feature | Use Case |
|---------|----------|
| N-dimensional arrays | Price matrices, return vectors |
| Linear algebra | Portfolio optimization, factor models |
| Random number generation | Monte Carlo simulation |
| Mathematical functions | Log returns, exponentials |

```python
import numpy as np
returns = np.log(prices[1:] / prices[:-1])
cov_matrix = np.cov(return_matrix.T)
portfolio_var = weights @ cov_matrix @ weights.T
```

### Pandas

The standard for financial time series and tabular data.

| Feature | Use Case |
|---------|----------|
| DataFrame/Series | Price tables, factor scores |
| Time series indexing | Date-based slicing and resampling |
| Rolling calculations | Moving averages, rolling volatility |
| GroupBy operations | Sector aggregation, cross-sectional ranking |
| Missing data handling | fillna, dropna, interpolate |

```python
import pandas as pd
prices = pd.read_csv("prices.csv", parse_dates=["date"], index_col="date")
monthly_returns = prices.resample("M").last().pct_change()
sector_avg = returns.groupby(sector_map).mean()
```

### SciPy

Advanced scientific computing.

| Feature | Use Case |
|---------|----------|
| `scipy.optimize` | Portfolio optimization, curve fitting |
| `scipy.stats` | Statistical distributions, hypothesis tests |
| `scipy.signal` | Digital filtering, spectral analysis |
| `scipy.interpolate` | Yield curve interpolation |

```python
from scipy.optimize import minimize
result = minimize(portfolio_volatility, initial_weights,
                  constraints=constraints, bounds=bounds)
```

## Statistics and Econometrics

### statsmodels

Statistical modeling and econometrics.

| Feature | Use Case |
|---------|----------|
| OLS regression | Factor models, beta estimation |
| Time series models | ARIMA, GARCH, VAR |
| Statistical tests | ADF test, Breusch-Pagan, Jarque-Bera |
| Rolling regression | Time-varying beta |

```python
import statsmodels.api as sm
model = sm.OLS(returns, factors).fit()
print(model.summary())
```

### arch

Volatility modeling.

| Feature | Use Case |
|---------|----------|
| GARCH models | Volatility forecasting |
| EGARCH, GJR-GARCH | Asymmetric volatility |
| Variance forecasting | Risk management, option pricing |

## Machine Learning

### scikit-learn

General-purpose machine learning.

| Feature | Use Case |
|---------|----------|
| Classification | Signal prediction (buy/sell/hold) |
| Regression | Return prediction |
| Clustering | Regime detection, asset grouping |
| Feature selection | Identifying predictive factors |
| Cross-validation | Avoiding overfitting |
| Pipeline | Reproducible preprocessing + modeling |

### XGBoost / LightGBM

Gradient boosting frameworks — often top performers for tabular financial data.

### TensorFlow / PyTorch

Deep learning for complex pattern recognition (NLP for news sentiment, time series forecasting with LSTMs/Transformers).

## Visualization

### matplotlib

Low-level plotting for full customization.

```python
import matplotlib.pyplot as plt
fig, axes = plt.subplots(2, 1, figsize=(15, 10))
axes[0].plot(prices.index, prices.close, label="Price")
axes[1].bar(returns.index, returns, label="Returns")
plt.show()
```

### seaborn

Statistical visualization built on matplotlib.

### plotly

Interactive charts — useful for exploring strategy behavior.

## Trading-Specific Libraries

| Library | Purpose |
|---------|---------|
| **TA-Lib** | 150+ technical analysis indicators (SMA, RSI, MACD, Bollinger) |
| **zipline** | Backtesting framework (originally from Quantopian) |
| **backtrader** | Event-driven backtesting framework |
| **bt** | Flexible backtesting for asset allocation strategies |
| **pyfolio** | Portfolio and risk analytics |
| **empyrical** | Common financial risk metrics |
| **alphalens** | Factor analysis and evaluation |
| **cvxpy** | Convex optimization for portfolio construction |

## Data Access Libraries

| Library | Purpose |
|---------|---------|
| **yfinance** | Yahoo Finance data (free, unofficial) |
| **pandas-datareader** | Multiple data sources (FRED, World Bank, etc.) |
| **alpha_vantage** | Free stock/forex/crypto API |
| **ccxt** | Unified crypto exchange API (100+ exchanges) |
| **ib_insync** | Interactive Brokers API wrapper |
| **polygon-api-client** | Polygon.io market data |

## Financial Application Notes

- Start with NumPy + Pandas + matplotlib — these cover 80% of research needs
- Add statsmodels for regression and time series analysis
- Add scikit-learn when exploring ML-based signals
- TA-Lib provides battle-tested indicator implementations — don't reinvent them
- pyfolio generates professional tearsheets for strategy evaluation
- cvxpy is the go-to for constrained portfolio optimization

## Summary

The Python ecosystem for algorithmic trading spans scientific computing (NumPy, SciPy), data manipulation (Pandas), statistics (statsmodels, arch), machine learning (scikit-learn, XGBoost), visualization (matplotlib, plotly), and specialized trading tools (TA-Lib, zipline, pyfolio, cvxpy). Mastering the right library for each task dramatically accelerates research and reduces bugs.

## Source

- Based on [QuantConnect: Key Concepts — Libraries](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/libraries)
