"""Universe data management: download, cache, and build panels."""

import time
from pathlib import Path

import pandas as pd
import yfinance as yf

from stratgen.paths import UNIVERSE_CACHE_DIR

# 11 S&P sector ETFs (XLC launched June 2018 — start from 2019 for full coverage)
SECTOR_ETFS = [
    "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY",
]

# S&P 100 (OEX) constituents — large-cap, liquid, data back to 2019.
# NOTE: Survivorship bias — this is the current list, not point-in-time.
SP100_TICKERS = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "AIG", "AMGN", "AMT", "AMZN",
    "AVGO", "AXP", "BA", "BAC", "BK", "BKNG", "BLK", "BMY", "BRK-B",
    "C", "CAT", "CHTR", "CL", "CMCSA", "COF", "COP", "COST", "CRM",
    "CSCO", "CVS", "CVX", "DE", "DHR", "DIS", "DOW", "DUK", "EMR",
    "EXC", "F", "FDX", "GD", "GE", "GILD", "GM", "GOOG", "GOOGL",
    "GS", "HD", "HON", "IBM", "INTC", "INTU", "JNJ", "JPM", "KHC",
    "KO", "LIN", "LLY", "LMT", "LOW", "MA", "MCD", "MDLZ", "MDT",
    "MET", "META", "MMM", "MO", "MRK", "MS", "MSFT", "NEE", "NFLX",
    "NKE", "NOW", "NVDA", "ORCL", "PEP", "PFE", "PG", "PM", "PYPL",
    "QCOM", "RTX", "SBUX", "SCHW", "SO", "SPG", "T", "TGT", "TMO",
    "TMUS", "TSLA", "TXN", "UNH", "UNP", "UPS", "USB", "V", "VZ",
    "WBA", "WFC", "WMT", "XOM",
]

UNIVERSES: dict[str, list[str]] = {
    "sp100": SP100_TICKERS,
    "sector-etfs": SECTOR_ETFS,
}

BENCHMARK = "SPY"


def get_universe_tickers(name: str = "sp100") -> list[str]:
    """Return ticker list for a named universe."""
    if name not in UNIVERSES:
        raise ValueError(f"Unknown universe: {name}. Choose from: {list(UNIVERSES.keys())}")
    return UNIVERSES[name]


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
            try:
                df = yf.download(ticker, start=start, end=end, progress=False)
                if hasattr(df.columns, "levels") and df.columns.nlevels > 1:
                    df = df.droplevel(level=1, axis=1)
                if df.empty:
                    print(f"  {ticker}: WARNING — no data returned, skipping")
                    continue
                df.to_parquet(parquet_path)
                print(f"  {ticker}: {len(df)} bars, "
                      f"{df.index[0].date()} to {df.index[-1].date()}")
            except Exception as e:
                print(f"  {ticker}: WARNING — download failed ({e}), skipping")
                continue

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
