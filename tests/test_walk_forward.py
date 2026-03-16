"""Tests for walk-forward evaluation."""
import numpy as np
import pandas as pd
import pytest
from pathlib import Path


def test_generate_wf_windows_basic():
    """Walk-forward window generation with known date range."""
    from screen import generate_wf_windows

    dates = pd.date_range("2015-01-02", "2025-12-31", freq="B")
    windows = generate_wf_windows(
        dates, train_months=18, test_months=6,
    )
    assert len(windows) >= 10
    for train_start, train_end, test_start, test_end in windows:
        assert train_start < train_end
        assert train_end <= test_start
        assert test_start < test_end
        train_days = (train_end - train_start).days
        assert 400 < train_days < 600
        test_days = (test_end - test_start).days
        assert 100 < test_days < 250


def test_generate_wf_windows_no_overlap():
    """Test periods should not overlap."""
    from screen import generate_wf_windows

    dates = pd.date_range("2015-01-02", "2025-12-31", freq="B")
    windows = generate_wf_windows(dates, train_months=18, test_months=6)
    test_ranges = [(ts, te) for _, _, ts, te in windows]
    for i in range(len(test_ranges) - 1):
        assert test_ranges[i][1] <= test_ranges[i + 1][0]


def test_generate_wf_windows_short_data():
    """With very short data, should produce at most 1 window."""
    from screen import generate_wf_windows

    dates = pd.date_range("2024-01-02", "2025-06-30", freq="B")
    windows = generate_wf_windows(dates, train_months=18, test_months=6)
    assert len(windows) <= 1


def test_generate_wf_windows_too_short():
    """With data shorter than one train window, should produce 0 windows."""
    from screen import generate_wf_windows

    dates = pd.date_range("2024-06-01", "2025-06-30", freq="B")
    windows = generate_wf_windows(dates, train_months=18, test_months=6)
    assert len(windows) == 0


def test_apply_screen_walk_forward():
    """Walk-forward backtest on real data."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    from screen import apply_screen, compute_all_features

    features = compute_all_features()
    screen_def = {
        "name": "test wf",
        "hypothesis": "testing walk-forward",
        "filters": [],
        "score": [
            {"feature": "volatility_20d_pctrank", "weight": 1.0},
        ],
        "top_n": 30,
        "rank_by": "_score",
        "rank_order": "desc",
        "holding_days": 21,
    }
    result = apply_screen(
        screen_def, features,
        walk_forward=True, train_months=18, test_months=6,
    )
    assert "wf_oos_sharpe_mean" in result
    assert "wf_oos_sharpe_std" in result
    assert "wf_n_windows" in result
    assert result["wf_n_windows"] >= 1
    assert isinstance(result["wf_oos_sharpe_mean"], float)
    assert "sharpe" in result
    assert result["n_months"] > 0
    if result["wf_oos_sharpe_mean"] >= 0.3:
        assert result["verdict"] == "KEEP"
    else:
        assert result["verdict"] == "DISCARD"


def test_apply_screen_walk_forward_per_window():
    """Walk-forward result includes per-window breakdown."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    from screen import apply_screen, compute_all_features

    features = compute_all_features()
    screen_def = {
        "name": "test wf detail",
        "hypothesis": "testing",
        "filters": [],
        "score": [
            {"feature": "volatility_20d_pctrank", "weight": 1.0},
        ],
        "top_n": 30,
        "rank_by": "_score",
        "rank_order": "desc",
    }
    result = apply_screen(
        screen_def, features,
        walk_forward=True, train_months=18, test_months=6,
    )
    assert "wf_windows" in result
    for w in result["wf_windows"]:
        assert "train_start" in w
        assert "test_start" in w
        assert "sharpe_is" in w
        assert "sharpe_oos" in w


def test_apply_screen_no_walk_forward_backward_compat():
    """Without walk_forward, behavior unchanged."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    from screen import apply_screen, compute_all_features

    features = compute_all_features()
    screen_def = {
        "name": "test compat",
        "hypothesis": "testing",
        "filters": [
            {"feature": "return_3m", "op": ">", "value": 0.05},
        ],
        "top_n": 20,
    }
    result = apply_screen(screen_def, features)
    assert "wf_oos_sharpe_mean" not in result
    assert "sharpe" in result


def test_apply_screen_walk_forward_zero_windows():
    """Walk-forward with insufficient data returns DISCARD gracefully."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    from screen import apply_screen, compute_all_features

    features = compute_all_features()
    screen_def = {
        "name": "test zero wf",
        "hypothesis": "testing",
        "filters": [],
        "score": [
            {"feature": "volatility_20d_pctrank", "weight": 1.0},
        ],
        "top_n": 30,
        "rank_by": "_score",
        "rank_order": "desc",
    }
    result = apply_screen(
        screen_def, features,
        start="2025-01-01", end="2025-06-30",
        walk_forward=True, train_months=18, test_months=6,
    )
    assert result["wf_n_windows"] == 0
    assert result["verdict"] == "DISCARD"
