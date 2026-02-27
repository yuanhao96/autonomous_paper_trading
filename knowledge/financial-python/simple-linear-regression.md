# Simple Linear Regression

## Overview

Ninth article in the Introduction to Financial Python series by QuantConnect. Covers the fundamentals of simple linear regression: the OLS (Ordinary Least Squares) method, slope and intercept estimation, parameter significance testing (t-statistics, p-values), model significance (R-squared), and visualization. Demonstrates with Amazon vs S&P 500 return data.

## Key Concepts

### The Linear Model

```
Y = α + βX + ε
```

Where:
- `Y` = dependent variable (response)
- `X` = independent variable (predictor)
- `α` = intercept
- `β` = slope
- `ε` = error term (residual)

### OLS Estimation

Ordinary Least Squares minimizes the sum of squared residuals to find the best-fit line.

**Slope**:
```
β̂ = Σ(xᵢ - x̄)(yᵢ - ȳ) / Σ(xᵢ - x̄)²
```

**Intercept**:
```
α̂ = ȳ - β̂x̄
```

### Python Implementation

**Data setup** — Amazon and SPY daily log returns (Jan–Jun 2017):
```python
from datetime import datetime
import numpy as np
qb = QuantBook()
tickers = ["AMZN", "SPY"]
symbols = [qb.AddEquity(ticker).Symbol for ticker in tickers]
history = qb.History(symbols, datetime(2017, 1, 1),
                     datetime(2017, 6, 30), Resolution.Daily)
df = np.log(history.close.unstack(0)).diff().dropna()
df.columns = tickers
```

**Fitting the model with statsmodels**:
```python
import statsmodels.formula.api as sm
model = sm.ols(formula='AMZN ~ SPY', data=df).fit()
print(model.summary())
```

**Accessing results**:
```python
print(f'Parameters: {model.params}')
# Intercept: 0.001504, SPY: 0.937181

print(f'Residuals: {model.resid.tail()}')
print(f'Fitted values: {model.predict()}')
```

**Visualization**:
```python
import matplotlib.pyplot as plt
plt.figure(figsize=(15, 10))
plt.scatter(df.SPY, df.AMZN)
plt.xlabel('SPY Return')
plt.ylabel('AMZN Return')
plt.plot(df.SPY, model.predict(), color='red')
plt.show()
```

### Parameter Significance

#### Hypothesis Test for β

- **H₀**: β = 0 (no linear relationship)
- **H₁**: β ≠ 0 (linear relationship exists)

#### T-Statistic

```
t = β̂ / SE(β̂)
```

#### Standard Error of β

```
SE(β̂) = √[(1/(n-2)) × Σε̂² / Σ(xᵢ - x̄)²]
```

**Interpretation**: In the AMZN ~ SPY example:
- SPY coefficient p-value ≈ 0 → >99.99% confidence that β ≠ 0
- Intercept p-value = 0.923 → only 7.7% confidence that α ≠ 0 (not significant)

### Model Significance (R-squared)

#### Sum of Squared Errors (SSE)

```
SSE = Σ(yᵢ - ŷᵢ)² = Σε̂ᵢ²
```

#### Total Sum of Squares (SS)

```
SS = Σ(yᵢ - ȳ)²
```

#### Coefficient of Determination

```
R² = 1 - SSE/SS = 1 - Σ(yᵢ - ŷᵢ)² / Σ(yᵢ - ȳ)²
```

- R² ranges from 0 to 1
- R² = 0: the model explains none of the variance
- R² = 1: the model explains all of the variance
- R² measures the proportion of variation in Y explained by the linear relationship with X

## Financial Application Notes

- Linear regression is the foundation of CAPM (β measures market sensitivity)
- The Fama-French model extends simple regression to multiple factors
- The slope (β) in AMZN ~ SPY represents Amazon's market beta
- A non-significant intercept (α ≈ 0) is consistent with market efficiency
- R² indicates how much of a stock's return is explained by market movements
- Residuals represent idiosyncratic (stock-specific) risk

## Summary

Covers the complete simple linear regression workflow: model specification (Y = α + βX + ε), OLS estimation of slope and intercept, implementation with `statsmodels`, parameter significance testing via t-statistics and p-values, and model evaluation via R-squared. The AMZN vs SPY example demonstrates how regression quantifies the relationship between a stock's returns and market returns.

## Source

- [QuantConnect: Simple Linear Regression](https://www.quantconnect.com/learning/articles/introduction-to-financial-python/simple-linear-regression)
