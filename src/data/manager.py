"""Unified data manager — single entry point for all market data."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from src.data.cache import ParquetCache
from src.data.sources.yfinance_source import YFinanceSource


class DataManager:
    """Unified data access with caching.

    Usage:
        dm = DataManager()
        df = dm.get_ohlcv("AAPL")  # cached after first fetch
        df = dm.get_ohlcv("AAPL", start=date(2020, 1, 1))
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache = ParquetCache(cache_dir)
        self._yf = YFinanceSource()

    def get_ohlcv(
        self,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
        period: str = "5y",
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """Get OHLCV data, using cache when available."""
        resolution = "daily"

        if not force_refresh:
            cached = self._cache.read(symbol, resolution)
            if cached is not None and not cached.empty:
                if start is not None:
                    cached = cached[cached.index >= pd.Timestamp(start)]
                if end is not None:
                    cached = cached[cached.index <= pd.Timestamp(end)]
                if not cached.empty:
                    return cached

        # Fetch from source
        df = self._yf.get_ohlcv(symbol, start=start, end=end, period=period)
        if not df.empty:
            self._cache.update(symbol, df, resolution)

        return df

    def get_bulk_ohlcv(
        self,
        symbols: list[str],
        start: date | None = None,
        end: date | None = None,
        period: str = "5y",
    ) -> dict[str, pd.DataFrame]:
        """Get OHLCV data for multiple symbols."""
        results: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            df = self.get_ohlcv(symbol, start=start, end=end, period=period)
            if not df.empty:
                results[symbol] = df
        return results

    def get_info(self, symbol: str) -> dict:
        """Get fundamental info for a symbol."""
        return self._yf.get_info(symbol)

    def clear_cache(self, symbol: str | None = None) -> None:
        """Clear cached data."""
        self._cache.clear(symbol)
