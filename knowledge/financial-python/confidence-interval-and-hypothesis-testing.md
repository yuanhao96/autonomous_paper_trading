# Confidence Interval and Hypothesis Testing

## Overview

Eighth article in the Introduction to Financial Python series by QuantConnect. Covers sampling error, confidence intervals, the Central Limit Theorem, hypothesis testing (null/alternative hypotheses), z-scores, p-values, and two-tailed tests. Demonstrates all concepts using S&P 500 (SPY) daily return data.

## Key Concepts

### Sample vs Population

When testing trading strategies, we work with samples (finite historical data) rather than the full population. Sample means differ from population means, necessitating confidence intervals to quantify estimation uncertainty.

### Confidence Interval

#### Standard Error

```
SE = σ / √n
```

Where σ is the sample standard deviation and n is the sample size. Larger samples produce smaller standard errors.

#### Computing Confidence Intervals

**Data setup**:
```python
from datetime import datetime
import numpy as np
qb = QuantBook()
spy = qb.AddEquity("SPY").Symbol
spy_table = qb.History(spy, datetime(2010, 8, 1), qb.Time, Resolution.Daily).loc[spy]
spy_total = spy_table[['open', 'close']]
spy_log_return = np.log(spy_total.close).diff().dropna()
print('Population mean:', np.mean(spy_log_return))
print('Population standard deviation:', np.std(spy_log_return))
```

**Comparing sample sizes**:
```python
print('10 days sample mean:', np.mean(spy_log_return.tail(10)))
print('10 days sample std:', np.std(spy_log_return.tail(10)))
print('1000 days sample mean:', np.mean(spy_log_return.tail(1000)))
print('1000 days sample std:', np.std(spy_log_return.tail(1000)))
```

**95% confidence interval formula**:
```
CI = (μ̄ - 1.96 × SE, μ̄ + 1.96 × SE)
```

```python
# 10-day sample
bottom_1 = np.mean(spy_log_return.tail(10)) - 1.96 * np.std(spy_log_return.tail(10)) / np.sqrt(len(spy_log_return.tail(10)))
upper_1 = np.mean(spy_log_return.tail(10)) + 1.96 * np.std(spy_log_return.tail(10)) / np.sqrt(len(spy_log_return.tail(10)))

# 1000-day sample
bottom_2 = np.mean(spy_log_return.tail(1000)) - 1.96 * np.std(spy_log_return.tail(1000)) / np.sqrt(len(spy_log_return.tail(1000)))
upper_2 = np.mean(spy_log_return.tail(1000)) + 1.96 * np.std(spy_log_return.tail(1000)) / np.sqrt(len(spy_log_return.tail(1000)))

print('10 days 95% CI:', (bottom_1, upper_1))
print('1000 days 95% CI:', (bottom_2, upper_2))
```

#### Common Confidence Levels

| Confidence Level | Critical Value (z) |
|-----------------|-------------------|
| 90% | 1.64 |
| 95% | 1.96 |
| 99% | 2.32 |

#### Three Sigma Rule (68-95-99.7)

```
P(μ - 1σ ≤ X ≤ μ + 1σ) ≈ 68.27%
P(μ - 2σ ≤ X ≤ μ + 2σ) ≈ 95.45%
P(μ - 3σ ≤ X ≤ μ + 3σ) ≈ 99.73%
```

#### Central Limit Theorem

Given a sufficiently large sample size from a population with finite variance, the distribution of sample means approximates a normal distribution. This justifies using z-scores and normal distribution critical values for confidence intervals.

### Hypothesis Testing

#### Setup

- **Null hypothesis (H₀)**: μ = 0 (the population mean return is zero)
- **Alternative hypothesis (H₁)**: μ ≠ 0 (the population mean return is not zero)

#### Confidence Interval Approach

**90% confidence interval around H₀**:
```python
mean_1000 = np.mean(spy_log_return.tail(1000))
std_1000 = np.std(spy_log_return.tail(1000))

bottom = 0 - 1.64 * std_1000 / np.sqrt(1000)
upper = 0 + 1.64 * std_1000 / np.sqrt(1000)
print((bottom, upper))
```

If the sample mean falls outside this interval, reject H₀ at the 90% confidence level.

**95% confidence interval**:
```python
bottom = 0 - 1.96 * std_1000 / np.sqrt(1000)
upper = 0 + 1.96 * std_1000 / np.sqrt(1000)
print((bottom, upper))
```

#### Z-Score Approach

```
z = (x̄ - μ₀) / (σ / √n)
```

```python
z_score = np.sqrt(1000) * (mean_1000 - 0) / std_1000
print(z_score)
```

#### P-Value

The probability of observing a result as extreme as the sample statistic, assuming H₀ is true.

```python
import scipy.stats as st
p_value = (1 - st.norm.cdf(z_score))
print(p_value)
```

**Two-tailed test**: The sample mean can be either positive enough or negative enough to reject the null hypothesis. For a two-tailed test, multiply the one-tail p-value by 2.

#### Effect of Sample Size

```python
mean_1200 = np.mean(spy_log_return.tail(1200))
std_1200 = np.std(spy_log_return.tail(1200))
z_score = np.sqrt(1200) * (mean_1200 - 0) / std_1200
print('z-score =', z_score)
p_value = (1 - st.norm.cdf(z_score))
print('p_value =', p_value)
```

**Key finding**: As sample size increases, the z-score increases and p-value decreases, making it easier to detect real effects (reject false null hypotheses).

## Financial Application Notes

- Confidence intervals quantify uncertainty in strategy backtests (e.g., "the true Sharpe ratio is between X and Y with 95% confidence")
- Hypothesis testing validates whether a strategy's return is statistically different from zero
- Larger backtesting periods provide more statistical power but may include regime changes
- P-values help distinguish skill from luck in trading strategy evaluation
- The Central Limit Theorem enables normal-distribution-based inference even when returns aren't perfectly normal

## Summary

Covers the statistical inference pipeline: computing standard errors from samples, constructing confidence intervals at various levels (90%, 95%, 99%), formulating null and alternative hypotheses, computing z-scores, and interpreting p-values for two-tailed tests. Larger sample sizes narrow confidence intervals and increase the power to detect real effects. These tools are essential for rigorous strategy evaluation.

## Source

- [QuantConnect: Confidence Interval and Hypothesis Testing](https://www.quantconnect.com/learning/articles/introduction-to-financial-python/confidence-interval-and-hypothesis-testing)
