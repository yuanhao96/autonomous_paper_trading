# NumPy and Basic Pandas

## Overview

Fourth article in the Introduction to Financial Python series by QuantConnect. Introduces NumPy for scientific computing (arrays, mathematical operations, statistics) and Pandas Series for labeled one-dimensional data with financial time series examples.

## Key Concepts

### NumPy

NumPy is the core library for scientific computing in Python, providing high-performance multidimensional arrays and mathematical tools.

```python
import numpy as np
```

#### Creating Arrays

**From a list**:
```python
price_list = [143.73, 145.83, 143.68, 144.02, 143.5, 142.62]
price_array = np.array(price_list)
print(f'{price_array} {type(price_array)}')
# Output: [143.73 145.83 143.68 144.02 143.5 142.62] <class 'numpy.ndarray'>
```

**2D arrays (matrices)**:
```python
Ar = np.array([[1, 3], [2, 4]])
print(Ar.shape)  # (2, 2)
```

#### Indexing and Slicing

```python
# Row access
print(Ar[0])      # [1 3]
print(Ar[1])      # [2 4]

# Column access
print(Ar[:, 0])   # [1 2] — first column
print(Ar[:, 1])   # [3 4] — second column
```

#### Element-wise Operations

```python
np.log(price_array)
# Output: [4.96793654 4.98244156 4.9675886 4.96995218 4.96633504 4.96018375]
```

#### Statistical Functions

```python
np.mean(price_array)   # 143.896666667
np.std(price_array)    # 0.967379047852
np.sum(price_array)    # 863.38
np.max(price_array)    # 145.83
```

### Pandas Series

A Series is a one-dimensional labeled array capable of holding any data type (integers, strings, floats, Python objects).

```python
import pandas as pd
```

#### Creating a Series

**Basic (auto-indexed)**:
```python
price = [143.73, 145.83, 143.68, 144.02, 143.5, 142.62]
s = pd.Series(price)
# 0    143.73
# 1    145.83
# ...
```

**With custom index**:
```python
s = pd.Series(price, index=['a', 'b', 'c', 'd', 'e', 'f'])
```

**With name attribute**:
```python
s = pd.Series(price, name='Apple Prices')
print(s.name)  # Apple Prices
```

#### Changing Index

```python
s.index = [6, 5, 4, 3, 2, 1]
```

#### Slicing

```python
s[1:]     # all elements except first
s[:-2]    # all elements except last two
```

#### Time Index

```python
time_index = pd.date_range('2017-01-01', periods=len(s), freq='D')
s.index = time_index
# 2017-01-01    143.73
# 2017-01-02    145.83
# ...
```

#### Indexing Methods

| Method | Description | Example |
|--------|-------------|---------|
| `s[label]` | Access by index label | `s[1]` returns value at label 1 |
| `s.iloc[n]` | Access by integer position | `s.iloc[1]` returns second element |
| `s.loc[label]` | Access by label explicitly | `s.loc['2017-01-03']` |
| Date string | Access by date | `s['2017-01-03']` |
| Date range | Slice by date range | `s['2017-01-02':'2017-01-05']` |

**Important distinction**: When using non-default indices, `s[1]` accesses the label `1`, while `s.iloc[1]` accesses the second position. These may differ.

#### Conditional Selection

```python
# Values below the mean
s[s < np.mean(s)]

# Values within one standard deviation above the mean
s[(s > np.mean(s)) & (s < np.mean(s) + 1.64 * np.std(s))]
```

**Logical operators for Series**: `&` (and), `|` (or), `~` (not)

#### Descriptive Statistics

```python
s.describe()
# count      6.000000
# mean     143.896667
# std        1.059711
# min      142.620000
# 25%      143.545000
# 50%      143.705000
# 75%      143.947500
# max      145.830000
```

## Financial Application Notes

- NumPy arrays enable vectorized operations on price data (log returns, statistics) — much faster than Python loops
- Pandas Series with DatetimeIndex is the standard way to represent financial time series
- `iloc` vs `loc` distinction is critical when working with custom indices (dates, tickers)
- Conditional selection enables filtering (e.g., finding days where price exceeded a threshold)
- `describe()` provides a quick statistical summary of any financial time series

## Summary

Introduces NumPy arrays (creation, indexing, element-wise operations, statistical functions) and Pandas Series (labeled 1D arrays with custom indices, time indices, multiple indexing methods, conditional selection, and descriptive statistics). These are the fundamental data structures for all financial data analysis in Python.

## Source

- [QuantConnect: NumPy and Basic Pandas](https://www.quantconnect.com/learning/articles/introduction-to-financial-python/numpy-and-basic-pandas)
