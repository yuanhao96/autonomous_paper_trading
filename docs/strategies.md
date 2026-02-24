# Strategies

This document covers the strategy interface, how to create new strategies, the registry system, backtesting, auditor review, and the V1 starter strategies.

## Strategy Interface

All trading strategies inherit from the abstract base class `Strategy` defined in `strategies/base.py`.

```python
from abc import ABC, abstractmethod
import pandas as pd
from trading.executor import Signal

class Strategy(ABC):
    """Base class that all trading strategies must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this strategy (e.g. 'sma_crossover')."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Semantic version string (e.g. '1.0.0')."""

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Analyse OHLCV data and return a list of trading signals.

        Parameters
        ----------
        data:
            DataFrame with at least Open, High, Low, Close, Volume
            columns, indexed by date.

        Returns
        -------
        list[Signal]
            Zero or more signals for the most recent data point.
        """

    @abstractmethod
    def describe(self) -> str:
        """Return a human-readable description of the strategy."""
```

### The Signal dataclass

Strategies return `Signal` objects defined in `trading/executor.py`:

```python
@dataclass(frozen=True)
class Signal:
    ticker: str           # Stock symbol (e.g. "AAPL")
    action: str           # "buy" or "sell"
    strength: float       # 0.0 to 1.0 (conviction level)
    reason: str           # Human-readable explanation
    strategy_name: str    # Name of the originating strategy
```

- `action` must be either `"buy"` or `"sell"`.
- `strength` must be in `[0.0, 1.0]`. Higher strength signals are processed first and receive a larger position allocation.
- `reason` is logged and included in reports.
- `strategy_name` ties the signal back to its source for attribution.

---

## How to Create a New Strategy

### Step 1: Create the strategy file

Create a new Python file in the `strategies/` directory, for example `strategies/bollinger_breakout.py`.

### Step 2: Implement the Strategy ABC

```python
"""Bollinger Band breakout strategy."""

from __future__ import annotations
import pandas as pd
from strategies.base import Strategy
from trading.executor import Signal


class BollingerBreakoutStrategy(Strategy):
    """Buy when price breaks above the upper Bollinger Band,
    sell when it drops below the lower band."""

    def __init__(
        self,
        period: int = 20,
        num_std: float = 2.0,
    ) -> None:
        self._period = period
        self._num_std = num_std

    @property
    def name(self) -> str:
        return "bollinger_breakout"

    @property
    def version(self) -> str:
        return "1.0.0"

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        if len(data) < self._period + 1:
            return []

        close = data["Close"]
        sma = close.rolling(window=self._period).mean()
        std = close.rolling(window=self._period).std()

        upper = sma + self._num_std * std
        lower = sma - self._num_std * std

        current_close = float(close.iloc[-1])
        current_upper = float(upper.iloc[-1])
        current_lower = float(lower.iloc[-1])

        ticker = data.attrs.get("ticker", "UNKNOWN")
        signals: list[Signal] = []

        if current_close > current_upper:
            band_width = current_upper - current_lower
            strength = min(
                (current_close - current_upper) / band_width, 1.0
            ) if band_width > 0 else 0.5
            signals.append(
                Signal(
                    ticker=ticker,
                    action="buy",
                    strength=strength,
                    reason=(
                        f"Price {current_close:.2f} broke above upper "
                        f"Bollinger Band {current_upper:.2f}"
                    ),
                    strategy_name=self.name,
                )
            )
        elif current_close < current_lower:
            band_width = current_upper - current_lower
            strength = min(
                (current_lower - current_close) / band_width, 1.0
            ) if band_width > 0 else 0.5
            signals.append(
                Signal(
                    ticker=ticker,
                    action="sell",
                    strength=strength,
                    reason=(
                        f"Price {current_close:.2f} dropped below lower "
                        f"Bollinger Band {current_lower:.2f}"
                    ),
                    strategy_name=self.name,
                )
            )

        return signals

    def describe(self) -> str:
        return (
            f"Bollinger Breakout strategy (v{self.version}): buys when "
            f"price breaks above the {self._period}-period upper Bollinger "
            f"Band ({self._num_std} std devs), sells on lower band breach."
        )
```

### Step 3: Register the strategy

In `main.py` (or wherever you initialize the system), import and register your strategy:

```python
from strategies.registry import registry
from strategies.bollinger_breakout import BollingerBreakoutStrategy

registry.register(BollingerBreakoutStrategy())
```

### Key guidelines

- Return an empty list from `generate_signals()` when there is insufficient data (check `len(data)` against your lookback requirement).
- Use `data.attrs.get("ticker", "UNKNOWN")` to read the ticker symbol from the DataFrame attributes.
- Keep signal strength proportional to conviction. The executor uses strength to size positions: `shares = floor(strength * max_allocation / price)`.
- Provide a descriptive `reason` string -- it appears in execution logs and reports.
- Use only data available at the current bar. Accessing future data (e.g., `shift(-1)`) will trigger critical findings in the auditor's look-ahead bias check.

---

## How the Registry Works

