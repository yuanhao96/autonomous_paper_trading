"""Local Parquet file cache for market data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.core.config import Settings


class ParquetCache:
    """Cache OHLCV data as Parquet files for fast reloads."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        if cache_dir is None:
            cache_dir = Settings().cache_dir
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str, resolution: str) -> Path:
        safe = symbol.replace("/", "_").replace("=", "_").upper()
        return self._dir / f"{safe}_{resolution}.parquet"

    def has(self, symbol: str, resolution: str = "daily") -> bool:
        return self._path(symbol, resolution).exists()

    def read(self, symbol: str, resolution: str = "daily") -> pd.DataFrame | None:
        path = self._path(symbol, resolution)
        if not path.exists():
            return None
        return pd.read_parquet(path)

    def write(self, symbol: str, df: pd.DataFrame, resolution: str = "daily") -> None:
        path = self._path(symbol, resolution)
        df.to_parquet(path, engine="pyarrow")

    def update(self, symbol: str, new_data: pd.DataFrame, resolution: str = "daily") -> pd.DataFrame:
        """Append new data to existing cache, deduplicating by index."""
        existing = self.read(symbol, resolution)
        if existing is not None:
            combined = pd.concat([existing, new_data])
            combined = combined[~combined.index.duplicated(keep="last")]
            combined = combined.sort_index()
        else:
            combined = new_data.sort_index()
        self.write(symbol, combined, resolution)
        return combined

    def clear(self, symbol: str | None = None, resolution: str = "daily") -> None:
        if symbol is not None:
            path = self._path(symbol, resolution)
            if path.exists():
                path.unlink()
        else:
            for f in self._dir.glob("*.parquet"):
                f.unlink()
