"""Curated static universe lists — Level 1 universe selection.

S&P 500 and NASDAQ-100 are scraped from Wikipedia and cached locally.
Hardcoded fallback lists are used if scraping fails.
"""

from __future__ import annotations

import logging

from src.universe.wikipedia import (
    fetch_nasdaq100,
    fetch_sp500,
    get_cached_or_fetch,
)

logger = logging.getLogger(__name__)

# ── Fallback lists (used when Wikipedia scraping fails) ──────────────
_SP500_FALLBACK: list[str] = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "BRK-B", "UNH", "XOM", "JNJ",
    "JPM", "V", "PG", "MA", "AVGO", "HD", "CVX", "MRK", "ABBV", "COST",
    "PEP", "KO", "ADBE", "WMT", "CRM", "MCD", "CSCO", "ACN", "LIN", "TMO",
    "ABT", "DHR", "NKE", "TXN", "PM", "NEE", "UNP", "ORCL", "AMGN", "RTX",
    "LOW", "HON", "IBM", "QCOM", "SBUX", "GE", "CAT", "INTU", "AMAT", "BA",
]

_NASDAQ100_FALLBACK: list[str] = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "AVGO", "COST", "TSLA", "ADBE",
    "AMD", "PEP", "CSCO", "NFLX", "INTC", "CMCSA", "TMUS", "INTU", "AMGN", "TXN",
    "QCOM", "ISRG", "AMAT", "BKNG", "ADI", "VRTX", "SBUX", "GILD", "MDLZ", "ADP",
    "REGN", "PYPL", "LRCX", "SNPS", "KLAC", "PANW", "MNST", "CDNS", "MELI", "ORLY",
]

SECTOR_ETFS: list[str] = [
    "XLK", "XLV", "XLF", "XLY", "XLP", "XLE", "XLI", "XLU", "XLRE", "XLC", "XLB",
]

BROAD_ETFS: list[str] = [
    "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "IVV", "VEA", "VWO", "EFA",
    "EEM", "AGG", "BND", "TLT", "IEF", "GLD", "SLV", "USO", "UNG",
]

G10_FOREX: list[str] = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X",
    "NZDUSD=X", "USDCAD=X", "EURGBP=X", "EURJPY=X", "GBPJPY=X",
]

CRYPTO_TOP: list[str] = [
    "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "SOL-USD",
    "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "MATIC-USD",
]


def _load_universe(name: str, fallback: list[str]) -> list[str]:
    """Load a universe from Wikipedia cache, falling back to hardcoded list."""
    fetchers = {
        "sp500": fetch_sp500,
        "nasdaq100": fetch_nasdaq100,
    }
    fetcher = fetchers.get(name)
    if fetcher is None:
        return fallback

    result = get_cached_or_fetch(name, fetcher)
    if result is not None:
        return result

    logger.info("Using hardcoded fallback for %s (%d symbols)", name, len(fallback))
    return fallback


def _build_universes() -> dict[str, list[str]]:
    """Build the registry, trying Wikipedia for sp500/nasdaq100."""
    return {
        "sp500": _load_universe("sp500", _SP500_FALLBACK),
        "nasdaq100": _load_universe("nasdaq100", _NASDAQ100_FALLBACK),
        "sector_etfs": SECTOR_ETFS,
        "broad_etfs": BROAD_ETFS,
        "g10_forex": G10_FOREX,
        "crypto_top": CRYPTO_TOP,
    }


# Build once at module load (with graceful fallback on failure)
STATIC_UNIVERSES: dict[str, list[str]] = _build_universes()


def get_static_universe(name: str) -> list[str]:
    """Get a static universe by name."""
    if name not in STATIC_UNIVERSES:
        available = ", ".join(STATIC_UNIVERSES.keys())
        raise ValueError(f"Unknown static universe: {name}. Available: {available}")
    return list(STATIC_UNIVERSES[name])


def list_static_universes() -> list[str]:
    """List available static universe names."""
    return list(STATIC_UNIVERSES.keys())
