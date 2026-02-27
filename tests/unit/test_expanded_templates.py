"""Tests for Phase F expanded strategy templates (46 total).

Verifies:
  - All translator templates produce valid Strategy classes
  - All signal map entries return valid signals
  - Generator SUPPORTED_TEMPLATES matches translator/signal registries
  - Optimization bounds exist for all templates
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.agent.generator import SUPPORTED_TEMPLATES
from src.live.signals import compute_signals
from src.screening.translator import get_optimization_bounds, translate
from src.strategies.spec import RiskParams, StrategySpec


def _make_spec(template_slug: str, params: dict | None = None) -> StrategySpec:
    """Helper to create a StrategySpec from a slug."""
    return StrategySpec(
        template=f"test/{template_slug}",
        parameters=params or {},
        universe_id="test",
    )


def _make_price_df(n: int = 300, trend: float = 0.5) -> pd.DataFrame:
    """Create a realistic OHLCV DataFrame."""
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    close = 100.0 + np.cumsum(np.random.default_rng(42).normal(trend / n, 1.0, n))
    close = np.maximum(close, 10.0)  # prevent negative prices
    return pd.DataFrame({
        "Open": close * 0.995,
        "High": close * 1.01,
        "Low": close * 0.99,
        "Close": close,
        "Volume": np.random.default_rng(42).integers(100_000, 5_000_000, n),
    }, index=idx)


# All template slugs (the part after "category/") from SUPPORTED_TEMPLATES
_ALL_SLUGS = [t.split("/", 1)[1] for t in SUPPORTED_TEMPLATES]


class TestTranslatorCoverage:
    """Verify translator handles all supported templates."""

    @pytest.mark.parametrize("slug", _ALL_SLUGS)
    def test_translate_produces_strategy(self, slug):
        """Each template slug must produce a non-None strategy class."""
        spec = _make_spec(slug)
        data = _make_price_df(300)
        strategy_cls = translate(spec, data)
        assert strategy_cls is not None, f"translate() returned None for {slug}"

    @pytest.mark.parametrize("slug", _ALL_SLUGS)
    def test_optimization_bounds_exist(self, slug):
        """Each template must have optimization bounds (or empty dict)."""
        spec = _make_spec(slug)
        bounds = get_optimization_bounds(spec)
        assert isinstance(bounds, dict), f"get_optimization_bounds() failed for {slug}"


class TestSignalCoverage:
    """Verify signal engine handles all supported templates."""

    @pytest.mark.parametrize("slug", _ALL_SLUGS)
    def test_signal_returns_valid(self, slug):
        """Each template slug must produce 'long' or 'flat' signal."""
        spec = _make_spec(slug)
        df = _make_price_df(300)
        signals = compute_signals(spec, {"TEST": df}, lookback_bars=10)
        assert signals["TEST"] in ("long", "flat"), (
            f"Signal for {slug} returned '{signals['TEST']}'"
        )


class TestTemplateConsistency:
    """Cross-check that generator, translator, and signals all agree."""

    def test_supported_templates_count(self):
        """Should have 46 supported templates."""
        assert len(SUPPORTED_TEMPLATES) == 46

    def test_all_templates_have_category_format(self):
        for t in SUPPORTED_TEMPLATES:
            assert "/" in t, f"Template '{t}' missing category/ prefix"

    def test_templates_cover_all_categories(self):
        """At least 8 categories should be represented."""
        categories = {t.split("/")[0] for t in SUPPORTED_TEMPLATES}
        assert len(categories) >= 8
        expected = {"momentum", "mean-reversion", "technical", "factor", "value",
                    "calendar", "volatility", "forex", "commodities"}
        assert expected.issubset(categories), f"Missing categories: {expected - categories}"


class TestNewMomentumTemplates:
    """Spot-check a few of the newly added momentum templates."""

    def test_momentum_volatility_signal(self):
        spec = _make_spec(
            "momentum-and-reversal-combined-with-volatility-effect-in-stocks",
            {"mom_lookback": 126, "vol_lookback": 20},
        )
        df = _make_price_df(300, trend=0.3)
        signals = compute_signals(spec, {"SPY": df}, lookback_bars=10)
        assert signals["SPY"] in ("long", "flat")

    def test_residual_momentum_signal(self):
        spec = _make_spec("residual-momentum", {"lookback": 126, "market_lookback": 126})
        df = _make_price_df(300)
        signals = compute_signals(spec, {"SPY": df}, lookback_bars=10)
        assert signals["SPY"] in ("long", "flat")


class TestNewCalendarTemplates:
    """Spot-check calendar anomaly templates."""

    def test_turn_of_month(self):
        spec = _make_spec("turn-of-the-month-in-equity-indexes", {"entry_day": -2, "exit_day": 3})
        df = _make_price_df(60)
        signals = compute_signals(spec, {"SPY": df}, lookback_bars=5)
        assert signals["SPY"] in ("long", "flat")

    def test_january_effect(self):
        spec = _make_spec("january-effect-in-stocks", {})
        df = _make_price_df(60)
        signals = compute_signals(spec, {"SPY": df}, lookback_bars=5)
        assert signals["SPY"] in ("long", "flat")

    def test_pre_holiday(self):
        spec = _make_spec("pre-holiday-effect", {"days_before": 1})
        df = _make_price_df(60)
        signals = compute_signals(spec, {"SPY": df}, lookback_bars=5)
        assert signals["SPY"] in ("long", "flat")


class TestNewVolatilityTemplates:
    """Spot-check volatility templates."""

    def test_vol_risk_premium(self):
        spec = _make_spec("volatility-risk-premium-effect", {"lookback": 20})
        df = _make_price_df(100)
        signals = compute_signals(spec, {"SPY": df}, lookback_bars=10)
        assert signals["SPY"] in ("long", "flat")

    def test_vix_mean_reversion(self):
        spec = _make_spec("vix-predicts-stock-index-returns", {"threshold": 20})
        df = _make_price_df(100)
        signals = compute_signals(spec, {"SPY": df}, lookback_bars=10)
        assert signals["SPY"] in ("long", "flat")


class TestNewFactorTemplates:
    """Spot-check factor investing templates."""

    def test_fama_french(self):
        spec = _make_spec("fama-french-five-factors", {"lookback": 126})
        df = _make_price_df(200)
        signals = compute_signals(spec, {"SPY": df}, lookback_bars=10)
        assert signals["SPY"] in ("long", "flat")

    def test_g_score(self):
        spec = _make_spec("g-score-investing", {"lookback": 126})
        df = _make_price_df(200)
        signals = compute_signals(spec, {"SPY": df}, lookback_bars=10)
        assert signals["SPY"] in ("long", "flat")
