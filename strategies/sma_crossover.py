"""SMA Crossover strategy.

Generates buy/sell signals based on a short-period simple moving average
crossing above or below a long-period simple moving average of closing
prices.
"""

from __future__ import annotations

import pandas as pd

from strategies.base import Strategy
from trading.executor import Signal


class SMACrossoverStrategy(Strategy):
    """Classic dual-SMA crossover momentum strategy."""

    def __init__(
        self,
        short_window: int = 20,
        long_window: int = 50,
    ) -> None:
        self._short_window: int = short_window
        self._long_window: int = long_window

    @property
    def name(self) -> str:
        return "sma_crossover"

    @property
    def version(self) -> str:
        return "1.0.0"

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Return signals for the most recent bar based on SMA crossover.

        A **buy** signal is emitted when the short SMA crosses *above* the
        long SMA (i.e. short > long on the last bar while short <= long on
        the previous bar).  A **sell** signal is the mirror case.

        Signal strength is the normalised absolute distance between the two
        SMAs relative to the closing price.
        """
        if len(data) < self._long_window + 1:
            return []

        close: pd.Series = data["Close"]
        short_sma: pd.Series = close.rolling(window=self._short_window).mean()
        long_sma: pd.Series = close.rolling(window=self._long_window).mean()

        # Current and previous bar values.
        cur_short: float = float(short_sma.iloc[-1])
        cur_long: float = float(long_sma.iloc[-1])
        prev_short: float = float(short_sma.iloc[-2])
        prev_long: float = float(long_sma.iloc[-2])

        ticker: str = data.attrs.get("ticker", "UNKNOWN")
        signals: list[Signal] = []

        # Normalised distance between SMAs (capped at 1.0).
        cur_close: float = float(close.iloc[-1])
        if cur_close != 0.0:
            strength: float = min(abs(cur_short - cur_long) / cur_close, 1.0)
        else:
            strength = 0.0

        # Bullish crossover: short crosses above long.
        if cur_short > cur_long and prev_short <= prev_long:
            signals.append(
                Signal(
                    ticker=ticker,
                    action="buy",
                    strength=strength,
                    reason=(
                        f"SMA{self._short_window} crossed above SMA{self._long_window} "
                        f"(short={cur_short:.2f}, long={cur_long:.2f})"
                    ),
                    strategy_name=self.name,
                )
            )

        # Bearish crossover: short crosses below long.
        elif cur_short < cur_long and prev_short >= prev_long:
            signals.append(
                Signal(
                    ticker=ticker,
                    action="sell",
                    strength=strength,
                    reason=(
                        f"SMA{self._short_window} crossed below SMA{self._long_window} "
                        f"(short={cur_short:.2f}, long={cur_long:.2f})"
                    ),
                    strategy_name=self.name,
                )
            )

        return signals

    def describe(self) -> str:
        return (
            f"SMA Crossover strategy (v{self.version}): generates a buy signal "
            f"when the {self._short_window}-period SMA crosses above the "
            f"{self._long_window}-period SMA, and a sell signal on the inverse "
            f"crossover.  Signal strength is proportional to the normalised "
            f"distance between the two averages."
        )
