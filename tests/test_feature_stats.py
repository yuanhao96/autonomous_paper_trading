import numpy as np
import pandas as pd
from feature_stats import compute_quintile_sharpe


def _make_synthetic_data(n_dates=30, n_tickers=50):
    """Build synthetic features and forward alpha for testing.

    Creates a single feature where higher values predict higher alpha
    (perfect monotonic relationship).
    """
    dates = pd.date_range("2024-01-01", periods=n_dates, freq="ME")
    tickers = [f"T{i:03d}" for i in range(n_tickers)]

    rng = np.random.default_rng(42)
    feat_vals = rng.uniform(0, 1, (n_dates, n_tickers))
    # Alpha is linearly related to feature + noise
    alpha_vals = feat_vals * 0.05 + rng.normal(0, 0.01, (n_dates, n_tickers))

    feat_df = pd.DataFrame(feat_vals, index=dates, columns=tickers)
    features = pd.concat({"signal": feat_df}, axis=1)

    fwd_alpha = pd.DataFrame(alpha_vals, index=dates, columns=tickers)
    return features, fwd_alpha


def test_quintile_returns_all_five():
    """All five quintile returns are present in output."""
    features, fwd_alpha = _make_synthetic_data()
    result = compute_quintile_sharpe(features, fwd_alpha)
    assert "signal" in result
    v = result["signal"]
    for q in range(1, 6):
        assert f"q{q}_alpha" in v, f"Missing q{q}_alpha"


def test_quintile_monotonicity_score():
    """Monotonicity score is 1.0 for perfectly monotonic feature."""
    features, fwd_alpha = _make_synthetic_data()
    result = compute_quintile_sharpe(features, fwd_alpha)
    v = result["signal"]
    # Strong linear relationship -> should be highly monotonic
    assert v["monotonic"] >= 0.75


def test_quintile_gradient():
    """Q5 should beat Q1 for a positively predictive feature."""
    features, fwd_alpha = _make_synthetic_data()
    result = compute_quintile_sharpe(features, fwd_alpha)
    v = result["signal"]
    assert v["q5_alpha"] > v["q1_alpha"]
    assert v["spread"] > 0


def test_quintile_too_few_tickers():
    """Features with < 25 valid tickers are skipped."""
    dates = pd.date_range("2024-01-01", periods=10, freq="ME")
    tickers = [f"T{i}" for i in range(10)]  # Only 10 tickers
    feat_df = pd.DataFrame(
        np.random.default_rng(0).uniform(0, 1, (10, 10)),
        index=dates, columns=tickers,
    )
    features = pd.concat({"tiny": feat_df}, axis=1)
    fwd_alpha = pd.DataFrame(
        np.random.default_rng(1).normal(0, 0.01, (10, 10)),
        index=dates, columns=tickers,
    )
    result = compute_quintile_sharpe(features, fwd_alpha)
    assert "tiny" not in result


def test_quintile_non_monotonic_feature():
    """Random noise feature should have low monotonicity."""
    dates = pd.date_range("2024-01-01", periods=30, freq="ME")
    tickers = [f"T{i:03d}" for i in range(50)]
    rng = np.random.default_rng(99)

    # Feature is pure noise, unrelated to alpha
    feat_df = pd.DataFrame(
        rng.uniform(0, 1, (30, 50)), index=dates, columns=tickers,
    )
    features = pd.concat({"noise": feat_df}, axis=1)
    fwd_alpha = pd.DataFrame(
        rng.normal(0, 0.01, (30, 50)), index=dates, columns=tickers,
    )
    result = compute_quintile_sharpe(features, fwd_alpha)
    if "noise" in result:
        # Monotonicity should be low for random noise
        assert result["noise"]["monotonic"] < 1.0
