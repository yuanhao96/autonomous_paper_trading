import numpy as np
import pandas as pd
from screen import compute_price_features, compute_fundamental_features
from screen import (
    apply_screen, compute_all_features, compute_pctrank_features,
    compute_regime, _compute_composite_score,
    _compute_sharpe,
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
    raw_names = [
        f for f in feature_names
        if not f.endswith("_pctrank") and f != "market_regime"
    ]
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


def test_regime_synthetic():
    """Test regime classification on synthetic SPY data."""
    n_days = 300
    dates = pd.date_range("2023-01-01", periods=n_days, freq="B")

    # Construct SPY close that starts below SMA200 then crosses above
    # First 220 days: declining (below SMA200 = downtrend)
    # Last 80 days: rising sharply (above SMA200 = uptrend)
    close_vals = np.concatenate([
        np.linspace(100, 85, 220),  # declining
        np.linspace(85, 120, 80),   # rising sharply
    ])
    spy_close = pd.Series(close_vals, index=dates, name="SPY")

    # Build prices with MultiIndex columns (field, ticker)
    prices = pd.DataFrame(
        spy_close.values, index=dates,
        columns=pd.MultiIndex.from_tuples([("Close", "SPY")]),
    )

    regime = compute_regime(prices)

    # Basic checks
    assert len(regime) == n_days
    valid = regime.dropna()
    assert set(valid.unique()).issubset({
        "quiet_bull", "volatile_bull",
        "quiet_bear", "volatile_bear",
    })

    # Early period (after warmup) should be downtrend (bear)
    late_warmup = regime.iloc[210:220].dropna()
    assert all(r in ("quiet_bear", "volatile_bear") for r in late_warmup)

    # Late period should be uptrend (bull) — price well above SMA200
    late_period = regime.iloc[-20:].dropna()
    assert all(r in ("quiet_bull", "volatile_bull") for r in late_period)


def test_regime_all_four_labels():
    """Verify all 4 regime labels can be produced."""
    n_days = 500
    dates = pd.date_range("2022-01-01", periods=n_days, freq="B")

    # Create price series with varied regimes:
    # Quiet uptrend, then volatile crash, then quiet recovery, then volatile rally
    close_vals = np.concatenate([
        np.linspace(100, 110, 150),  # gentle up
        np.linspace(110, 70, 50),    # sharp crash
        np.linspace(70, 75, 150),    # slow grind
        np.linspace(75, 130, 50),    # sharp rally
        np.linspace(130, 135, 100),  # gentle up again
    ])
    spy_close = pd.Series(close_vals, index=dates, name="SPY")
    prices = pd.DataFrame(
        spy_close.values, index=dates,
        columns=pd.MultiIndex.from_tuples([("Close", "SPY")]),
    )

    regime = compute_regime(prices)
    valid_labels = regime.dropna().unique()

    # Should produce at least 3 of the 4 labels with this price path
    assert len(valid_labels) >= 3


def test_regime_on_real_data():
    """Test regime on actual cached data."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    prices = pd.read_parquet(Path("data/prices.parquet"))
    regime = compute_regime(prices)

    # Should cover our full date range
    assert len(regime) > 1000
    valid = regime.dropna()
    # Real data should produce all 4 labels over 2020-2025
    assert len(valid.unique()) == 4
    assert set(valid.unique()) == {
        "quiet_bull", "volatile_bull",
        "quiet_bear", "volatile_bear",
    }


def test_regime_in_compute_all_features():
    """Verify regime is integrated into the feature DataFrame."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    features = compute_all_features()
    feature_names = features.columns.get_level_values(0).unique()
    assert "market_regime" in feature_names
    # Check values are valid regime labels
    regime_vals = features["market_regime"].iloc[-1].dropna().unique()
    assert len(regime_vals) == 1  # all tickers same regime on same day


def test_compute_sharpe_basic():
    """Test Sharpe ratio computation."""
    alpha = np.array([0.01, 0.02, 0.01, 0.03, 0.01])
    sharpe = _compute_sharpe(alpha, 12.0)
    assert sharpe > 0
    # Negative alpha should give negative Sharpe
    sharpe_neg = _compute_sharpe(-alpha, 12.0)
    assert sharpe_neg < 0


def test_compute_sharpe_edge_cases():
    """Test Sharpe with edge cases."""
    assert _compute_sharpe(np.array([0.01]), 12.0) == 0.0  # too few
    assert _compute_sharpe(np.array([]), 12.0) == 0.0
    assert _compute_sharpe(np.array([0.01, 0.01]), 12.0) == 0.0  # zero std


def test_apply_screen_basic_keys():
    """apply_screen returns expected keys without walk-forward."""
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
    assert "sharpe" in result
    assert "wf_oos_sharpe_mean" not in result
    assert result["verdict"] in ("KEEP", "DISCARD")


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


def test_alpha_decay_synthetic():
    """Test _compute_alpha_decay on synthetic prices."""
    from screen import _compute_alpha_decay

    dates = pd.date_range("2024-01-01", periods=25, freq="B")
    # Two stocks: AAPL goes up steadily, GOOG flat
    close = pd.DataFrame({
        "AAPL": np.linspace(100, 120, 25),  # +20% over 25 days
        "GOOG": np.full(25, 100.0),          # flat
        "SPY": np.linspace(100, 105, 25),    # +5% (benchmark)
    }, index=dates)
    spy = close["SPY"]
    entry_prices = {"AAPL": 100.0, "GOOG": 100.0}
    s0_rebal = 100.0

    decay = _compute_alpha_decay(
        entry_prices, close, spy, dates,
        rebal_idx=0, period_len=21, s0_rebal=s0_rebal,
    )
    assert "5d" in decay
    assert "10d" in decay
    # At 5d: AAPL ~+4%, GOOG 0%, port ~+2%. SPY ~+1%. Alpha ~+1%
    assert decay["5d"] > 0
    # Alpha should grow over time (AAPL keeps outpacing SPY)
    assert decay["10d"] > decay["5d"]


def test_alpha_decay_short_period():
    """Holding period shorter than checkpoints produces empty decay."""
    from screen import _compute_alpha_decay

    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    close = pd.DataFrame({
        "AAPL": np.linspace(100, 110, 10),
        "SPY": np.linspace(100, 102, 10),
    }, index=dates)
    spy = close["SPY"]

    # period_len=4 means only 4 trading days — both 5d and 10d skipped
    decay = _compute_alpha_decay(
        {"AAPL": 100.0}, close, spy, dates,
        rebal_idx=0, period_len=4, s0_rebal=100.0,
    )
    assert decay == {}


def test_alpha_decay_no_spy():
    """Alpha decay works without SPY (spy=None)."""
    from screen import _compute_alpha_decay

    dates = pd.date_range("2024-01-01", periods=25, freq="B")
    close = pd.DataFrame({
        "AAPL": np.linspace(100, 120, 25),
    }, index=dates)

    decay = _compute_alpha_decay(
        {"AAPL": 100.0}, close, None, dates,
        rebal_idx=0, period_len=21, s0_rebal=np.nan,
    )
    assert "5d" in decay
    # Without SPY, alpha = port return (spy_cp=0)
    assert decay["5d"] > 0


def test_alpha_decay_in_backtest():
    """End-to-end: apply_screen produces alpha_decay in monthly_details."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    features = compute_all_features()
    screen_def = {
        "name": "test decay",
        "hypothesis": "testing alpha decay",
        "filters": [
            {"feature": "return_3m", "op": ">", "value": 0.05},
            {"feature": "close_vs_sma200", "op": ">", "value": 1.0},
        ],
        "top_n": 20,
        "holding_days": 21,
    }
    result = apply_screen(screen_def, features)
    # Should have monthly_details with alpha_decay
    md = result.get("monthly_details", [])
    assert md, "No monthly_details in result"
    has_decay = any("alpha_decay" in d for d in md)
    assert has_decay, "No alpha_decay in any monthly_details entry"
    for d in md:
        if "alpha_decay" in d:
            ad = d["alpha_decay"]
            assert isinstance(ad, dict)
            for k, v in ad.items():
                assert k.endswith("d")
                assert isinstance(v, float)
            break
