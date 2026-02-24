"""RSI Mean Reversion strategy.

Generates buy signals when the Relative Strength Index drops below an
oversold threshold and sell signals when it rises above an overbought
threshold, betting on price mean-reversion.
"""

from __future__ import annotations

import pandas as pd

from strategies.base import Strategy
from trading.executor import Signal


class RSIMeanReversionStrategy(Strategy):
    """Mean-reversion strategy driven by the RSI oscillator."""

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
    ) -> None:
        self._period: int = period
        self._oversold: float = oversold
        self._overbought: float = overbought

    @property
    def name(self) -> str:
        return "rsi_mean_reversion"

    @property
    def version(self) -> str:
        return "1.0.0"

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Return signals for the most recent bar based on RSI levels.

        A **buy** signal is emitted when RSI < ``oversold``; a **sell**
        signal when RSI > ``overbought``.  Signal strength reflects how
        far the RSI has moved past the threshold, normalised to [0, 1].
        """
        # Need at least period + 1 rows to compute one valid RSI value.
        if len(data) < self._period + 1:
            return []

        close: pd.Series = data["Close"]

        # --- RSI calculation ---------------------------------------------------
        delta: pd.Series = close.diff()
        gain: pd.Series = delta.clip(lower=0.0)
        loss: pd.Series = (-delta).clip(lower=0.0)

        avg_gain: pd.Series = gain.ewm(
            com=self._period - 1, min_periods=self._period
        ).mean()
        avg_loss: pd.Series = loss.ewm(
            com=self._period - 1, min_periods=self._period
        ).mean()

        rs: pd.Series = avg_gain / avg_loss
        rsi: pd.Series = 100.0 - 100.0 / (1.0 + rs)

        current_rsi: float = float(rsi.iloc[-1])

        # If RSI is NaN (insufficient data), no signal.
        if pd.isna(current_rsi):
            return []

        ticker: str = data.attrs.get("ticker", "UNKNOWN")
        signals: list[Signal] = []

        if current_rsi < self._oversold:
            # How far below the oversold line, normalised by the line itself.
            strength: float = min(
                (self._oversold - current_rsi) / self._oversold, 1.0
            )
            signals.append(
                Signal(
                    ticker=ticker,
                    action="buy",
                    strength=strength,
                    reason=(
                        f"RSI({self._period}) at {current_rsi:.1f} is below "
                        f"oversold threshold {self._oversold:.1f}"
                    ),
                    strategy_name=self.name,
                )
            )

        elif current_rsi > self._overbought:
            # How far above the overbought line, normalised by (100 - line).
            headroom: float = 100.0 - self._overbought
            strength = min(
                (current_rsi - self._overbought) / headroom, 1.0
            ) if headroom > 0.0 else 1.0
            signals.append(
                Signal(
                    ticker=ticker,
                    action="sell",
                    strength=strength,
                    reason=(
                        f"RSI({self._period}) at {current_rsi:.1f} is above "
                        f"overbought threshold {self._overbought:.1f}"
                    ),
                    strategy_name=self.name,
                )
            )

        return signals

    def describe(self) -> str:
        return (
            f"RSI Mean Reversion strategy (v{self.version}): buys when the "
            f"{self._period}-period RSI falls below {self._oversold:.0f} "
            f"(oversold) and sells when it rises above "
            f"{self._overbought:.0f} (overbought).  Signal strength is "
            f"proportional to how far the RSI has moved past the threshold."
        )