The strategy registry (`strategies/registry.py`) is an in-memory store of named strategy instances.

### API

```python
from strategies.registry import registry

# Register a strategy instance
registry.register(my_strategy)

# Look up a strategy by name
strategy = registry.get("sma_crossover")  # returns Strategy or None

# List all registered strategy names
names = registry.list_strategies()  # returns list[str]

# Get all strategy instances
all_strategies = registry.get_all()  # returns list[Strategy]
```

### Behavior

- The registry is a module-level singleton: `registry = StrategyRegistry()`. All imports share the same instance.
- Strategies are keyed by their `name` property. Registering a strategy with the same name as an existing one replaces it.
- The daily trading cycle in `main.py` auto-registers the default strategies (SMA Crossover, RSI Mean Reversion) if the registry is empty.

---

## How Backtesting Evaluates Strategies

The backtester (`evaluation/backtester.py`) uses a walk-forward methodology to simulate strategy performance on historical data.

### BacktestConfig

```python
@dataclass
class BacktestConfig:
    train_window_days: int = 252   # ~1 year of training data
    test_window_days: int = 63     # ~3 months of test data
    step_days: int = 21            # ~1 month step between windows
```

The backtester slides a window across the historical data. In each iteration:

1. The first `train_window_days` rows are reserved as context (the strategy does not trade on them).
2. The next `test_window_days` rows are the test slice where the strategy generates signals.
3. The window advances by `step_days` for the next iteration.

### Simulation rules

- A **buy** signal opens a long position at the next trading day's open price.
- A **sell** signal (or end of window) closes the open position.
- Only one position is held at a time within each window.
- Position size is 100% of current equity (simplified for backtesting).

### BacktestResult

```python
@dataclass
class BacktestResult:
    trades: list[dict]           # Individual trade records
    equity_curve: pd.Series      # Portfolio value over time
    metrics: PerformanceSummary  # Sharpe, drawdown, win rate, P&L
    windows_used: int            # Number of walk-forward windows
```

Each trade record contains:

| Key | Type | Description |
|-----|------|-------------|
| `ticker` | str | Stock symbol |
| `entry_date` | str | Date of position entry |
| `exit_date` | str | Date of position exit |
| `side` | str | Always `"long"` in V1 |
| `entry_price` | float | Entry execution price (open) |
| `exit_price` | float | Exit execution price (open or close) |
| `pnl` | float | Dollar profit/loss |
| `return_pct` | float | Percentage return |

### PerformanceSummary

The metrics computed for every backtest:

| Metric | Description |
|--------|-------------|
| `sharpe_ratio` | Annualized Sharpe ratio (daily returns, 5% risk-free rate) |
| `max_drawdown` | Maximum peak-to-trough decline as a fraction |
| `win_rate` | Fraction of trades with positive P&L |
| `total_pnl` | Sum of all trade P&L |
| `avg_pnl` | Average P&L per trade |
| `best_trade` | Highest single-trade P&L |
| `worst_trade` | Lowest single-trade P&L |
| `num_trades` | Total number of trades |

### Running a backtest

```python
from evaluation.backtester import Backtester, BacktestConfig
from strategies.sma_crossover import SMACrossoverStrategy
from trading.data import get_ohlcv

strategy = SMACrossoverStrategy(short_window=20, long_window=50)
data = get_ohlcv("AAPL", period="2y", interval="1d")

backtester = Backtester(BacktestConfig(
    train_window_days=252,
    test_window_days=63,
    step_days=21,
))

result = backtester.run(strategy, data)

print(f"Sharpe: {result.metrics.sharpe_ratio:.2f}")
print(f"Max DD: {result.metrics.max_drawdown:.2%}")
print(f"Win Rate: {result.metrics.win_rate:.2%}")
print(f"Total P&L: ${result.metrics.total_pnl:,.2f}")
print(f"Trades: {result.metrics.num_trades}")
```

---

## How the Auditor Reviews Strategies

Before any strategy is promoted to live paper trading, it must pass the Auditor Agent's review. The auditor (`agents/auditor/agent.py`) runs four categories of checks.

### Check categories

#### 1. Look-ahead bias (`agents/auditor/checks/look_ahead_bias.py`)

Detects future information leaking into trading decisions through two methods:

- **Static code analysis** -- scans strategy source code for suspicious patterns:
  - `shift(-N)` -- accesses future rows in a time series.
  - `iloc[... + N]` -- positive offset relative to current index.
  - Open-ended `.loc[...: ]` slices that may include future data.
  - `DataFrame.lookup()` calls that can access arbitrary cells.
- **Trade date validation** -- checks that no trade enters before sufficient look-back data is available.
- **Perfect entry detection** -- flags strategies where every trade is profitable (100% win rate with 10+ trades is critical) or where the win rate exceeds 95% with 20+ trades (warning).

#### 2. Overfitting (`agents/auditor/checks/overfitting.py`)

Compares in-sample vs out-of-sample performance metrics. A large degradation between in-sample and out-of-sample results suggests the strategy has been over-fitted to historical data. This check runs only when both metric sets are provided to the auditor.

