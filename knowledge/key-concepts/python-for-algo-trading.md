# Python for Algorithmic Trading

## Overview

Covers Python-specific patterns and best practices for algorithmic trading: why Python is the language of choice, performance considerations, common pitfalls, and integration with the C/C++ scientific computing ecosystem.

## Why Python for Trading

Python dominates quantitative finance for several reasons:

| Advantage | Description |
|-----------|-------------|
| **Rich ecosystem** | NumPy, Pandas, SciPy, scikit-learn, statsmodels, matplotlib |
| **Rapid prototyping** | Concise syntax enables fast strategy iteration |
| **Community** | Largest quant finance community; most tutorials and examples |
| **Interoperability** | Easy integration with C/C++ libraries for performance-critical code |
| **Readability** | Clear syntax reduces bugs in complex strategy logic |

## Performance Considerations

### Vectorized Operations

The most important Python performance pattern for trading: use NumPy/Pandas vectorized operations instead of Python loops.

```python
# Bad: Python loop (slow)
returns = []
for i in range(1, len(prices)):
    returns.append(prices[i] / prices[i-1] - 1)

# Good: Vectorized (fast)
returns = prices.pct_change()

# Bad: Loop for moving average
sma = []
for i in range(window, len(prices)):
    sma.append(np.mean(prices[i-window:i]))

# Good: Vectorized rolling
sma = prices.rolling(window).mean()
```

Vectorized operations are 10-100x faster because they execute in compiled C code under the hood.

### Avoid Repeated Computation

Cache expensive calculations rather than recomputing each bar:

```python
# Bad: Recalculate entire history every bar
def on_data(self, data):
    all_returns = np.log(self.history_prices).diff()
    volatility = all_returns.std() * np.sqrt(252)

# Good: Maintain rolling window
def on_data(self, data):
    self.window.append(data["SPY"].close)
    if len(self.window) >= self.lookback:
        returns = np.diff(np.log(self.window[-self.lookback:]))
        volatility = np.std(returns) * np.sqrt(252)
```

### Memory Management

- Use generators for large data processing instead of loading everything into memory
- Drop columns/rows you don't need from DataFrames
- Use appropriate dtypes (float32 vs float64 when precision isn't critical)

## Common Python Pitfalls in Trading

### Mutable Default Arguments

```python
# Bug: Shared mutable default
def add_signal(self, signals=[]):
    signals.append(self.current_signal)
    return signals
# Every call shares the same list!

# Fix: Use None as default
def add_signal(self, signals=None):
    if signals is None:
        signals = []
    signals.append(self.current_signal)
    return signals
```

### Float Comparison

```python
# Bug: Float equality comparison
if price == 100.0:  # May never be exactly True
    self.buy()

# Fix: Use tolerance
if abs(price - 100.0) < 0.01:
    self.buy()

# Or use numpy
if np.isclose(price, 100.0, atol=0.01):
    self.buy()
```

### Integer Division (Python 2 vs 3)

```python
# Python 2: 3/2 = 1 (integer division!)
# Python 3: 3/2 = 1.5 (float division)
# Always use: 3/2.0 or from __future__ import division
```

### Shallow vs Deep Copy

```python
import copy

# Shallow copy: nested objects still shared
portfolio_copy = self.weights.copy()

# Deep copy: fully independent
portfolio_copy = copy.deepcopy(self.weights)
```

## Type Hints for Trading Code

Type hints improve readability and catch bugs in complex strategy code:

```python
from typing import Dict, List, Optional
import pandas as pd

def calculate_signals(
    prices: pd.DataFrame,
    lookback: int = 20,
    threshold: float = 0.02
) -> Dict[str, float]:
    """Calculate trading signals for each symbol."""
    signals: Dict[str, float] = {}
    for symbol in prices.columns:
        returns = prices[symbol].pct_change(lookback).iloc[-1]
        if abs(returns) > threshold:
            signals[symbol] = 1.0 if returns > 0 else -1.0
    return signals
```

## Essential Libraries

| Library | Purpose |
|---------|---------|
| **NumPy** | Array operations, linear algebra, random numbers |
| **Pandas** | DataFrames, time series, financial data manipulation |
| **SciPy** | Optimization, statistics, signal processing |
| **scikit-learn** | Machine learning models |
| **statsmodels** | Statistical models, regression, time series analysis |
| **matplotlib** | Plotting and visualization |
| **ta-lib** | Technical analysis indicators |

## Financial Application Notes

- Pandas is the standard for handling financial time series in Python
- NumPy vectorization is non-negotiable for any strategy processing significant data
- Use type hints and docstrings — trading code is often revisited months later
- Test strategy logic with unit tests on known data before running full backtests
- Profile code with `cProfile` or `line_profiler` to find bottlenecks

## Summary

Python is the dominant language for algorithmic trading due to its rich ecosystem, rapid prototyping capability, and readability. Key performance patterns include vectorized operations (NumPy/Pandas instead of loops), caching expensive calculations, and proper memory management. Common pitfalls include mutable defaults, float comparison, and shallow copies. Type hints and thorough testing improve code quality for complex strategy codebases.

## Source

- Based on [QuantConnect: Key Concepts — Python and LEAN](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/python-and-lean)
