"""Download & cache S&P 500 price + fundamental data."""
from pathlib import Path

import pandas as pd
import yfinance as yf

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def get_sp500_tickers() -> tuple[list[str], pd.DataFrame]:
    """Scrape current S&P 500 constituents from Wikipedia.

    Returns (sorted ticker list, sector DataFrame with columns [ticker, sector, sub_industry]).
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    table = pd.read_html(url, storage_options={"User-Agent": "Mozilla/5.0"})[0]
    table["Symbol"] = table["Symbol"].str.replace(".", "-", regex=False)
    tickers = sorted(table["Symbol"].tolist())
    sectors = table[["Symbol", "GICS Sector", "GICS Sub-Industry"]].rename(
        columns={"Symbol": "ticker", "GICS Sector": "sector",
                 "GICS Sub-Industry": "sub_industry"}
    )
    return tickers, sectors


def download_prices(tickers: list[str], start: str = "2019-01-01",
                    end: str = "2025-12-31") -> pd.DataFrame:
    """Download daily OHLCV for given tickers. Returns MultiIndex columns (field, ticker)."""
    df = yf.download(tickers, start=start, end=end, group_by="column", threads=True)
    return df


def download_financials(tickers: list[str]) -> pd.DataFrame:
    """Download quarterly financials for given tickers.

    Returns a DataFrame with columns: ticker, date, and financial fields.
    Each row = one quarter for one ticker.
    """
    rows = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            # quarterly_income_stmt has columns = dates, rows = line items
            inc = t.quarterly_income_stmt
            bs = t.quarterly_balance_sheet
            cf = t.quarterly_cashflow
            if inc is None or inc.empty:
                continue
            for date in inc.columns:
                row = {"ticker": ticker, "date": date}
                for stmt in [inc, bs, cf]:
                    if stmt is not None and date in stmt.columns:
                        for item in stmt.index:
                            row[item] = stmt.loc[item, date]
                rows.append(row)
        except Exception:
            continue
    return pd.DataFrame(rows)


def cache_all(force: bool = False):
    """Download everything and save to parquet. Skip if cache exists unless force=True."""
    prices_path = DATA_DIR / "prices.parquet"
    financials_path = DATA_DIR / "financials.parquet"

    tickers, sectors = get_sp500_tickers()
    # SPY is an ETF, not a constituent — add explicitly for benchmark
    if "SPY" not in tickers:
        tickers.append("SPY")
    print(f"S&P 500 + SPY: {len(tickers)} tickers")

    # Always save sector mapping (lightweight, no download needed)
    sectors_path = DATA_DIR / "sectors.parquet"
    sectors.to_parquet(sectors_path, index=False)
    print(f"Saved {sectors_path} ({len(sectors)} rows)")

    if force or not prices_path.exists():
        print("Downloading prices...")
        prices = download_prices(tickers)
        prices.to_parquet(prices_path)
        print(f"Saved {prices_path} ({len(prices)} rows)")
    else:
        print(f"Prices cached at {prices_path}")

    if force or not financials_path.exists():
        print("Downloading financials...")
        financials = download_financials(tickers)
        financials.to_parquet(financials_path)
        print(f"Saved {financials_path} ({len(financials)} rows)")
    else:
        print(f"Financials cached at {financials_path}")


if __name__ == "__main__":
    import sys
    cache_all(force="--force" in sys.argv)
