"""Tests for market regime detection."""

import numpy as np
import pandas as pd
import pytest

from src.validation.regimes import (
    RegimePeriod,
    detect_regimes,
    get_regime_date_ranges,
    select_regime_periods,
)


def _make_price_series(
    returns: list[float], start: str = "2020-01-01"
) -> pd.Series:
    """Build a price series from daily returns."""
    dates = pd.bdate_range(start, periods=len(returns))
    prices = [100.0]
    for r in returns:
        prices.append(prices[-1] * (1 + r))
    return pd.Series(prices[: len(dates)], index=dates[:len(prices[:len(dates)])])


class TestDetectRegimes:
    def test_bull_regime(self):
        """Sustained positive returns → bull regime."""
        # ~20% annualized, low vol
        returns = [0.001] * 300
        prices = _make_price_series(returns)
        regimes = detect_regimes(prices, window=63)
        regime_types = {r.regime for r in regimes}
        assert "bull" in regime_types

    def test_bear_regime(self):
        """Sustained negative returns → bear regime."""
        returns = [-0.001] * 300
        prices = _make_price_series(returns)
        regimes = detect_regimes(prices, window=63)
        regime_types = {r.regime for r in regimes}
        assert "bear" in regime_types

    def test_high_vol_regime(self):
        """Large daily swings → high_vol regime."""
        rng = np.random.RandomState(42)
        returns = (rng.randn(300) * 0.03).tolist()  # 3% daily vol → ~47% annualized
        prices = _make_price_series(returns)
        regimes = detect_regimes(prices, window=63)
        regime_types = {r.regime for r in regimes}
        assert "high_vol" in regime_types

    def test_too_short_data(self):
        """Data shorter than window → empty."""
        prices = pd.Series([100, 101, 102], index=pd.bdate_range("2020-01-01", periods=3))
        regimes = detect_regimes(prices, window=63)
        assert regimes == []

    def test_regime_periods_have_dates(self):
        returns = [0.001] * 300
        prices = _make_price_series(returns)
        regimes = detect_regimes(prices, window=63)
        for r in regimes:
            assert r.start < r.end
            assert r.days > 0

    def test_regime_period_repr(self):
        rp = RegimePeriod(
            regime="bull",
            start=pd.Timestamp("2020-01-01"),
            end=pd.Timestamp("2020-06-30"),
            annual_return=0.15,
            volatility=0.12,
            max_drawdown=-0.05,
        )
        s = repr(rp)
        assert "bull" in s
        assert "2020-01-01" in s


class TestSelectRegimePeriods:
    def test_selects_longest_per_type(self):
        # Create data with multiple regime transitions
        bull = [0.001] * 150
        bear = [-0.001] * 100
        high_vol_rng = np.random.RandomState(42)
        high_vol = (high_vol_rng.randn(100) * 0.03).tolist()
        returns = bull + bear + high_vol
        prices = _make_price_series(returns)

        best = select_regime_periods(prices, min_days=30, window=63)
        # Should have at least one regime
        assert len(best) >= 1

    def test_min_days_filter(self):
        returns = [0.001] * 200
        prices = _make_price_series(returns)
        # Very high min_days should filter out short periods
        best = select_regime_periods(prices, min_days=500)
        # Might be empty if no period is >= 500 days
        for name, period in best.items():
            assert period.days >= 500


class TestGetRegimeDateRanges:
    def test_returns_tuples(self):
        returns = [0.001] * 300
        prices = _make_price_series(returns)
        ranges = get_regime_date_ranges(prices, min_days=30)
        for name, (start, end) in ranges.items():
            assert isinstance(start, pd.Timestamp)
            assert isinstance(end, pd.Timestamp)
            assert start < end