#### 3. Survivorship bias (`agents/auditor/checks/survivorship_bias.py`)

Checks whether the backtest universe includes only currently-listed tickers. If all tickers in the universe survived to the present day, the backtest may overstate returns by excluding delisted or bankrupt companies. This check runs only when tickers are provided.

#### 4. Data quality (`agents/auditor/checks/data_quality.py`)

Inspects OHLCV data and equity curves for:
- Missing values (NaN).
- Large gaps in the date index.
- Anomalous price movements.
- Insufficient data points.

### Severity levels

| Level | Meaning | Effect on audit |
|-------|---------|-----------------|
| `critical` | Fundamental flaw that invalidates results | Audit FAILS |
| `warning` | Potential issue that warrants investigation | Audit passes (noted in report) |
| `info` | Informational observation | Audit passes (noted in report) |

An audit passes only when there are **zero critical findings**.

### Running an audit

```python
from agents.auditor.agent import AuditorAgent
from evaluation.backtester import Backtester
from strategies.sma_crossover import SMACrossoverStrategy
from trading.data import get_ohlcv

# Run a backtest
strategy = SMACrossoverStrategy()
data = get_ohlcv("AAPL", period="2y", interval="1d")
result = Backtester().run(strategy, data)

# Read strategy source code
with open("strategies/sma_crossover.py") as f:
    source_code = f.read()

# Audit the results
auditor = AuditorAgent()
report = auditor.audit_backtest(
    backtest_result=result,
    strategy_code=source_code,
    tickers=["AAPL"],
)

print(f"Passed: {report.passed}")
print(f"Summary: {report.summary}")
for finding in report.findings:
    print(f"  [{finding.severity}] {finding.check_name}: {finding.description}")
```

---

## V1 Starter Strategies

### SMA Crossover (`strategies/sma_crossover.py`)

**Type:** Momentum / trend-following

**How it works:** Computes two simple moving averages (SMA) of closing prices -- a short-period SMA (default 20 bars) and a long-period SMA (default 50 bars). A **buy** signal is generated when the short SMA crosses above the long SMA (bullish crossover), indicating upward momentum. A **sell** signal is generated on the inverse crossover (short crosses below long).

**Parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `short_window` | 20 | Period for the short SMA |
| `long_window` | 50 | Period for the long SMA |

**Signal strength:** The normalized absolute distance between the two SMAs divided by the current closing price, capped at 1.0. A wider spread between the averages indicates stronger momentum.

**Data requirement:** Minimum `long_window + 1` bars (51 bars with defaults).

**Example:**

```python
from strategies.sma_crossover import SMACrossoverStrategy

strategy = SMACrossoverStrategy(short_window=10, long_window=30)
print(strategy.describe())
# SMA Crossover strategy (v1.0.0): generates a buy signal when the
# 10-period SMA crosses above the 30-period SMA, and a sell signal
# on the inverse crossover. Signal strength is proportional to the
# normalised distance between the two averages.
```

---

### RSI Mean Reversion (`strategies/rsi_mean_reversion.py`)

**Type:** Mean reversion / oscillator-based

**How it works:** Computes the Relative Strength Index (RSI) using exponential weighted moving averages of gains and losses. A **buy** signal is generated when the RSI drops below the oversold threshold (default 30), betting that the price will revert upward. A **sell** signal is generated when the RSI rises above the overbought threshold (default 70), anticipating a pullback.

**Parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `period` | 14 | RSI calculation period |
| `oversold` | 30.0 | RSI level below which a buy signal is generated |
| `overbought` | 70.0 | RSI level above which a sell signal is generated |

**Signal strength:** For buy signals, `(oversold - current_rsi) / oversold`, capped at 1.0. For sell signals, `(current_rsi - overbought) / (100 - overbought)`, capped at 1.0. The further past the threshold, the stronger the signal.

**Data requirement:** Minimum `period + 1` bars (15 bars with defaults).

**Example:**

```python
from strategies.rsi_mean_reversion import RSIMeanReversionStrategy

strategy = RSIMeanReversionStrategy(period=14, oversold=25, overbought=75)
print(strategy.describe())
# RSI Mean Reversion strategy (v1.0.0): buys when the 14-period RSI
# falls below 25 (oversold) and sells when it rises above 75
# (overbought). Signal strength is proportional to how far the RSI
# has moved past the threshold.
```

---

### Strategy comparison

| Aspect | SMA Crossover | RSI Mean Reversion |
|--------|---------------|--------------------|
| Type | Momentum | Mean reversion |
| Thesis | Trends persist | Extremes revert |
| Best market | Trending | Range-bound |
| Signal frequency | Low (crossovers are rare) | Moderate |
| Lookback data needed | 51 bars | 15 bars |
| Default parameters | 20/50 SMA | 14-period RSI, 30/70 |

Both strategies are registered automatically on the first run if no strategies are in the registry. They serve as baselines for the system's self-evaluation and evolution loop.
