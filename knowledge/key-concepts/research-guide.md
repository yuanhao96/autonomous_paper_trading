# Research Guide

## Overview

Covers the quantitative research workflow for developing trading strategies: from idea generation through data exploration, hypothesis testing, backtesting, and production deployment. Establishes a systematic methodology to avoid common research pitfalls.

## The Research Workflow

```
Idea → Data Exploration → Hypothesis → Backtest → Validation → Deployment
  ↑                                                      |
  └──────────── Iterate on failures ─────────────────────┘
```

### Phase 1: Idea Generation

Sources for trading strategy ideas:
- Academic papers (SSRN, arXiv, Journal of Finance)
- Market anomalies literature (momentum, value, carry, etc.)
- Practitioner research (AQR, Two Sigma, Renaissance whitepapers)
- Market microstructure observations
- Cross-asset relationships and macro themes

### Phase 2: Data Exploration

Before coding a strategy, explore the data in a research notebook:

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load and inspect data
prices = pd.read_csv("spy_daily.csv", parse_dates=["date"], index_col="date")
print(prices.describe())
prices.close.plot(figsize=(15, 5), title="SPY Close Price")
plt.show()

# Compute returns
returns = np.log(prices.close).diff().dropna()
print(f"Mean daily return: {returns.mean():.6f}")
print(f"Daily volatility: {returns.std():.6f}")
print(f"Annualized Sharpe: {returns.mean() / returns.std() * np.sqrt(252):.2f}")
```

Key exploration steps:
- Check for missing data, outliers, and data quality issues
- Compute basic statistics (mean, std, skewness, kurtosis)
- Visualize distributions and time series
- Check for stationarity and structural breaks

### Phase 3: Hypothesis Formation

Formulate a clear, testable hypothesis:

| Component | Example |
|-----------|---------|
| **Signal** | 12-month momentum (past returns predict future returns) |
| **Universe** | US large-cap equities |
| **Direction** | Long top decile, short bottom decile |
| **Holding period** | Monthly rebalancing |
| **Expected Sharpe** | > 0.5 after costs |

### Phase 4: Backtesting

Implement and backtest the strategy:

```python
# Simple momentum backtest
lookback = 252  # 12 months
holding_period = 21  # 1 month

signals = returns.rolling(lookback).sum()
positions = signals.shift(1).apply(lambda x: 1 if x > 0 else -1)
strategy_returns = positions * returns

# Performance metrics
total_return = strategy_returns.sum()
sharpe = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)
max_dd = (strategy_returns.cumsum() - strategy_returns.cumsum().cummax()).min()
```

### Phase 5: Validation

Before trusting backtest results, validate rigorously:

#### Out-of-Sample Testing

Split data into in-sample (training) and out-of-sample (testing):
- **In-sample**: Develop and optimize the strategy
- **Out-of-sample**: Evaluate with untouched data
- Never optimize on out-of-sample data

#### Walk-Forward Analysis

Repeatedly train on expanding/rolling windows and test on subsequent periods:

```
Train: 2010-2015 → Test: 2016
Train: 2010-2016 → Test: 2017
Train: 2010-2017 → Test: 2018
...
```

#### Statistical Significance

- Is the Sharpe ratio statistically different from zero?
- How many independent trades contribute to the result?
- What's the p-value of the strategy's alpha?

### Phase 6: Deployment

Transition from research to production:
- Paper trade first (simulated orders, real data)
- Monitor for tracking error vs backtest
- Start with small position sizes
- Scale up gradually as confidence builds

## Common Research Pitfalls

### Look-Ahead Bias

Using information that wasn't available at the time of the trading decision:
- Using adjusted prices for decisions (adjustments applied retroactively)
- Using annual earnings data before the report date
- Using future index membership for stock selection

### Survivorship Bias

Only testing on stocks that survived to the present:
- Excludes delisted, bankrupt, and acquired companies
- Overstates historical returns
- Use point-in-time databases that include dead stocks

### Data Snooping / Overfitting

Testing many strategies on the same data until something "works":
- Apply multiple testing corrections (Bonferroni, FDR)
- Use out-of-sample validation
- Prefer simple strategies with economic rationale over complex curve-fitting

### Transaction Cost Neglect

Ignoring real trading costs:
- Commissions and fees
- Bid-ask spread (especially for illiquid stocks)
- Market impact (large orders move prices)
- Short borrowing costs

## Research Notebooks vs Production Code

| Aspect | Research Notebook | Production Algorithm |
|--------|------------------|---------------------|
| **Purpose** | Exploration, visualization | Execution, reliability |
| **Code style** | Exploratory, iterative | Clean, tested, modular |
| **Data** | Historical, static | Live streaming |
| **Speed** | Acceptable if slow | Must keep up with data |
| **Error handling** | Minimal | Robust |

## Financial Application Notes

- The research notebook is for exploration; never deploy notebook code directly to production
- Always separate signal research from execution logic
- Document every assumption and parameter choice for reproducibility
- Use version control for research notebooks (Jupyter + Git)
- Build a personal library of validated signals and utility functions

## Summary

The quantitative research workflow follows a disciplined path: idea generation, data exploration, hypothesis formation, backtesting, validation (out-of-sample testing, walk-forward analysis, statistical significance), and gradual deployment. Key pitfalls to avoid include look-ahead bias, survivorship bias, data snooping/overfitting, and transaction cost neglect. Research notebooks are for exploration; production code requires separate, robust implementations.

## Source

- Based on [QuantConnect: Key Concepts — Research Guide](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/research-guide)
