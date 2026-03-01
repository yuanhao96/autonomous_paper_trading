"""Universe data management: download, cache, and build panels for sector ETFs."""

import time
from pathlib import Path

import pandas as pd
import yfinance as yf

from stratgen.paths import UNIVERSE_CACHE_DIR

# 11 S&P sector ETFs (XLC launched June 2018 — start from 2019 for full coverage)
SECTOR_ETFS = [
    "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY",
]
BENCHMARK = "SPY"


def download_universe(
    tickers: list[str] | None = None,
    start: str = "2019-01-01",
    end: str = "2025-12-31",
    cache_dir: Path | None = None,
    max_age_hours: int = 24,
) -> dict[str, pd.DataFrame]:
    """Download OHLCV for all tickers, using Parquet cache.

    For each ticker: check cache freshness, download if stale, save Parquet.
    Returns dict mapping ticker -> DataFrame[Open, High, Low, Close, Volume].
    """
    if tickers is None:
        tickers = SECTOR_ETFS
    if cache_dir is None:
        cache_dir = UNIVERSE_CACHE_DIR

    cache_dir.mkdir(parents=True, exist_ok=True)
    universe: dict[str, pd.DataFrame] = {}

    for ticker in tickers:
        parquet_path = cache_dir / f"{ticker}.parquet"
        use_cache = False

        if parquet_path.exists():
            age_hours = (time.time() - parquet_path.stat().st_mtime) / 3600
            if age_hours < max_age_hours:
                use_cache = True

        if use_cache:
            df = pd.read_parquet(parquet_path)
            print(f"  {ticker}: cached ({len(df)} bars)")
        else:
            print(f"  {ticker}: downloading...")
            df = yf.download(ticker, start=start, end=end, progress=False)
            if hasattr(df.columns, "levels") and df.columns.nlevels > 1:
                df = df.droplevel(level=1, axis=1)
            df.to_parquet(parquet_path)
            print(f"  {ticker}: {len(df)} bars, {df.index[0].date()} to {df.index[-1].date()}")

        universe[ticker] = df

    print(f"\nUniverse: {len(universe)} tickers loaded.\n")
    return universe


def build_panel(
    universe_data: dict[str, pd.DataFrame],
    field: str = "Close",
) -> pd.DataFrame:
    """Build panel DataFrame(index=dates, columns=tickers) for one OHLCV field.

    Aligns on shared dates, drops rows with any NaN.
    """
    panel = pd.DataFrame({t: d[field] for t, d in universe_data.items()})
    panel = panel.dropna()
    return panel
