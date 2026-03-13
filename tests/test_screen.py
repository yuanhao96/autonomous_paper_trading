import numpy as np
import pandas as pd
from screen import compute_price_features, compute_fundamental_features
from screen import apply_screen, compute_all_features, compute_pctrank_features
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


def test_pctrank_features_synthetic():
    """Test percentile ranks on synthetic data — no cached data needed."""
    dates = pd.date_range("2024-01-01", periods=5, freq="B")
    tickers = ["AAPL", "GOOG", "MSFT", "AMZN"]
    # Build a MultiIndex DataFrame with one feature
    data = pd.DataFrame(
        [[10, 20, 30, 40],
         [40, 30, 20, 10],
         [10, 10, 10, 10],  # all same — rank should be ~0.5
         [np.nan, 20, 30, np.nan],  # NaN handling
         [5, 15, 25, 35]],
        index=dates,
        columns=tickers,
    )
    features = pd.concat({"score": data}, axis=1)

    result = compute_pctrank_features(features)
    assert "score_pctrank" in result.columns.get_level_values(0)

    ranked = result["score_pctrank"]
    # Row 0: AAPL=10 lowest -> 0.25, AMZN=40 highest -> 1.0
    assert ranked.iloc[0]["AAPL"] == pytest.approx(0.25)
    assert ranked.iloc[0]["AMZN"] == pytest.approx(1.0)
    # Row 1: reversed order
    assert ranked.iloc[1]["AAPL"] == pytest.approx(1.0)
    assert ranked.iloc[1]["AMZN"] == pytest.approx(0.25)
    # Row 2: all same — all get same rank (0.5 for 4 tied values)
    assert ranked.iloc[2]["AAPL"] == ranked.iloc[2]["GOOG"]
    # Row 3: NaN stays NaN
    assert pd.isna(ranked.iloc[3]["AAPL"])
    assert pd.isna(ranked.iloc[3]["AMZN"])
    assert pd.notna(ranked.iloc[3]["GOOG"])


def test_pctrank_features_on_real_data():
    """Test pctrank on actual cached features."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    features = compute_all_features()
    feature_names = features.columns.get_level_values(0).unique()
    # Should have pctrank variants
    pctrank_names = [f for f in feature_names if f.endswith("_pctrank")]
    raw_names = [f for f in feature_names if not f.endswith("_pctrank")]
    assert len(pctrank_names) == len(raw_names)
    # Pctrank values should be in [0, 1]
    for feat in pctrank_names[:3]:
        vals = features[feat].values.flatten()
        valid = vals[~np.isnan(vals)]
        assert valid.min() >= 0.0
        assert valid.max() <= 1.0


def test_apply_screen_with_pctrank():
    """Test that screens using _pctrank features work."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    features = compute_all_features()
    screen_def = {
        "name": "test pctrank",
        "hypothesis": "top quintile momentum",
        "filters": [
            {"feature": "return_6m_pctrank", "op": ">", "value": 0.8},
        ],
        "top_n": 20,
        "rank_by": "return_6m_pctrank",
        "rank_order": "desc",
    }
    result = apply_screen(screen_def, features)
    assert result["n_months"] > 0
    assert isinstance(result["sharpe"], float)


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
