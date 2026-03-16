"""Tests for new price-derived features."""
import numpy as np
import pandas as pd
import pytest
from pathlib import Path


def test_return_1w_synthetic():
    """Test 5-day return feature on synthetic data."""
    from screen import compute_price_features

    dates = pd.date_range("2024-01-01", periods=30, freq="B")
    tickers = ["AAPL", "GOOG"]
    close_data = pd.DataFrame(
        {"AAPL": np.linspace(100, 130, 30),
         "GOOG": np.linspace(200, 180, 30)},
        index=dates,
    )
    prices = pd.concat({
        "Close": close_data,
        "High": close_data * 1.02,
        "Low": close_data * 0.98,
        "Volume": pd.DataFrame(1e6, index=dates, columns=tickers),
    }, axis=1)

    features = compute_price_features(prices)
    assert "return_1w" in features.columns.get_level_values(0)
    vals = features["return_1w"]["AAPL"].dropna()
    assert len(vals) > 0
    assert vals.iloc[-1] > 0


def test_return_12m_skip_1m_synthetic():
    """Test 12m momentum skipping most recent month."""
    from screen import compute_price_features

    dates = pd.date_range("2023-01-01", periods=300, freq="B")
    tickers = ["AAPL"]
    close_data = pd.DataFrame(
        {"AAPL": np.linspace(100, 200, 300)}, index=dates,
    )
    prices = pd.concat({
        "Close": close_data,
        "High": close_data * 1.02,
        "Low": close_data * 0.98,
        "Volume": pd.DataFrame(1e6, index=dates, columns=tickers),
    }, axis=1)

    features = compute_price_features(prices)
    assert "return_12m_skip_1m" in features.columns.get_level_values(0)
    vals = features["return_12m_skip_1m"]["AAPL"].dropna()
    assert len(vals) > 0


def test_idio_vol_synthetic():
    """Test idiosyncratic volatility."""
    from screen import compute_price_features

    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    spy_rets = np.random.normal(0.0005, 0.01, 100)
    aapl_rets = spy_rets * 1.2 + np.random.normal(0, 0.02, 100)
    goog_rets = spy_rets * 0.8 + np.random.normal(0, 0.005, 100)

    spy_close = pd.Series(
        100 * np.cumprod(1 + spy_rets), index=dates, name="SPY",
    )
    aapl_close = pd.Series(
        150 * np.cumprod(1 + aapl_rets), index=dates, name="AAPL",
    )
    goog_close = pd.Series(
        200 * np.cumprod(1 + goog_rets), index=dates, name="GOOG",
    )

    close_data = pd.concat([spy_close, aapl_close, goog_close], axis=1)
    tickers = ["SPY", "AAPL", "GOOG"]
    prices = pd.concat({
        "Close": close_data,
        "High": close_data * 1.01,
        "Low": close_data * 0.99,
        "Volume": pd.DataFrame(1e6, index=dates, columns=tickers),
    }, axis=1)

    features = compute_price_features(prices)
    assert "idio_vol" in features.columns.get_level_values(0)
    aapl_iv = features["idio_vol"]["AAPL"].dropna().iloc[-1]
    goog_iv = features["idio_vol"]["GOOG"].dropna().iloc[-1]
    assert aapl_iv > goog_iv


def test_volume_change_20d_synthetic():
    """Test volume change (20d/60d dollar volume ratio)."""
    from screen import compute_price_features

    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    tickers = ["AAPL"]
    close_data = pd.DataFrame(
        {"AAPL": np.linspace(100, 120, 100)}, index=dates,
    )
    vol_data = pd.DataFrame(
        {"AAPL": [1e6] * 50 + [2e6] * 50}, index=dates,
    )
    prices = pd.concat({
        "Close": close_data,
        "High": close_data * 1.02,
        "Low": close_data * 0.98,
        "Volume": vol_data,
    }, axis=1)

    features = compute_price_features(prices)
    assert "volume_change_20d" in features.columns.get_level_values(0)
    val = features["volume_change_20d"]["AAPL"].iloc[-1]
    assert val > 1.0


def test_new_features_on_real_data():
    """New features exist on real cached data."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    from screen import compute_price_features

    prices = pd.read_parquet(Path("data/prices.parquet"))
    features = compute_price_features(prices)
    for feat in [
        "return_1w", "return_12m_skip_1m", "idio_vol", "volume_change_20d",
    ]:
        assert feat in features.columns.get_level_values(0), (
            f"Missing: {feat}"
        )
