"""Tests for src/core/signals.py — signal registry + all signal functions."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.core.signals import SIGNAL_REGISTRY, compute_signal


def _make_price_df(n: int = 300, trend: float = 0.5) -> pd.DataFrame:
    """Create a realistic OHLCV DataFrame."""
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    rng = np.random.default_rng(42)
    close = 100.0 + np.cumsum(rng.normal(trend / n, 1.0, n))
    close = np.maximum(close, 10.0)
    return pd.DataFrame(
        {
            "Open": close * 0.995,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": rng.integers(100_000, 5_000_000, n),
        },
        index=idx,
    )


# All slugs in the registry
_ALL_SLUGS = sorted(SIGNAL_REGISTRY.keys())


class TestSignalRegistry:
    def test_registry_has_all_entries(self):
        """Registry must have 46 existing + 41 new = 87 entries."""
        assert len(SIGNAL_REGISTRY) == 87

    @pytest.mark.parametrize("slug", _ALL_SLUGS)
    def test_signal_returns_valid(self, slug):
        """Every registered signal must return 'long' or 'flat'."""
        df = _make_price_df(300)
        result = compute_signal(slug, df, {})
        assert result in ("long", "flat"), f"Signal for {slug} returned '{result}'"

    def test_unknown_slug_fallback(self):
        """Unknown slug falls back to momentum timeseries."""
        df = _make_price_df(300, trend=2.0)
        result = compute_signal("nonexistent-template", df, {"lookback": 50})
        assert result in ("long", "flat")


class TestExistingSignals:
    """Spot-check existing 46 signal functions."""

    def test_momentum_timeseries_long(self):
        prices = [100 + i * 0.5 for i in range(260)]
        idx = pd.date_range("2020-01-01", periods=260, freq="B")
        df = pd.DataFrame(
            {
                "Open": prices, "High": prices, "Low": prices,
                "Close": prices, "Volume": [1_000_000] * 260,
            },
            index=idx,
        )
        assert compute_signal("time-series-momentum", df, {"lookback": 252}) == "long"

    def test_momentum_timeseries_flat(self):
        prices = [200 - i * 0.5 for i in range(260)]
        idx = pd.date_range("2020-01-01", periods=260, freq="B")
        df = pd.DataFrame(
            {
                "Open": prices, "High": prices, "Low": prices,
                "Close": prices, "Volume": [1_000_000] * 260,
            },
            index=idx,
        )
        assert compute_signal("time-series-momentum", df, {"lookback": 252}) == "flat"

    def test_bollinger_oversold(self):
        # Steady then sharp drop → should be below lower band
        prices = [100.0] * 50 + [80.0]
        idx = pd.date_range("2020-01-01", periods=51, freq="B")
        df = pd.DataFrame(
            {
                "Open": prices, "High": prices, "Low": prices,
                "Close": prices, "Volume": [1_000_000] * 51,
            },
            index=idx,
        )
        assert compute_signal("mean-reversion-bollinger", df, {"bb_period": 20}) == "long"


class TestCategoryASignals:
    """Category A templates should produce valid signals (reuse existing fns)."""

    _CAT_A_SLUGS = [
        "momentum-effect-in-country-equity-indexes",
        "momentum-effect-in-reits",
        "momentum-effect-in-stocks-in-small-portfolios",
        "momentum-in-mutual-fund-returns",
        "momentum-effect-in-commodities-futures",
        "commodities-futures-trend-following",
        "forex-momentum",
        "momentum-strategy-low-frequency-forex",
        "mean-reversion-effect-in-country-equity-indexes",
        "pairs-trading-with-country-etfs",
        "short-term-reversal-with-futures",
        "beta-factor-in-country-equity-indexes",
        "value-effect-within-countries",
    ]

    @pytest.mark.parametrize("slug", _CAT_A_SLUGS)
    def test_category_a_valid(self, slug):
        df = _make_price_df(300)
        result = compute_signal(slug, df, {})
        assert result in ("long", "flat")


class TestCategoryBSignals:
    """Category B templates with new signal functions."""

    _CAT_B_SLUGS = [
        "january-barometer",
        "12-month-cycle-cross-section",
        "lunar-cycle-in-equity-market",
        "option-expiration-week-effect",
        "momentum-and-state-of-market-filters",
        "momentum-and-style-rotation-effect",
        "momentum-short-term-reversal-strategy",
        "improved-momentum-strategy-on-commodities-futures",
        "momentum-effect-combined-with-term-structure-in-commodities",
        "intraday-etf-momentum",
        "price-and-earnings-momentum",
        "sentiment-and-style-rotation-effect-in-stocks",
        "intraday-dynamic-pairs-trading",
        "optimal-pairs-trading",
        "pairs-trading-copula-vs-cointegration",
        "intraday-arbitrage-between-index-etfs",
        "can-crude-oil-predict-equity-returns",
        "trading-with-wti-brent-spread",
        "dynamic-breakout-ii-strategy",
        "capm-alpha-ranking-dow-30",
        "expected-idiosyncratic-skewness",
        "asset-growth-effect",
        "roa-effect-within-stocks",
        "standardized-unexpected-earnings",
        "fundamental-factor-long-short-strategy",
        "stock-selection-based-on-fundamental-factors",
        "exploiting-term-structure-of-vix-futures",
        "risk-premia-in-forex-markets",
    ]

    @pytest.mark.parametrize("slug", _CAT_B_SLUGS)
    def test_category_b_valid(self, slug):
        df = _make_price_df(300)
        result = compute_signal(slug, df, {})
        assert result in ("long", "flat")
