"""Tests for Parquet cache."""

import pandas as pd
import pytest

from src.data.cache import ParquetCache


@pytest.fixture
def cache(tmp_path):
    return ParquetCache(cache_dir=tmp_path)


@pytest.fixture
def sample_df():
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    return pd.DataFrame(
        {
            "Open": range(100),
            "High": range(1, 101),
            "Low": range(100),
            "Close": range(100),
            "Volume": [1000] * 100,
        },
        index=dates,
    )


class TestParquetCache:
    def test_has_empty(self, cache):
        assert not cache.has("AAPL")

    def test_write_and_read(self, cache, sample_df):
        cache.write("AAPL", sample_df)
        assert cache.has("AAPL")
        loaded = cache.read("AAPL")
        assert loaded is not None
        assert len(loaded) == 100

    def test_read_nonexistent(self, cache):
        assert cache.read("FAKE") is None

    def test_update_deduplicates(self, cache, sample_df):
        cache.write("AAPL", sample_df)
        # Write overlapping data
        new_dates = pd.date_range("2020-03-01", periods=50, freq="D")
        new_df = pd.DataFrame(
            {
                "Open": range(200, 250),
                "High": range(201, 251),
                "Low": range(200, 250),
                "Close": range(200, 250),
                "Volume": [2000] * 50,
            },
            index=new_dates,
        )
        combined = cache.update("AAPL", new_df)
        # Should have original data + new data, deduplicated
        assert len(combined) > 100

    def test_clear_single(self, cache, sample_df):
        cache.write("AAPL", sample_df)
        cache.write("MSFT", sample_df)
        cache.clear("AAPL")
        assert not cache.has("AAPL")
        assert cache.has("MSFT")

    def test_clear_all(self, cache, sample_df):
        cache.write("AAPL", sample_df)
        cache.write("MSFT", sample_df)
        cache.clear()
        assert not cache.has("AAPL")
        assert not cache.has("MSFT")

    def test_symbol_with_special_chars(self, cache, sample_df):
        cache.write("BTC-USD", sample_df)
        assert cache.has("BTC-USD")
        loaded = cache.read("BTC-USD")
        assert loaded is not None
