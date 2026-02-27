"""Shared test fixtures — network-resilient data_manager for integration tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.manager import DataManager
from src.data.sources.yfinance_source import YFinanceSource

_CACHED_NETWORK_STATUS: bool | None = None


def _network_available() -> bool:
    """Probe yfinance once, cache result for the session."""
    global _CACHED_NETWORK_STATUS
    if _CACHED_NETWORK_STATUS is None:
        try:
            import yfinance as yf
            df = yf.Ticker("SPY").history(period="5d")
            _CACHED_NETWORK_STATUS = not df.empty
        except Exception:
            _CACHED_NETWORK_STATUS = False
    return _CACHED_NETWORK_STATUS


_SYNTHETIC_SYMBOLS = [
    "SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV",
    "XLY", "XLP", "XLI", "XLU", "AAPL", "MSFT", "GOOGL",
]


def _make_synthetic_ohlcv(
    symbols: list[str] | None = None, n: int = 1600,
) -> dict[str, pd.DataFrame]:
    """Deterministic synthetic OHLCV data for offline testing.

    Generates ~6 years of business-day data (2019-01-01 onwards)
    so date-filtered queries (e.g. 2023-2024) find sufficient bars.
    """
    symbols = symbols or _SYNTHETIC_SYMBOLS
    result: dict[str, pd.DataFrame] = {}
    for i, sym in enumerate(symbols):
        rng = np.random.default_rng(42 + i)
        close = 100.0 + np.cumsum(rng.normal(0.05, 1.0, n))
        close = np.maximum(close, 10.0)
        idx = pd.date_range("2019-01-01", periods=n, freq="B")
        result[sym] = pd.DataFrame({
            "Open": close * 0.995,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": rng.integers(100_000, 5_000_000, n),
        }, index=idx)
    return result


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Convenience alias used by integration tests."""
    return tmp_path


@pytest.fixture
def data_manager(tmp_path: Path) -> DataManager:
    """DataManager that falls back to synthetic data when network is unavailable.

    When offline, monkeypatches YFinanceSource.get_ohlcv on the DataManager
    instance so every call — including date-filtered ones — returns synthetic
    data instead of hitting the network.
    """
    cache_dir = tmp_path / "cache"
    if _network_available():
        return DataManager(cache_dir=cache_dir)

    # Build a DataManager whose yfinance source always returns synthetic data
    synthetic = _make_synthetic_ohlcv()
    dm = DataManager(cache_dir=cache_dir)

    _original_get = YFinanceSource.get_ohlcv

    def _offline_get(
        self: YFinanceSource, symbol: str, **kwargs: object,
    ) -> pd.DataFrame:
        return synthetic.get(symbol, pd.DataFrame())

    # Monkeypatch the instance's source so the patch lives as long as dm does
    dm._yf.get_ohlcv = _offline_get.__get__(dm._yf, YFinanceSource)  # type: ignore[assignment]
    return dm
