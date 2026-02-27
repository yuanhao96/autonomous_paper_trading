# Duck Typing

## Overview

Covers the duck typing paradigm in Python and its implications for algorithmic trading code. Duck typing allows flexible, interchangeable components in trading systems — different data sources, order types, and strategies can be used interchangeably if they share the same interface.

## What is Duck Typing?

"If it walks like a duck and quacks like a duck, then it must be a duck."

In Python, duck typing means an object's **behavior** (methods and properties) matters more than its **type**. If an object has the right methods, it can be used regardless of its class.

```python
# These work with ANY object that has a .close attribute
def get_return(bar):
    return bar.close / bar.open - 1

# Works with TradeBar, QuoteBar, or any custom bar type
trade_bar_return = get_return(trade_bar)
quote_bar_return = get_return(quote_bar)
custom_bar_return = get_return(custom_bar)
```

## Duck Typing in Trading Systems

### Interchangeable Data Sources

Different data sources can be used interchangeably if they provide the same interface:

```python
class CSVDataSource:
    def get_prices(self, symbol, start, end):
        # Load from CSV files
        return pd.read_csv(f"{symbol}.csv")

class APIDataSource:
    def get_prices(self, symbol, start, end):
        # Fetch from REST API
        return requests.get(f"/api/prices/{symbol}").json()

class DatabaseDataSource:
    def get_prices(self, symbol, start, end):
        # Query database
        return pd.read_sql(f"SELECT * FROM prices WHERE symbol='{symbol}'", conn)

# Strategy doesn't care which source it gets
def backtest(strategy, data_source):
    prices = data_source.get_prices("SPY", "2020-01-01", "2023-12-31")
    return strategy.run(prices)
```

### Interchangeable Strategy Components

```python
# Any object with a generate_signal method works
class MomentumSignal:
    def generate_signal(self, prices):
        return 1.0 if prices[-1] > prices[-20] else -1.0

class MeanReversionSignal:
    def generate_signal(self, prices):
        zscore = (prices[-1] - np.mean(prices[-20:])) / np.std(prices[-20:])
        return -1.0 if zscore > 2 else 1.0 if zscore < -2 else 0.0

class MLSignal:
    def generate_signal(self, prices):
        features = self.extract_features(prices)
        return self.model.predict(features)

# Portfolio manager uses any signal generator
def rebalance(signal_generator, prices):
    signal = signal_generator.generate_signal(prices)
    # ... execute trades based on signal
```

### Interchangeable Risk Models

```python
class SimpleStopLoss:
    def check_risk(self, position, current_price):
        return current_price < position.entry_price * 0.95

class TrailingStopLoss:
    def check_risk(self, position, current_price):
        return current_price < position.high_water_mark * 0.95

class VolatilityStopLoss:
    def check_risk(self, position, current_price):
        return current_price < position.entry_price - 2 * position.atr
```

## Protocols and Abstract Base Classes

For more formal interfaces, Python provides:

### typing.Protocol (Python 3.8+)

```python
from typing import Protocol
import pandas as pd

class DataSource(Protocol):
    def get_prices(self, symbol: str, start: str, end: str) -> pd.DataFrame: ...

class SignalGenerator(Protocol):
    def generate_signal(self, prices: pd.Series) -> float: ...
```

Protocols define the expected interface without requiring inheritance — true structural typing.

### Abstract Base Classes

```python
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def initialize(self): ...

    @abstractmethod
    def on_data(self, data): ...

    @abstractmethod
    def on_end_of_day(self): ...
```

ABCs enforce interface compliance at class definition time.

## EAFP vs LBYL

Python favors **EAFP** (Easier to Ask Forgiveness than Permission) over **LBYL** (Look Before You Leap):

```python
# LBYL (less Pythonic)
if hasattr(data, "SPY") and data["SPY"] is not None:
    price = data["SPY"].close

# EAFP (more Pythonic)
try:
    price = data["SPY"].close
except (KeyError, AttributeError):
    return  # No data available
```

## Financial Application Notes

- Duck typing enables modular strategy components that can be swapped without code changes
- Use Protocols for type-checking without forcing inheritance hierarchies
- Data source abstraction via duck typing enables easy switching between live and historical data
- Risk model interchangeability allows A/B testing different risk management approaches
- Keep interfaces small — a signal generator should only need `generate_signal()`, not inherit from a massive base class

## Summary

Duck typing in Python allows trading system components (data sources, signal generators, risk models, execution handlers) to be used interchangeably based on their interface rather than their class hierarchy. This enables modular, testable, and flexible algorithm architectures. Protocols and ABCs formalize interfaces when needed, and EAFP exception handling is the Pythonic way to handle missing data.

## Source

- Based on [QuantConnect: Key Concepts — Duck Typing](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/duck-typing)
