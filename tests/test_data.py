"""Tests for trading.data — market data fetching and caching."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_history(n: int = 50) -> pd.DataFrame:
    """Build a simple OHLCV DataFrame that yfinance.Ticker.history would return."""
    dates = pd.bdate_range("2023-06-01", periods=n)
    return pd.DataFrame(
        {
            "Open": [150.0] * n,
            "High": [155.0] * n,
            "Low": [145.0] * n,
            "Close": [152.0] * n,
            "Volume": [1_000_000] * n,
            "Dividends": [0.0] * n,
            "Stock Splits": [0.0] * n,
        },
        index=dates,
    )


# ---------------------------------------------------------------------------
# Tests — get_ohlcv
# ---------------------------------------------------------------------------


class TestGetOhlcv:
    def test_fetches_from_yfinance(self, tmp_path: Path) -> None:
        """First call should fetch from yfinance and cache to parquet."""
        mock_history = _make_mock_history()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_history

        with (
            patch("trading.data.yf.Ticker", return_value=mock_ticker),
            patch("trading.data._load_cache_dir", return_value=tmp_path),
        ):
            from trading.data import get_ohlcv

            df = get_ohlcv("AAPL", period="3mo", interval="1d")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 50
        # Extra columns (Dividends, Stock Splits) should be dropped.
        assert "Dividends" not in df.columns
        assert "Stock Splits" not in df.columns
        assert set(df.columns) == {"Open", "High", "Low", "Close", "Volume"}

        # A parquet cache file should have been written.
        cache_files = list(tmp_path.glob("*.parquet"))
        assert len(cache_files) == 1

    def test_caching_uses_cache_on_second_call(self, tmp_path: Path) -> None:
        """Second call with daily interval should use the parquet cache."""
        mock_history = _make_mock_history()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_history

        with (
            patch("trading.data.yf.Ticker", return_value=mock_ticker),
            patch("trading.data._load_cache_dir", return_value=tmp_path),
        ):
            from trading.data import get_ohlcv

            # First call — fetches and caches.
            df1 = get_ohlcv("TSLA", period="1y", interval="1d")
            # Second call — should read from cache.
            df2 = get_ohlcv("TSLA", period="1y", interval="1d")

        # yfinance history should have been called only once (second call
        # reads the cache).
        assert mock_ticker.history.call_count == 1
        pd.testing.assert_frame_equal(df1, df2, check_freq=False)

    def test_empty_response(self, tmp_path: Path) -> None:
        """yfinance returning empty DataFrame should propagate cleanly."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()

        with (
            patch("trading.data.yf.Ticker", return_value=mock_ticker),
            patch("trading.data._load_cache_dir", return_value=tmp_path),
        ):
            from trading.data import get_ohlcv

            df = get_ohlcv("INVALID", period="1y", interval="1d")

        assert df.empty

    def test_intraday_never_cached(self, tmp_path: Path) -> None:
        """Intraday intervals should always refetch (no caching)."""
        mock_history = _make_mock_history(10)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_history

        with (
            patch("trading.data.yf.Ticker", return_value=mock_ticker),
            patch("trading.data._load_cache_dir", return_value=tmp_path),
        ):
            from trading.data import get_ohlcv

            get_ohlcv("AAPL", period="5d", interval="1h")
            get_ohlcv("AAPL", period="5d", interval="1h")

        # Both calls should fetch because intraday is never cached.
        assert mock_ticker.history.call_count == 2
