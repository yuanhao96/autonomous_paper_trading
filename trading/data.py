"""Market data fetching and caching module.

Fetches OHLCV data via yfinance and caches results as parquet files
in the configured cache directory.
"""

import logging
from datetime import date
from pathlib import Path

import pandas as pd
import yaml
import yfinance as yf

logger = logging.getLogger(__name__)

# Intervals considered "daily or larger" for cache validity purposes.
_DAILY_OR_LARGER_INTERVALS: set[str] = {
    "1d", "5d", "1wk", "1mo", "3mo",
}

# Project root is three levels up from this file's directory isn't reliable;
# instead, resolve relative to the working directory or an absolute path from config.
_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


def _load_cache_dir() -> Path:
    """Read the cache directory from config/settings.yaml, falling back to 'data/market'."""
    settings_path = _PROJECT_ROOT / "config" / "settings.yaml"
    cache_dir_str = "data/market"
    try:
        with open(settings_path, "r") as f:
            settings = yaml.safe_load(f)
        if settings and "data" in settings and "cache_dir" in settings["data"]:
            cache_dir_str = settings["data"]["cache_dir"]
    except FileNotFoundError:
        logger.warning(
            "config/settings.yaml not found; using default cache dir '%s'",
            cache_dir_str,
        )
    except Exception:
        logger.exception("Error reading settings.yaml; using default cache dir")

    cache_dir = Path(cache_dir_str)
    if not cache_dir.is_absolute():
        cache_dir = _PROJECT_ROOT / cache_dir

    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _cache_key(ticker: str, interval: str) -> str:
    """Build the cache filename for a given ticker, interval, and today's date."""
    today_str = date.today().isoformat()
    return f"{ticker.upper()}_{interval}_{today_str}.parquet"


def _is_cache_valid(cache_path: Path, interval: str) -> bool:
    """Determine whether a cached file is still usable.

    Rules:
    - The cache file must exist.
    - The file must be from today (encoded in the filename).
    - For intraday intervals (anything smaller than '1d'), always refetch.
    - For daily-or-larger intervals, use the cache if it is from today.
    """
    if not cache_path.exists():
        return False

    # Intraday data changes throughout the day, so never trust the cache.
    if interval not in _DAILY_OR_LARGER_INTERVALS:
        return False

    # The filename already encodes today's date via _cache_key, so if the file
    # exists and the interval is daily-or-larger, it is valid.
    return True


def get_ohlcv(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch OHLCV data for a single ticker, using a local parquet cache.

    Parameters
    ----------
    ticker:
        Stock symbol (e.g. ``"AAPL"``).
    period:
        Look-back window understood by yfinance (e.g. ``"1y"``, ``"6mo"``).
    interval:
        Bar interval understood by yfinance (e.g. ``"1d"``, ``"1h"``).

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ``Open, High, Low, Close, Volume``.
        Index is ``DatetimeIndex`` named ``Date``.
    """
    cache_dir = _load_cache_dir()
    filename = _cache_key(ticker, interval)
    cache_path = cache_dir / filename

    if _is_cache_valid(cache_path, interval):
        logger.info("Cache hit for %s (interval=%s): %s", ticker, interval, cache_path)
        df: pd.DataFrame = pd.read_parquet(cache_path)
        df.attrs["ticker"] = ticker.upper()
        return df

    logger.info("Cache miss for %s (interval=%s); fetching from yfinance", ticker, interval)

    yf_ticker = yf.Ticker(ticker)
    df = yf_ticker.history(period=period, interval=interval)

    if df.empty:
        logger.warning(
            "yfinance returned empty DataFrame for %s"
            " (period=%s, interval=%s)",
            ticker, period, interval,
        )
        return df

    # Normalise columns to the standard set.
    # yfinance may include extra columns like Dividends, Stock Splits — drop them.
    standard_cols = ["Open", "High", "Low", "Close", "Volume"]
    available = [c for c in standard_cols if c in df.columns]
    df = df[available]

    # Persist to cache.
    try:
        df.to_parquet(cache_path)
        logger.info("Cached %s rows for %s to %s", len(df), ticker, cache_path)
    except Exception:
        logger.exception("Failed to write cache file %s", cache_path)

    df.attrs["ticker"] = ticker.upper()
    return df


def _range_cache_key(ticker: str, interval: str, start: str, end: str) -> str:
    """Build the cache filename for a date-range query."""
    return f"{ticker.upper()}_{interval}_{start}_{end}.parquet"


def get_ohlcv_range(
    ticker: str,
    start: str,
    end: str,
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch OHLCV data for a fixed date range, using a local parquet cache.

    Parameters
    ----------
    ticker:
        Stock symbol (e.g. ``"SPY"``).
    start:
        Start date as ISO string (e.g. ``"2020-01-01"``).
    end:
        End date as ISO string (e.g. ``"2021-12-31"``).
    interval:
        Bar interval understood by yfinance (e.g. ``"1d"``).

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ``Open, High, Low, Close, Volume``.
        Index is ``DatetimeIndex`` named ``Date``.
    """
    cache_dir = _load_cache_dir()
    filename = _range_cache_key(ticker, interval, start, end)
    cache_path = cache_dir / filename

    if cache_path.exists():
        logger.info("Range cache hit for %s (%s to %s)", ticker, start, end)
        df: pd.DataFrame = pd.read_parquet(cache_path)
        df.attrs["ticker"] = ticker.upper()
        return df

    logger.info("Range cache miss for %s (%s to %s); fetching", ticker, start, end)

    yf_ticker = yf.Ticker(ticker)
    df = yf_ticker.history(start=start, end=end, interval=interval)

    if df.empty:
        logger.warning("yfinance returned empty DataFrame for %s (%s to %s)", ticker, start, end)
        return df

    standard_cols = ["Open", "High", "Low", "Close", "Volume"]
    available = [c for c in standard_cols if c in df.columns]
    df = df[available]

    try:
        df.to_parquet(cache_path)
        logger.info("Cached %d rows for %s range to %s", len(df), ticker, cache_path)
    except Exception:
        logger.exception("Failed to write range cache file %s", cache_path)

    df.attrs["ticker"] = ticker.upper()
    return df


def get_multiple(
    tickers: list[str],
    period: str = "1y",
    interval: str = "1d",
) -> dict[str, pd.DataFrame]:
    """Batch-fetch OHLCV data for multiple tickers.

    Parameters
    ----------
    tickers:
        List of stock symbols.
    period:
        Look-back window (passed to :func:`get_ohlcv`).
    interval:
        Bar interval (passed to :func:`get_ohlcv`).

    Returns
    -------
    dict[str, pd.DataFrame]
        Mapping of ``{ticker: DataFrame}``.
    """
    results: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        try:
            results[ticker] = get_ohlcv(ticker, period=period, interval=interval)
        except Exception:
            logger.exception("Failed to fetch data for %s", ticker)
            results[ticker] = pd.DataFrame()
    return results
