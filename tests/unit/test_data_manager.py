"""Tests for DataManager mtime-based cache TTL."""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data.manager import DataManager


def _make_ohlcv(n: int = 10) -> pd.DataFrame:
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    close = pd.Series([100 + i for i in range(n)], index=idx)
    return pd.DataFrame({
        "Open": close * 0.99,
        "High": close * 1.01,
        "Low": close * 0.98,
        "Close": close,
        "Volume": [1_000_000] * n,
    })


class TestCacheTTL:
    def test_period_call_bypasses_stale_cache(self, tmp_path):
        """Period-based call with stale cache should re-fetch from source."""
        dm = DataManager(cache_dir=tmp_path, cache_ttl_hours=1)
        fresh_df = _make_ohlcv()

        # Write a cached file and backdate its mtime by 2 hours
        cache_path = dm._cache._path("AAPL", "daily")
        fresh_df.to_parquet(cache_path)
        old_mtime = time.time() - 7200  # 2 hours ago
        os.utime(cache_path, (old_mtime, old_mtime))

        with patch.object(dm._yf, "get_ohlcv", return_value=fresh_df) as mock_fetch:
            result = dm.get_ohlcv("AAPL", period="5y")
            mock_fetch.assert_called_once()
            assert not result.empty

    def test_period_call_uses_fresh_cache(self, tmp_path):
        """Period-based call with fresh cache should NOT re-fetch."""
        dm = DataManager(cache_dir=tmp_path, cache_ttl_hours=24)
        fresh_df = _make_ohlcv()

        # Write a fresh cached file (mtime = now)
        cache_path = dm._cache._path("AAPL", "daily")
        fresh_df.to_parquet(cache_path)

        with patch.object(dm._yf, "get_ohlcv") as mock_fetch:
            result = dm.get_ohlcv("AAPL", period="5y")
            mock_fetch.assert_not_called()
            assert not result.empty

    def test_date_range_call_ignores_ttl(self, tmp_path):
        """Calls with explicit start/end should not check TTL."""
        from datetime import date

        dm = DataManager(cache_dir=tmp_path, cache_ttl_hours=1)
        fresh_df = _make_ohlcv()

        # Write stale cache
        cache_path = dm._cache._path("AAPL", "daily")
        fresh_df.to_parquet(cache_path)
        old_mtime = time.time() - 7200
        os.utime(cache_path, (old_mtime, old_mtime))

        with patch.object(dm._yf, "get_ohlcv") as mock_fetch:
            result = dm.get_ohlcv(
                "AAPL",
                start=date(2023, 1, 1),
                end=date(2023, 1, 14),
            )
            # Should serve from cache (date-range call ignores TTL)
            mock_fetch.assert_not_called()
            assert not result.empty
