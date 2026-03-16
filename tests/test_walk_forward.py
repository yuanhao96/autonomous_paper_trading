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
