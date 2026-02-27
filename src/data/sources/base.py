"""Abstract base class for data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class DataSource(ABC):
    """Abstract interface for market data sources.

    Implementations: YFinanceSource (current), future IBKR/Binance adapters.
    """

    @abstractmethod
    def get_ohlcv(
        self,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
        period: str = "5y",
    ) -> pd.DataFrame:
        """Download OHLCV data for a symbol.

        Returns DataFrame with columns: Open, High, Low, Close, Volume
        and a DatetimeIndex.
        """

    @abstractmethod
    def get_info(self, symbol: str) -> dict:
        """Get fundamental info for a symbol (market cap, sector, etc.)."""

    @abstractmethod
    def get_bulk_ohlcv(
        self,
        symbols: list[str],
        start: date | None = None,
        end: date | None = None,
        period: str = "5y",
    ) -> dict[str, pd.DataFrame]:
        """Download OHLCV for multiple symbols."""

    @abstractmethod
    def search_symbols(self, query: str, max_results: int = 10) -> list[dict]:
        """Search for symbols matching a query string."""
