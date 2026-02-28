"""Unified data manager — single entry point for all market data."""

from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.data.cache import ParquetCache
from src.data.sources.yfinance_source import YFinanceSource

# Approximate trading-day spans for yfinance period strings
_PERIOD_MIN_DAYS: dict[str, int] = {
    "1mo": 20,
    "3mo": 60,
    "6mo": 120,
    "1y": 220,
    "2y": 450,
    "5y": 1200,
    "10y": 2400,
    "max": 0,  # no minimum
}


class DataManager:
    """Unified data access with caching.

    Usage:
        dm = DataManager()
        df = dm.get_ohlcv("AAPL")  # cached after first fetch
        df = dm.get_ohlcv("AAPL", start=date(2020, 1, 1))
    """

    def __init__(self, cache_dir: Path | None = None, cache_ttl_hours: int = 24) -> None:
        self._cache = ParquetCache(cache_dir)
        self._yf = YFinanceSource()
        self._cache_ttl_seconds = cache_ttl_hours * 3600

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

        # For period-based calls (no explicit date range), expire stale cache
        if not force_refresh and start is None and end is None:
            cache_path = self._cache._path(symbol, resolution)
            if cache_path.exists():
                age = time.time() - cache_path.stat().st_mtime
                if age > self._cache_ttl_seconds:
                    force_refresh = True

        if not force_refresh:
            cached = self._cache.read(symbol, resolution)
            if cached is not None and not cached.empty:
                if start is not None:
                    cached = cached[cached.index >= pd.Timestamp(start)]
                if end is not None:
                    cached = cached[cached.index <= pd.Timestamp(end)]
                if not cached.empty:
                    # Validate coverage: cached data must span the requested range
                    # (within 5 trading days tolerance for weekends/holidays)
                    cache_ok = True
                    if start is not None:
                        delta = (cached.index[0] - pd.Timestamp(start)).days
                        if delta > 5:
                            cache_ok = False
                    if end is not None:
                        delta = (pd.Timestamp(end) - cached.index[-1]).days
                        if delta > 5:
                            cache_ok = False

                    # Period-based calls: verify cached data has enough bars
                    if cache_ok and start is None and end is None:
                        min_bars = _PERIOD_MIN_DAYS.get(period, 0)
                        if min_bars > 0 and len(cached) < min_bars:
                            cache_ok = False

                    if cache_ok:
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
