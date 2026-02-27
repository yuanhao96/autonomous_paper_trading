"""yfinance-based universe data provider for filtering and screening."""

from __future__ import annotations

import pandas as pd
import yfinance as yf


class YFinanceUniverseProvider:
    """Provides fundamental data for universe filtering via yfinance."""

    def get_fundamentals(self, symbols: list[str]) -> pd.DataFrame:
        """Fetch fundamental data for a list of symbols.

        Returns a DataFrame with columns like market_cap, sector, price, etc.
        indexed by symbol.
        """
        records = []
        for symbol in symbols:
            try:
                info = yf.Ticker(symbol).info
                records.append({
                    "symbol": symbol,
                    "market_cap": info.get("marketCap", 0),
                    "avg_daily_volume": info.get("averageDailyVolume10Day", 0),
                    "price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                    "sector": info.get("sector", ""),
                    "industry": info.get("industry", ""),
                    "pe_ratio": info.get("trailingPE", 0),
                    "pb_ratio": info.get("priceToBook", 0),
                    "dividend_yield": info.get("dividendYield", 0) or 0,
                    "beta": info.get("beta", 0) or 0,
                    "country": info.get("country", ""),
                    "exchange": info.get("exchange", ""),
                })
            except Exception:
                continue

        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records).set_index("symbol")

    def get_momentum(self, symbols: list[str], periods: list[int] | None = None) -> pd.DataFrame:
        """Calculate momentum (return) over various periods for symbols.

        Returns DataFrame with columns like momentum_1m, momentum_3m, etc.
        """
        if periods is None:
            periods = [21, 63, 126, 252]  # ~1m, 3m, 6m, 12m

        period_names = {21: "1m", 63: "3m", 126: "6m", 252: "12m"}
        records = []

        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2y")
                if hist.empty or len(hist) < max(periods):
                    continue

                row: dict = {"symbol": symbol}
                for p in periods:
                    name = period_names.get(p, f"{p}d")
                    if len(hist) >= p:
                        ret = (hist["Close"].iloc[-1] / hist["Close"].iloc[-p]) - 1
                        row[f"momentum_{name}"] = ret
                    else:
                        row[f"momentum_{name}"] = 0.0
                records.append(row)
            except Exception:
                continue

        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records).set_index("symbol")

    def get_volatility(self, symbols: list[str], window: int = 30) -> pd.DataFrame:
        """Calculate rolling volatility for symbols."""
        records = []
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1y")
                if hist.empty or len(hist) < window:
                    continue
                returns = hist["Close"].pct_change().dropna()
                vol = returns.rolling(window).std().iloc[-1] * (252 ** 0.5)
                records.append({"symbol": symbol, f"volatility_{window}d": vol})
            except Exception:
                continue

        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records).set_index("symbol")

    def get_rsi(self, symbols: list[str], period: int = 14) -> pd.DataFrame:
        """Calculate RSI for symbols."""
        records = []
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="6mo")
                if hist.empty or len(hist) < period + 1:
                    continue
                delta = hist["Close"].diff()
                gain = delta.clip(lower=0).rolling(period).mean()
                loss = (-delta.clip(upper=0)).rolling(period).mean()
                rs = gain / loss.replace(0, float("inf"))
                rsi = 100 - (100 / (1 + rs))
                records.append({"symbol": symbol, f"rsi_{period}": rsi.iloc[-1]})
            except Exception:
                continue

        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records).set_index("symbol")
