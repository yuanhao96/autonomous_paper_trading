"""Tests for strategy capacity analysis."""

import numpy as np
import pandas as pd
import pytest

from src.validation.capacity import CapacityEstimate, estimate_capacity, quick_capacity_check


@pytest.fixture
def sample_prices():
    dates = pd.bdate_range("2020-01-01", periods=252)
    return pd.DataFrame(
        {
            "AAPL": np.linspace(100, 150, 252),
            "MSFT": np.linspace(200, 280, 252),
        },
        index=dates,
    )


@pytest.fixture
def sample_volumes():
    dates = pd.bdate_range("2020-01-01", periods=252)
    return pd.DataFrame(
        {
            "AAPL": [50_000_000] * 252,  # $50M * $125 avg = ~$6.25B daily
            "MSFT": [30_000_000] * 252,  # $30M * $240 avg = ~$7.2B daily
        },
        index=dates,
    )


class TestEstimateCapacity:
    def test_basic_capacity(self, sample_prices, sample_volumes):
        cap = estimate_capacity(
            prices=sample_prices,
            volumes=sample_volumes,
            avg_position_pct=0.10,
            max_positions=10,
        )
        assert cap.max_capital > 0
        assert cap.limiting_factor in ("volume", "impact", "concentration")
        assert cap.avg_daily_volume_usd > 0
        assert cap.is_viable  # Should be way over $50K with this volume

    def test_empty_data(self):
        cap = estimate_capacity(
            prices=pd.DataFrame(),
            volumes=pd.DataFrame(),
        )
        assert cap.max_capital == 0
        assert not cap.is_viable

    def test_low_volume_limits_capacity(self):
        """Very low volume should limit capacity."""
        dates = pd.bdate_range("2020-01-01", periods=100)
        prices = pd.DataFrame({"MICRO": [10.0] * 100}, index=dates)
        volumes = pd.DataFrame({"MICRO": [1000] * 100}, index=dates)  # $10K daily vol
        cap = estimate_capacity(prices=prices, volumes=volumes)
        # With 1% participation of $10K vol → $100 per trade
        assert cap.max_capital < 100_000

    def test_capacity_estimate_repr(self):
        cap = CapacityEstimate(
            max_capital=500_000,
            limiting_factor="volume",
            avg_daily_volume_usd=10_000_000,
            max_participation_rate=0.01,
            details="test",
        )
        assert cap.is_viable


class TestQuickCapacityCheck:
    def test_from_ohlcv_dict(self):
        dates = pd.bdate_range("2020-01-01", periods=100)
        data = {
            "SPY": pd.DataFrame(
                {
                    "Open": [400] * 100,
                    "High": [405] * 100,
                    "Low": [395] * 100,
                    "Close": [400] * 100,
                    "Volume": [80_000_000] * 100,
                },
                index=dates,
            )
        }
        cap = quick_capacity_check(
            symbols=["SPY"],
            data=data,
            position_pct=0.10,
            max_positions=5,
        )
        assert cap.max_capital > 0
        assert cap.is_viable

    def test_empty_data(self):
        cap = quick_capacity_check(symbols=[], data={})
        assert cap.max_capital == 0
        assert not cap.is_viable
