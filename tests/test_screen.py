import numpy as np
import pandas as pd
from screen import compute_price_features, compute_fundamental_features
from screen import (
    apply_screen, compute_all_features, compute_pctrank_features,
    _compute_composite_score,
)
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


def test_composite_score_synthetic():
    """Test composite scoring on synthetic data."""
    dates = pd.date_range("2024-01-01", periods=3, freq="B")
    tickers = ["AAPL", "GOOG", "MSFT", "AMZN"]
    feat_a = pd.DataFrame(
        [[0.8, 0.6, 0.4, 0.2],
         [0.2, 0.4, 0.6, 0.8],
         [0.5, 0.5, 0.5, 0.5]],
        index=dates, columns=tickers,
    )
    feat_b = pd.DataFrame(
        [[0.1, 0.3, 0.5, 0.7],
         [0.7, 0.5, 0.3, 0.1],
         [0.5, 0.5, 0.5, 0.5]],
        index=dates, columns=tickers,
    )
    features = pd.concat({"momentum": feat_a, "quality": feat_b}, axis=1)

    score_def = [
        {"feature": "momentum", "weight": 0.6},
        {"feature": "quality", "weight": 0.4},
    ]
    scores = _compute_composite_score(score_def, features, dates[0], tickers)
    # AAPL: 0.6*0.8 + 0.4*0.1 = 0.52
    # AMZN: 0.6*0.2 + 0.4*0.7 = 0.40
    assert scores["AAPL"] == pytest.approx(0.52)
    assert scores["AMZN"] == pytest.approx(0.40)
    # AAPL should have highest score at date 0
    assert scores["AAPL"] == scores.max()


def test_composite_score_negative_weight():
    """Negative weights invert the feature (lower = better)."""
    dates = pd.date_range("2024-01-01", periods=1, freq="B")
    tickers = ["A", "B", "C"]
    momentum = pd.DataFrame([[0.9, 0.5, 0.1]], index=dates, columns=tickers)
    volatility = pd.DataFrame([[0.8, 0.3, 0.1]], index=dates, columns=tickers)
    features = pd.concat({"mom": momentum, "vol": volatility}, axis=1)

    score_def = [
        {"feature": "mom", "weight": 1.0},
        {"feature": "vol", "weight": -1.0},  # lower vol = better
    ]
    scores = _compute_composite_score(score_def, features, dates[0], tickers)
    # A: 0.9 - 0.8 = 0.1, B: 0.5 - 0.3 = 0.2, C: 0.1 - 0.1 = 0.0
    assert scores["B"] == pytest.approx(0.2)
    assert scores["A"] == pytest.approx(0.1)
    assert scores["C"] == pytest.approx(0.0)
    assert scores["B"] == scores.max()  # B wins: good mom, low vol


def test_composite_score_missing_feature():
    """Missing features are skipped (contribute 0)."""
    dates = pd.date_range("2024-01-01", periods=1, freq="B")
    tickers = ["A", "B"]
    data = pd.DataFrame([[0.5, 0.8]], index=dates, columns=tickers)
    features = pd.concat({"real_feat": data}, axis=1)

    score_def = [
        {"feature": "real_feat", "weight": 1.0},
        {"feature": "nonexistent", "weight": 0.5},  # should be skipped
    ]
    scores = _compute_composite_score(score_def, features, dates[0], tickers)
    assert scores["A"] == pytest.approx(0.5)
    assert scores["B"] == pytest.approx(0.8)


def test_apply_screen_with_composite_score():
    """End-to-end: screen with composite scoring on real data."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    features = compute_all_features()
    screen_def = {
        "name": "composite momentum+quality-vol",
        "hypothesis": "multi-factor composite",
        "filters": [
            {"feature": "close_vs_sma200", "op": ">", "value": 1.0},
        ],
        "score": [
            {"feature": "return_6m_pctrank", "weight": 0.4},
            {"feature": "roe_pctrank", "weight": 0.3},
            {"feature": "volatility_20d_pctrank", "weight": -0.3},
        ],
        "top_n": 20,
        "rank_by": "_score",
        "rank_order": "desc",
    }
    result = apply_screen(screen_def, features)
    assert result["n_months"] > 0
    assert isinstance(result["sharpe"], float)
    assert result.get("score") == screen_def["score"]


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
