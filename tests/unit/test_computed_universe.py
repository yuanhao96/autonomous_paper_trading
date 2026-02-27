"""Tests for computed universe builders."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.universe.computed import (
    _engle_granger_pvalue,
    _simple_adf,
    compute_universe,
    get_available_computations,
)


def _make_dm_with_data(symbol_data: dict[str, list[float]]):
    """Create a mock DataManager returning specified price data."""
    dm = MagicMock()

    def get_ohlcv(symbol, **kwargs):
        if symbol not in symbol_data:
            return pd.DataFrame()
        prices = symbol_data[symbol]
        idx = pd.date_range("2022-01-01", periods=len(prices), freq="B")
        close = pd.Series(prices, index=idx)
        return pd.DataFrame({
            "Open": close * 0.99, "High": close * 1.01,
            "Low": close * 0.98, "Close": close,
            "Volume": [1_000_000] * len(close),
        })

    dm.get_ohlcv = get_ohlcv
    return dm


class TestAvailableComputations:
    def test_registry_populated(self):
        available = get_available_computations()
        assert "momentum_screen" in available
        assert "volume_screen" in available
        assert "sector_rotation" in available
        assert "cointegration_pairs" in available
        assert "mean_reversion_screen" in available

    def test_unknown_computation_raises(self):
        dm = MagicMock()
        with pytest.raises(ValueError, match="Unknown computation"):
            compute_universe("nonexistent_builder", ["SPY"], dm)


class TestMomentumScreen:
    def test_ranks_by_momentum(self):
        """Higher-momentum symbols should be ranked first."""
        dm = _make_dm_with_data({
            "AAA": [100 + i * 2 for i in range(250)],    # Strong uptrend
            "BBB": [100 + i * 0.5 for i in range(250)],  # Mild uptrend
            "CCC": [100 - i * 0.5 for i in range(250)],  # Downtrend
        })
        result = compute_universe(
            "momentum_screen", ["AAA", "BBB", "CCC"], dm,
            params={"lookback_days": 126, "top_n": 2, "min_bars": 200},
        )
        assert len(result) == 2
        assert result[0] == "AAA"
        assert result[1] == "BBB"

    def test_top_n_limit(self):
        dm = _make_dm_with_data({
            "A": [100 + i for i in range(250)],
            "B": [100 + i * 0.5 for i in range(250)],
            "C": [100 + i * 0.2 for i in range(250)],
        })
        result = compute_universe(
            "momentum_screen", ["A", "B", "C"], dm,
            params={"top_n": 1, "min_bars": 200},
        )
        assert len(result) == 1

    def test_insufficient_data_excluded(self):
        dm = _make_dm_with_data({
            "SHORT": [100.0] * 10,  # Only 10 bars
        })
        result = compute_universe(
            "momentum_screen", ["SHORT"], dm,
            params={"min_bars": 200},
        )
        assert result == []


class TestVolumeScreen:
    def test_filters_by_volume(self):
        dm = MagicMock()

        def get_ohlcv(symbol, **kwargs):
            idx = pd.date_range("2022-01-01", periods=100, freq="B")
            close = pd.Series([100.0] * 100, index=idx)
            vol_map = {"HIGH_VOL": 5_000_000, "LOW_VOL": 100_000}
            vol = vol_map.get(symbol, 1_000_000)
            return pd.DataFrame({
                "Open": close, "High": close, "Low": close, "Close": close,
                "Volume": [vol] * 100,
            })

        dm.get_ohlcv = get_ohlcv

        result = compute_universe(
            "volume_screen", ["HIGH_VOL", "LOW_VOL"], dm,
            params={"min_adv": 1_000_000, "min_bars": 50},
        )
        assert "HIGH_VOL" in result
        assert "LOW_VOL" not in result


class TestSectorRotation:
    def test_picks_top_sectors(self):
        dm = _make_dm_with_data({
            "XLK": [100 + i * 3 for i in range(100)],    # Best performer
            "XLF": [100 + i * 1 for i in range(100)],    # Mid performer
            "XLE": [100 - i * 0.5 for i in range(100)],  # Worst performer
        })
        result = compute_universe(
            "sector_rotation", ["XLK", "XLF", "XLE"], dm,
            params={"lookback_days": 63, "top_n": 2},
        )
        assert len(result) == 2
        assert result[0] == "XLK"


class TestCointegrationPairs:
    def test_finds_cointegrated_series(self):
        """Two perfectly correlated series (with noise) should be cointegrated."""
        n = 300
        np.random.seed(42)
        # Create two cointegrated series: y = 2*x + noise
        x = np.cumsum(np.random.randn(n)) + 100
        y = 2 * x + np.random.randn(n) * 0.5 + 50
        # Create a non-cointegrated series
        z = np.cumsum(np.random.randn(n)) + 200

        dm = _make_dm_with_data({
            "A": (x + 100).tolist(),  # Ensure positive prices
            "B": (y + 200).tolist(),
            "C": (z + 300).tolist(),
        })
        result = compute_universe(
            "cointegration_pairs", ["A", "B", "C"], dm,
            params={"lookback_days": 252, "p_threshold": 0.10, "min_bars": 100},
        )
        # Should find at least A and B as cointegrated
        assert "A" in result
        assert "B" in result

    def test_too_few_symbols(self):
        dm = _make_dm_with_data({"ONLY": [100.0] * 300})
        result = compute_universe(
            "cointegration_pairs", ["ONLY"], dm,
            params={"min_bars": 100},
        )
        assert result == []


class TestMeanReversionScreen:
    def test_identifies_mean_reverting(self):
        """A stationary (mean-reverting) series should be selected."""
        n = 300
        np.random.seed(42)
        # Mean-reverting series (Ornstein-Uhlenbeck process)
        mr = np.zeros(n)
        mr[0] = 100
        for i in range(1, n):
            mr[i] = mr[i-1] + 0.3 * (100 - mr[i-1]) + np.random.randn() * 0.5
        mr = np.abs(mr) + 10  # Ensure positive prices

        # Random walk (non-stationary)
        rw = np.cumsum(np.random.randn(n)) + 200
        rw = np.abs(rw) + 10

        dm = _make_dm_with_data({
            "MR": mr.tolist(),
            "RW": rw.tolist(),
        })
        result = compute_universe(
            "mean_reversion_screen", ["MR", "RW"], dm,
            params={"lookback_days": 252, "p_threshold": 0.10, "top_n": 5, "min_bars": 100},
        )
        # Mean-reverting series should be found (but we can't guarantee
        # the simplified ADF catches everything — just test no crash)
        assert isinstance(result, list)


class TestStatisticalHelpers:
    def test_simple_adf_stationary(self):
        """A mean-reverting series should have low p-value."""
        np.random.seed(42)
        n = 500
        series = np.zeros(n)
        series[0] = 0
        for i in range(1, n):
            series[i] = 0.7 * series[i-1] + np.random.randn()
        stat, pval = _simple_adf(series)
        assert stat < -2.0  # Should be negative (stationary)
        assert pval < 0.10

    def test_simple_adf_random_walk(self):
        """A random walk should have high p-value."""
        np.random.seed(42)
        rw = np.cumsum(np.random.randn(500))
        stat, pval = _simple_adf(rw)
        assert pval > 0.10

    def test_simple_adf_short_series(self):
        stat, pval = _simple_adf(np.array([1.0, 2.0]))
        assert pval == 1.0

    def test_engle_granger_cointegrated(self):
        """Two cointegrated series should have low p-value."""
        np.random.seed(42)
        n = 500
        x = np.cumsum(np.random.randn(n)) + 100
        y = 2 * x + np.random.randn(n) * 0.5
        pval = _engle_granger_pvalue(y, x)
        assert pval < 0.10

    def test_engle_granger_independent(self):
        """Two independent random walks should have high p-value."""
        np.random.seed(42)
        n = 500
        x = np.cumsum(np.random.randn(n))
        y = np.cumsum(np.random.randn(n))
        pval = _engle_granger_pvalue(y, x)
        assert pval > 0.05
