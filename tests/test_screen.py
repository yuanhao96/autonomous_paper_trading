import pandas as pd
from screen import compute_price_features, compute_fundamental_features
from screen import apply_screen, compute_all_features
from pathlib import Path
import pytest


def test_price_features_shape():
    """Use cached data if available, otherwise skip."""
    prices_path = Path("data/prices.parquet")
    if not prices_path.exists():
        pytest.skip("No cached price data")
    prices = pd.read_parquet(prices_path)
    features = compute_price_features(prices)
    assert isinstance(features, pd.DataFrame)
    # Should have MultiIndex columns: (feature_name, ticker)
    assert "return_1m" in features.columns.get_level_values(0)
    assert "close_vs_sma200" in features.columns.get_level_values(0)
    assert len(features) > 100


def test_fundamental_features_shape():
    prices_path = Path("data/prices.parquet")
    fin_path = Path("data/financials.parquet")
    if not prices_path.exists() or not fin_path.exists():
        pytest.skip("No cached data")
    prices = pd.read_parquet(prices_path)
    financials = pd.read_parquet(fin_path)
    features = compute_fundamental_features(financials, prices)
    assert isinstance(features, pd.DataFrame)
    assert "gross_margin" in features.columns.get_level_values(0)


def test_apply_screen():
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    features = compute_all_features()
    screen_def = {
        "name": "test momentum",
        "hypothesis": "testing",
        "filters": [
            {"feature": "return_3m", "op": ">", "value": 0.05},
            {"feature": "close_vs_sma200", "op": ">", "value": 1.0},
        ],
        "top_n": 20,
    }
    result = apply_screen(screen_def, features)
    assert "alpha_monthly_mean" in result
    assert "sharpe" in result
    assert "n_avg_stocks" in result
    assert "monthly_details" in result
    assert "stock_details" in result
    assert isinstance(result["alpha_monthly_mean"], float)
    # Check monthly_details structure (slim — no stocks)
    if result["n_months"] > 0:
        detail = result["monthly_details"][0]
        assert "month" in detail
        assert "port_return" in detail
        assert "spy_return" in detail
        assert "alpha" in detail
        assert "n_stocks" in detail
        assert "stocks" not in detail
        # Check stock_details structure (archived separately)
        sd = result["stock_details"][0]
        assert "month" in sd
        assert "stocks" in sd
        assert isinstance(sd["stocks"], dict)
