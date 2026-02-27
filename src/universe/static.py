"""Curated static universe lists — Level 1 universe selection."""

from __future__ import annotations

# ── Static Universe Definitions ─────────────────────────────────────
# These are refreshed manually or quarterly. They serve as the base
# pools for Level 1 (static) strategies.

SP500_SAMPLE: list[str] = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "BRK-B", "UNH", "XOM", "JNJ",
    "JPM", "V", "PG", "MA", "AVGO", "HD", "CVX", "MRK", "ABBV", "COST",
    "PEP", "KO", "ADBE", "WMT", "CRM", "MCD", "CSCO", "ACN", "LIN", "TMO",
    "ABT", "DHR", "NKE", "TXN", "PM", "NEE", "UNP", "ORCL", "AMGN", "RTX",
    "LOW", "HON", "IBM", "QCOM", "SBUX", "GE", "CAT", "INTU", "AMAT", "BA",
]

NASDAQ100_SAMPLE: list[str] = [
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

# Registry of all static universes
STATIC_UNIVERSES: dict[str, list[str]] = {
    "sp500": SP500_SAMPLE,
    "nasdaq100": NASDAQ100_SAMPLE,
    "sector_etfs": SECTOR_ETFS,
    "broad_etfs": BROAD_ETFS,
    "g10_forex": G10_FOREX,
    "crypto_top": CRYPTO_TOP,
}


def get_static_universe(name: str) -> list[str]:
    """Get a static universe by name."""
    if name not in STATIC_UNIVERSES:
        available = ", ".join(STATIC_UNIVERSES.keys())
        raise ValueError(f"Unknown static universe: {name}. Available: {available}")
    return list(STATIC_UNIVERSES[name])


def list_static_universes() -> list[str]:
    """List available static universe names."""
    return list(STATIC_UNIVERSES.keys())
