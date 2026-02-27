# Globals and Statics

## Overview

Covers state management in algorithmic trading: how to store and share data across event handlers, the risks of global and static variables, and best practices for managing algorithm state. Proper state management is critical for correctness and debugging.

## State in Trading Algorithms

Trading algorithms need to maintain state across multiple data events:

- **Indicator values**: Moving averages, RSI, Bollinger Bands
- **Position tracking**: Entry prices, stop-loss levels, trade counters
- **Signal history**: Recent signals for confirmation logic
- **Cached computations**: Covariance matrices, factor scores

## Instance Variables (Recommended)

The standard approach: store state as instance variables on the algorithm class.

```python
class MyStrategy:
    def initialize(self):
        self.lookback = 20
        self.entry_price = {}      # Dict of entry prices per symbol
        self.trade_count = 0
        self.last_rebalance = None
        self.signals = []          # Rolling signal history

    def on_data(self, data):
        self.trade_count += 1
        price = data["SPY"].close
        self.signals.append(price > self.sma.current.value)
```

**Advantages**:
- Scoped to the algorithm instance
- Easy to inspect and debug
- Clear ownership and lifecycle
- No risk of cross-algorithm contamination

## Global Variables (Use with Caution)

Global variables exist outside any class and persist for the algorithm's lifetime.

```python
# Module-level global
TRADE_LOG = []

class MyStrategy:
    def on_data(self, data):
        TRADE_LOG.append({"time": self.time, "price": data["SPY"].close})
```

### Risks of Globals

| Risk | Description |
|------|-------------|
| **Hidden dependencies** | Hard to trace what modifies the global |
| **Testing difficulty** | Globals persist between test runs, causing flaky tests |
| **Multi-instance conflicts** | If running multiple strategies, globals are shared |
| **Thread safety** | Concurrent access without locks causes race conditions |

### When Globals Are Acceptable

- **Constants**: `MAX_POSITION_SIZE = 0.10`, `TRADING_DAYS_PER_YEAR = 252`
- **Configuration**: Read-only settings loaded at startup
- **Logging**: Shared log handler (with thread-safe implementation)

## Static Variables

Class-level variables shared across all instances of a class.

```python
class RiskManager:
    MAX_DRAWDOWN = 0.20        # Class constant (OK)
    total_instances = 0         # Shared counter (risky)

    def __init__(self):
        RiskManager.total_instances += 1
```

Use static/class variables only for true constants. Use instance variables for mutable state.

## Rolling Windows

A common pattern for maintaining fixed-size state buffers:

```python
from collections import deque

class MyStrategy:
    def initialize(self):
        self.price_window = deque(maxlen=20)  # Auto-evicts old values
        self.return_window = deque(maxlen=252)

    def on_data(self, data):
        self.price_window.append(data["SPY"].close)
        if len(self.price_window) >= 2:
            ret = self.price_window[-1] / self.price_window[-2] - 1
            self.return_window.append(ret)
```

`deque(maxlen=N)` automatically removes the oldest element when the buffer is full — no manual cleanup needed.

## State Serialization

For live trading algorithms that may restart:

- **Save state** periodically (to file, database, or object store)
- **Restore state** on startup to resume without losing context
- Use JSON or pickle for simple state; databases for complex state
- Be careful with pickle — version changes can break deserialization

## Best Practices

1. **Prefer instance variables** over globals or statics
2. **Use constants** (uppercase) for immutable configuration
3. **Initialize all state** in the `initialize()` method — not scattered across handlers
4. **Use deque** for rolling windows instead of growing lists
5. **Avoid mutable class variables** — they create subtle bugs when multiple instances exist
6. **Document state variables** — future you will forget what `self.flag_3` means

## Financial Application Notes

- Indicator state (SMA values, RSI) is typically managed by indicator objects, not raw variables
- Entry/exit tracking state is critical for strategies with stop-losses and profit targets
- State serialization enables live trading resilience across restarts
- Keep state minimal — the more state you maintain, the more can go wrong

## Summary

Trading algorithms maintain state across events using instance variables (recommended), rolling windows (deque), and occasionally globals/statics (for constants only). Avoid mutable globals due to hidden dependencies, testing difficulties, and thread-safety risks. Initialize all state in the `initialize()` method and use `deque(maxlen=N)` for fixed-size buffers. For live trading, implement state serialization to survive restarts.

## Source

- Based on [QuantConnect: Key Concepts — Globals and Statics](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/globals-and-statics)
