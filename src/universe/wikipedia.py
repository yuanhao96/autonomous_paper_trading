"""Scrape index constituents from Wikipedia with local JSON caching."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR = Path("data/cache")
_DEFAULT_MAX_AGE_HOURS = 24
_TIMEOUT_SECONDS = 15
_HEADERS = {"User-Agent": "autonomous-trading/0.1 (index-constituents-scraper)"}


def _normalize_ticker(raw: str) -> str:
    """Normalize a ticker symbol for yfinance compatibility.

    Strips whitespace, replaces '.' with '-' (e.g. BRK.B → BRK-B).
    """
    return raw.strip().replace(".", "-")


def fetch_sp500() -> list[str] | None:
    """Scrape current S&P 500 constituents from Wikipedia.

    Returns list of ~503 tickers, or None on failure.
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT_SECONDS)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failed to fetch S&P 500 page: %s", exc)
        return None

    try:
        soup = BeautifulSoup(resp.text, "lxml")
        result = soup.find("table", {"id": "constituents"})
        if not isinstance(result, Tag):
            # Fallback: first wikitable
            result = soup.find("table", {"class": "wikitable"})
        if not isinstance(result, Tag):
            logger.warning("Could not find S&P 500 constituents table")
            return None

        tickers: list[str] = []
        rows = result.find_all("tr")[1:]  # skip header
        for row in rows:
            cells = row.find_all("td")
            if cells:
                tickers.append(_normalize_ticker(cells[0].get_text()))

        if len(tickers) < 400:
            logger.warning("S&P 500 scrape returned only %d tickers", len(tickers))
            return None

        return tickers
    except Exception as exc:
        logger.warning("Failed to parse S&P 500 page: %s", exc)
        return None


def fetch_nasdaq100() -> list[str] | None:
    """Scrape current NASDAQ-100 constituents from Wikipedia.

    Returns list of ~101 tickers, or None on failure.
    """
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT_SECONDS)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failed to fetch NASDAQ-100 page: %s", exc)
        return None

    try:
        soup = BeautifulSoup(resp.text, "lxml")
        # The components table has id="constituents"
        found = soup.find("table", {"id": "constituents"})
        table: Tag | None = found if isinstance(found, Tag) else None
        if table is None:
            # Fallback: look for wikitable with "Ticker" header
            for t in soup.find_all("table", {"class": "wikitable"}):
                if not isinstance(t, Tag):
                    continue
                hdr = t.find("tr")
                if hdr and "ticker" in hdr.get_text().lower():
                    table = t
                    break
        if table is None:
            logger.warning("Could not find NASDAQ-100 constituents table")
            return None

        # Find which column holds tickers
        header_row_tag = table.find("tr")
        if not isinstance(header_row_tag, Tag):
            logger.warning("NASDAQ-100 table has no header row")
            return None
        headers = [th.get_text().strip().lower() for th in header_row_tag.find_all("th")]
        ticker_col = None
        for i, h in enumerate(headers):
            if "ticker" in h or "symbol" in h:
                ticker_col = i
                break
        if ticker_col is None:
            ticker_col = 1  # common default

        tickers: list[str] = []
        rows = table.find_all("tr")[1:]  # skip header
        for row in rows:
            cells = row.find_all("td")
            if cells and ticker_col < len(cells):
                tickers.append(_normalize_ticker(cells[ticker_col].get_text()))

        if len(tickers) < 80:
            logger.warning("NASDAQ-100 scrape returned only %d tickers", len(tickers))
            return None

        return tickers
    except Exception as exc:
        logger.warning("Failed to parse NASDAQ-100 page: %s", exc)
        return None


def get_cached_or_fetch(
    name: str,
    fetcher: Callable[[], list[str] | None],
    cache_dir: Path = _DEFAULT_CACHE_DIR,
    max_age_hours: int = _DEFAULT_MAX_AGE_HOURS,
) -> list[str] | None:
    """Return cached symbol list if fresh, otherwise fetch and cache.

    Args:
        name: Cache key (e.g. "sp500", "nasdaq100").
        fetcher: Callable that returns list[str] | None.
        cache_dir: Directory for cache files.
        max_age_hours: Maximum cache age before re-fetching.

    Returns:
        List of ticker symbols, or None if fetch fails and no valid cache.
    """
    cache_file = cache_dir / f"universe_{name}.json"

    # Try reading cache
    if cache_file.exists():
        try:
            data: dict[str, Any] = json.loads(cache_file.read_text())
            fetched_at = datetime.fromisoformat(data["fetched_at"])
            age_hours = (datetime.now(tz=timezone.utc) - fetched_at).total_seconds() / 3600
            if age_hours < max_age_hours:
                symbols_cached: list[str] = data["symbols"]
                logger.debug("Using cached %s universe (%d symbols, %.1fh old)",
                             name, len(symbols_cached), age_hours)
                return symbols_cached
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.debug("Cache file %s is invalid: %s", cache_file, exc)

    # Fetch fresh data
    symbols = fetcher()
    if symbols is None:
        # Fetch failed — try stale cache as last resort
        if cache_file.exists():
            try:
                stale: dict[str, Any] = json.loads(cache_file.read_text())
                stale_symbols: list[str] = stale["symbols"]
                logger.info("Fetch failed, using stale cache for %s (%d symbols)",
                            name, len(stale_symbols))
                return stale_symbols
            except (json.JSONDecodeError, KeyError):
                pass
        return None

    # Write cache
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_data = {
            "symbols": symbols,
            "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        cache_file.write_text(json.dumps(cache_data, indent=2))
        logger.info("Cached %d %s symbols to %s", len(symbols), name, cache_file)
    except OSError as exc:
        logger.warning("Failed to write cache file %s: %s", cache_file, exc)

    return symbols
