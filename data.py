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
                    end: str = "2025-12-31",
                    batch_size: int = 20) -> pd.DataFrame:
    """Download daily OHLCV in batches to avoid Yahoo rate limits.

    Returns MultiIndex columns (field, ticker).
    """
    import time

    n_batches = (len(tickers) + batch_size - 1) // batch_size
    chunks = []
    failed = []

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"  Batch {batch_num}/{n_batches} ({len(batch)} tickers)...")
        df = yf.download(
            batch, start=start, end=end,
            group_by="column", threads=True,
        )
        if not df.empty:
            # Track which tickers actually came back
            got = set(df.columns.get_level_values(-1).unique())
            missed = [t for t in batch if t not in got]
            failed.extend(missed)
            chunks.append(df)
        else:
            failed.extend(batch)
        if batch_num < n_batches:
            time.sleep(2)  # rate-limit pause

    # Retry failed tickers one-by-one
    if failed:
        print(f"  Retrying {len(failed)} failed tickers individually...")
        for t in failed:
            time.sleep(1)
            try:
                df = yf.download(
                    t, start=start, end=end,
                    group_by="column", threads=False,
                    progress=False,
                )
                if not df.empty:
                    chunks.append(df)
            except Exception:
                print(f"    {t}: still failed")

    if not chunks:
        return pd.DataFrame()
    combined = pd.concat(chunks, axis=1)
    combined = combined.loc[:, ~combined.columns.duplicated()]
    return combined


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


def update_prices(tickers: list[str],
                   prices_path: Path = DATA_DIR / "prices.parquet") -> None:
    """Incrementally update cached prices with only missing recent days.

    Uses a single yf.download call (no batching needed for short periods).
    """
    from datetime import datetime, timedelta

    existing = pd.read_parquet(prices_path)
    last_date = existing.index[-1]
    start = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    if start >= today:
        print(f"Prices already up to date ({last_date.date()})")
        return

    print(f"Updating prices: {last_date.date()} → {today}...")
    # Single call is fine for short date ranges (days/weeks, not years)
    new_data = yf.download(
        tickers, start=start, end=today,
        group_by="column", threads=True,
    )

    if new_data.empty:
        print("No new trading days to add.")
        return

    combined = pd.concat([existing, new_data])
    combined = combined[~combined.index.duplicated(keep="last")]
    combined = combined.sort_index()
    combined.to_parquet(prices_path)
    print(f"Updated {prices_path}: {len(existing)} → {len(combined)} rows "
          f"(+{len(combined) - len(existing)} days)")


def cache_all(force: bool = False, update: bool = False):
    """Download and save to parquet.

    Args:
        force: Full re-download of everything.
        update: Incremental update — append recent days to existing cache.
    """
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

    if update and prices_path.exists():
        update_prices(tickers, prices_path)
    elif force or not prices_path.exists():
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
    cache_all(
        force="--force" in sys.argv,
        update="--update" in sys.argv,
    )
