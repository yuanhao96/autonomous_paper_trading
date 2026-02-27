# Rate of Return, Mean and Variance

## Overview

Sixth article in the Introduction to Financial Python series by QuantConnect. Introduces fundamental quantitative finance concepts: single-period and multi-period rate of return, logarithmic (continuously compounded) returns, arithmetic and geometric means, variance, and standard deviation. Demonstrates calculations using Apple stock data.

## Key Concepts

### Rate of Return

#### Single-Period Return

The basic return over one period:

```
r = (p_t / p_0) - 1 = (p_t - p_0) / p_0
```

Where `r` is the return, `p_t` is the price at time t, `p_0` is the initial price.

```python
import numpy as np
rate_return = 102.0 / 100 - 1
print(rate_return)
# Output: 0.02
```

#### Multi-Period (Cumulative) Return

Compounding across multiple periods:

```
r = (1 + r_1)(1 + r_2)(1 + r_3)...(1 + r_n) - 1
```

**Annualized return example**: A 6% quarterly return compounds to:
```
1 + r_annual = (1 + 0.06)^4 → r_annual ≈ 26.2%
```

#### Logarithmic Return

Continuous compounding leads to log returns:

```
r = ln(p_t / p_0) = ln(p_t) - ln(p_0)
```

**Key advantage**: Cumulative log return equals the sum of individual log returns.

```python
from datetime import datetime
qb = QuantBook()
aapl = qb.AddEquity("AAPL").Symbol
aapl_table = qb.History(aapl, datetime(1998, 1, 1), qb.Time, Resolution.Daily).loc[aapl]
aapl = aapl_table.loc['2017-3', ['open', 'close']]
aapl['log_price'] = np.log(aapl.close)
aapl['log_return'] = aapl['log_price'].diff()
print(aapl)
```

Output:
```
                 open      close  log_price  log_return
2017-03-01  32.210640  32.189492   3.471640         NaN
2017-03-02  32.403321  32.847428   3.491873    0.020233
2017-03-03  32.896773  32.652397   3.485918   -0.005955
```

**Monthly return via summation**:
```python
month_return = aapl.log_return.sum()
print(month_return)
# Output: 0.0494191398112811
```

**Mathematical proof**: `ln(p_t/p_0) = ln(p_t/p_{t-1}) + ln(p_{t-1}/p_{t-2}) + ... + ln(p_1/p_0)`

### Mean

#### Arithmetic Mean

```
μ = (Σ x_i) / n
```

```python
print(np.mean(aapl.log_price))
# Output: 3.4956395904827184
```

#### Geometric Mean

```
x̄ = (x_1 × x_2 × ... × x_n)^(1/n)
```

For returns: `(1 + r̄)^t = p_t / p_0`

The geometric mean is appropriate for growth rate series (compounding returns), while the arithmetic mean is appropriate for additive series (log returns).

### Variance

A measure of dispersion. In finance, variance is typically synonymous with risk — higher variance means higher risk.

```
σ² = Σ(x_i - μ)² / n
```

```python
print(np.var(aapl.log_price))
# Output: 0.00014725117002413818
```

### Standard Deviation

The square root of variance, in the same units as the original data:

```
σ = √(σ²) = √(Σ(x_i - μ)² / n)
```

```python
print(np.std(aapl.log_price))
# Output: 0.012134709309420568
```

## Financial Application Notes

- Log returns are preferred in quantitative finance because they are additive across time periods
- Arithmetic mean is used for log returns; geometric mean is used for simple returns
- Variance and standard deviation measure portfolio risk
- Annualized volatility = daily σ × √252 (trading days per year)
- These concepts are prerequisites for hypothesis testing, regression analysis, and portfolio optimization

## Summary

Covers three return calculation methods (single-period, multi-period compounding, logarithmic), two types of means (arithmetic and geometric), and two dispersion measures (variance and standard deviation). Log returns are the standard in quantitative finance due to their additive property across time periods.

## Source

- [QuantConnect: Rate of Return, Mean and Variance](https://www.quantconnect.com/learning/articles/introduction-to-financial-python/rate-of-return,-mean-and-variance)
