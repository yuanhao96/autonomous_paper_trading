# Multiple Linear Regression

## Overview

Tenth article in the Introduction to Financial Python series by QuantConnect. Extends simple regression to multiple predictors, covers the Fama-French 5-factor model implementation, F-tests for overall model significance, residual analysis (normality, homoskedasticity), and practical comparison of simple vs multi-factor models for predicting Amazon returns.

## Key Concepts

### The Multiple Regression Model

```
Y = α + β₁X₁ + β₂X₂ + ... + βₚXₚ + ε
```

Extends simple linear regression (Y = α + βX + ε) by including p predictor variables.

### Python Implementation

**Data setup** — Amazon returns with SPY, AAPL, EBAY, WMT as predictors (2016):
```python
from datetime import datetime
import numpy as np
qb = QuantBook()
symbols = [qb.AddEquity(ticker).Symbol
    for ticker in ["SPY", "AAPL", "AMZN", "EBAY", "WMT"]]

history = qb.History(symbols, datetime(2016, 1, 1),
                     datetime(2017, 1, 1), Resolution.Daily)
df = np.log(history.close.unstack(0)).diff().dropna()
```

**Simple regression** (baseline):
```python
import statsmodels.formula.api as sm
simple = sm.ols(formula='AMZN ~ SPY', data=df).fit()
print(simple.summary())
# SPY coefficient: 1.0695, p-value: 0.000, R² = 0.234
```

**Multiple regression**:
```python
model = sm.ols(formula='AMZN ~ SPY + AAPL + EBAY + WMT', data=df).fit()
print(model.summary())
# R² = 0.254
```

**Key property**: R² cannot decrease as variables are added. The multiple model improved R² from 0.234 to 0.254, though additional predictors may lack statistical significance.

### Fama-French 5-Factor Model

A well-known asset pricing model with 5 factors:
- **Mkt-RF**: Market excess return
- **SMB**: Small Minus Big (size factor)
- **HML**: High Minus Low (value factor)
- **RMW**: Robust Minus Weak (profitability factor)
- **CMA**: Conservative Minus Aggressive (investment factor)

**Data download**:
```python
url = 'https://raw.githubusercontent.com/QuantConnect/Tutorials/master/Data/F-F_Research_Data_5_Factors_2x3.CSV'
response = qb.Download(url).replace(' ', '')
lines = [x.split(',') for x in response.split('\n')[4:]
    if len(x.split(',')[0]) == 6]

records = {datetime.strptime(line[0], "%Y%m"): line[1:]
           for line in lines}
fama_table = pd.DataFrame.from_dict(records, orient='index',
    columns=['Mkt-RF', 'SMB', 'HML', 'RMW', 'CMA', 'RF'])
```

**Fitting the model**:
```python
fama = fama_table['2016']
fama_df = pd.concat([fama, amzn_log], axis=1)
fama_model = sm.ols(formula='Close ~ MKT + SMB + HML + RMW + CMA',
                    data=fama_df).fit()
print(fama_model.summary())
# R² = 0.387
```

**Prediction comparison** (simple vs Fama-French vs actual):
```python
result = pd.DataFrame({
    'simple regression': simple.predict(),
    'fama_french': fama_model.predict(),
    'sample': df.amzn
}, index=df.index)

plt.figure(figsize=(15, 7.5))
plt.plot(result['2016-7':'2016-9'].index,
         result.loc['2016-7':'2016-9', 'simple regression'])
plt.plot(result['2016-7':'2016-9'].index,
         result.loc['2016-7':'2016-9', 'fama_french'])
plt.plot(result['2016-7':'2016-9'].index,
         result.loc['2016-7':'2016-9', 'sample'])
plt.legend()
plt.show()
```

### F-Test (Overall Model Significance)

Tests whether any predictor is useful:

- **H₀**: β₁ = β₂ = ... = βₚ = 0 (no predictor matters)
- **H₁**: At least one βᵢ ≠ 0

For the Fama-French model, p-value = 2.21e-24 — highly significant.

Note: In simple regression, the F-test is equivalent to the t-test on the slope.

### Residual Analysis

#### Normality of Residuals

```python
plt.figure()
fama_model.resid.plot.density()
plt.show()

print(f'Residual mean: {np.mean(fama_model.resid)}')
# Output: -2.31e-16 (essentially zero)
print(f'Residual variance: {np.var(fama_model.resid)}')
# Output: 0.000205
```

Residuals should be normally distributed with mean zero.

#### Homoskedasticity (Constant Variance)

**Visual check**:
```python
plt.figure(figsize=(20, 10))
plt.scatter(df.spy, simple.resid)
plt.axhline(0.05)
plt.axhline(-0.05)
plt.xlabel('X value')
plt.ylabel('Residual')
plt.show()
```

**Breusch-Pagan test**:
```python
from statsmodels.stats import diagnostic as dia
het = dia.het_breuschpagan(fama_model.resid,
    fama_df[['MKT', 'SMB', 'HML', 'RMW', 'CMA']][1:])
print(f'p-value: {het[-1]}')
# Output: 0.144 (fail to reject H₀ — no heteroskedasticity detected)
```

At the 95% significance level, we cannot reject constant variance — the homoskedasticity assumption holds.

## Financial Application Notes

- The Fama-French model is the standard for academic and professional asset pricing research
- R² increasing from 0.234 (single-factor) to 0.387 (5-factor) shows the value of multi-factor models
- Adding predictors always increases R² — use adjusted R² or information criteria to penalize model complexity
- Residual diagnostics (normality, homoskedasticity) validate model assumptions
- Violations of assumptions (heteroskedasticity, non-normal residuals) can invalidate inference
- The `statsmodels` library provides a comprehensive regression toolkit matching R's functionality

## Summary

Extends simple regression to multiple predictors, demonstrates the Fama-French 5-factor model as a practical financial application, covers model significance testing (F-test), and introduces residual diagnostics (normality testing, Breusch-Pagan heteroskedasticity test). The Fama-French model substantially improved explanatory power (R² = 0.387 vs 0.234) for Amazon returns.

## Source

- [QuantConnect: Multiple Linear Regression](https://www.quantconnect.com/learning/articles/introduction-to-financial-python/multiple-linear-regression)
