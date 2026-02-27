# Random Variables and Distributions

## Overview

Seventh article in the Introduction to Financial Python series by QuantConnect. Covers random variables (discrete and continuous), probability distributions (PDF, CDF), uniform distribution, binomial distribution, and normal distribution. Demonstrates simulations with dice rolls, binomial trials, and SPY return analysis.

## Key Concepts

### Random Variables

A random variable is a drawing from a distribution whose outcome prior to the draw is uncertain.

| Type | Description | Example |
|------|-------------|---------|
| **Discrete** | Takes finite values | Dice rolls: {1, 2, 3, 4, 5, 6} |
| **Continuous** | Takes any value in a range | Rate of return: (-∞, +∞) |

### Distribution Functions

- **Probability Distribution Function**: Provides probabilities for different outcomes, P(X)
- **Cumulative Distribution Function (CDF)**: P(X ≤ x) — probability the random variable doesn't exceed x
- **Probability Density Function (PDF)**: Used for continuous distributions

### Uniform Distribution

All outcomes have equal probability.

**Dice simulation**:
```python
import random
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def dice():
    number = [1, 2, 3, 4, 5, 6]
    return random.choice(number)

series = np.array([dice() for x in range(10000)])

plt.figure(figsize=(20, 10))
plt.hist(series, bins=11, align='mid')
plt.xlabel('Dice Number')
plt.ylabel('Occurrences')
plt.grid()
plt.show()
```

**Cumulative probability check**:
```python
print(len([x for x in series if x <= 3]) / float(len(series)))
# Output: ~0.4956 (theoretical: 0.5)
print(np.mean(series))
# Output: ~3.5103 (theoretical: 3.5)
```

**Formulas**:
- Mean: `μ = (a + b) / 2`
- Variance: `σ² = (b - a)² / 12`

### Binomial Distribution

The number of successes in a sequence of n independent experiments, each with probability p.

**Notation**: X ~ B(n, p)

**Formula**: `P(X = k) = C(n,k) × p^k × (1-p)^(n-k)` where `C(n,k) = n! / ((n-k)! × k!)`

**Trial function** (success probability = 0.7):
```python
def trial():
    number = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    a = random.choice(number)
    return 1 if a <= 7 else 0

res = [trial() for x in range(10)]
print(sum(res))  # ~7
```

**Simulation (10,000 iterations)**:
```python
def binomial(number):
    l = []
    for i in range(10000):
        res = [trial() for x in range(10)]
        l.append(sum(res))
    return len([x for x in l if x == number]) / float(len(l))

prob = []
for i in range(1, 11):
    prob.append(binomial(i))
prob_s = pd.Series(prob, index=range(1, 11))
print(prob_s)
```

**Simulated vs theoretical probabilities** (n=10, p=0.7):
```
Successes  Simulated  Theoretical
7          ~0.267     0.2668
8          ~0.234     0.2335
```

**Theoretical verification**:
```python
from math import factorial
# P(X=7)
print((float(factorial(10)) / (factorial(7) * factorial(3))) * (0.7**7) * (0.3**3))
# Output: 0.266827932
# P(X=8)
print((float(factorial(10)) / (factorial(8) * factorial(2))) * (0.7**8) * (0.3**2))
# Output: 0.2334744405
```

**Formulas**:
- Mean: `μ = np`
- Variance: `σ² = np(1-p)`

### Normal Distribution

The most commonly used distribution in financial research.

**PDF formula**: `f(x) = (1/√(2πσ²)) × e^(-(x-μ)²/(2σ²))`

**Notation**: X ~ N(μ, σ²)

**Standard Normal**: μ = 0, σ = 1

#### SPY Returns Analysis

```python
from datetime import datetime
qb = QuantBook()
spy = qb.AddEquity("SPY").Symbol
spy_table = qb.History(spy, datetime(1998, 1, 1), qb.Time, Resolution.Daily).loc[spy]
spy = spy_table.loc['2009':'2017', ['open', 'close']]
spy['log_return'] = np.log(spy.close).diff()
spy = spy.dropna()
```

**Density plot**:
```python
plt.figure(figsize=(20, 10))
spy.log_return.plot.density()
plt.show()
```

**Key finding**: SPY log returns are approximately normal but with a taller peak (>0.6 vs 0.4 for standard normal) — indicating leptokurtosis (fat tails).

**Comparing distributions with different parameters**:
```python
de_2 = pd.Series(np.random.normal(0, 2, 10000), name='μ=0, σ=2')
de_3 = pd.Series(np.random.normal(0, 3, 10000), name='μ=0, σ=3')
de_0 = pd.Series(np.random.normal(0, 0.5, 10000), name='μ=0, σ=0.5')
mu_1 = pd.Series(np.random.normal(-2, 1, 10000), name='μ=-2, σ=1')
df = pd.concat([de_2, de_3, de_0, mu_1], axis=1)

plt.figure(figsize=(20, 10))
df.plot.density()
plt.show()
```

## Financial Application Notes

- Normal distribution underpins Black-Scholes options pricing, CAPM, and portfolio theory
- Real financial returns exhibit fat tails (leptokurtosis) — more extreme events than normal distribution predicts
- Binomial distribution is the basis for binomial tree option pricing models
- Understanding distributions is prerequisite for hypothesis testing, regression, and risk modeling
- Monte Carlo simulations rely on sampling from these distributions

## Summary

Covers discrete (uniform, binomial) and continuous (normal) probability distributions with simulations and financial data analysis. Key takeaway: while the normal distribution is the workhorse of quantitative finance, real financial returns deviate from normality with fatter tails. These distribution concepts are prerequisites for confidence intervals, hypothesis testing, and advanced financial models.

## Source

- [QuantConnect: Random Variables and Distributions](https://www.quantconnect.com/learning/articles/introduction-to-financial-python/random-variables-and-distributions)
