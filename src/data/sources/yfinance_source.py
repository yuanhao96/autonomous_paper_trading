"""yfinance data source for OHLCV and fundamental data."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import yfinance as yf


class YFinanceSource:
    """Fetch OHLCV and info data from Yahoo Finance."""

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
        ticker = yf.Ticker(symbol)
        if start is not None:
            kwargs = {
                "start": start.isoformat(),
                "end": (end or date.today()).isoformat(),
            }
        else:
            kwargs = {"period": period}

        df = ticker.history(**kwargs)
        if df.empty:
            return df

        # Standardize columns
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        # Strip timezone — backtesting.py and Parquet cache expect tz-naive
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.index.name = "Date"
        return df

    def get_info(self, symbol: str) -> dict:
        """Get fundamental info for a symbol (market cap, sector, etc.)."""
        ticker = yf.Ticker(symbol)
        return dict(ticker.info)

    def get_bulk_ohlcv(
        self,
        symbols: list[str],
        start: date | None = None,
        end: date | None = None,
        period: str = "5y",
    ) -> dict[str, pd.DataFrame]:
        """Download OHLCV for multiple symbols."""
        results: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            try:
                df = self.get_ohlcv(symbol, start=start, end=end, period=period)
                if not df.empty:
                    results[symbol] = df
            except Exception:
                continue
        return results

    def search_symbols(self, query: str, max_results: int = 10) -> list[dict]:
        """Search for symbols matching a query string."""
        try:
            results = yf.Tickers(query)
            # yfinance doesn't have a great search API, return basic info
            return [{"symbol": query, "name": query}]
        except Exception:
            return []
