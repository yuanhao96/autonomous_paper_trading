"""Abstract Strategy interface.

Every concrete strategy inherits from ``Strategy`` and implements
signal generation plus a human-readable description.  The framework
uses these methods for backtesting, live paper-trading, and reporting.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from trading.executor import Signal


class Strategy(ABC):
    """Base class that all trading strategies must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this strategy (e.g. ``'sma_crossover'``)."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Semantic version string (e.g. ``'1.0.0'``)."""

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Analyse OHLCV *data* and return a list of trading signals.

        Parameters
        ----------
        data:
            DataFrame with at least ``Open``, ``High``, ``Low``, ``Close``,
            ``Volume`` columns, indexed by date.

        Returns
        -------
        list[Signal]
            Zero or more signals for the most recent data point.
        """

    @abstractmethod
    def describe(self) -> str:
        """Return a human-readable description of the strategy."""
