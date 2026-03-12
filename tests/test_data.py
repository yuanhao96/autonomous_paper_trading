import pandas as pd
from data import get_sp500_tickers, download_prices, download_financials


def test_sp500_tickers():
    tickers = get_sp500_tickers()
    assert isinstance(tickers, list)
    assert len(tickers) > 400
    assert "AAPL" in tickers
    assert "MSFT" in tickers


def test_download_prices_small():
    """Test with 3 tickers to keep it fast."""
    df = download_prices(["AAPL", "MSFT", "GOOGL"], start="2024-01-01", end="2024-03-01")
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 30  # ~2 months of trading days
    # MultiIndex columns: (field, ticker)
    assert "AAPL" in df.columns.get_level_values(1)
    assert "Close" in df.columns.get_level_values(0)


def test_download_financials_small():
    """Test with 2 tickers."""
    df = download_financials(["AAPL", "MSFT"])
    assert isinstance(df, pd.DataFrame)
    assert "ticker" in df.columns
    assert "Total Revenue" in df.columns or "TotalRevenue" in df.columns
    assert len(df) > 0
