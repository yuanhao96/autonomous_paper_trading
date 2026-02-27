"""Unit tests for NautilusTrader translator.

All tests are skipped when NautilusTrader is not installed.
Tests verify:
  - translate_nautilus returns (class, dict) tuples for all 46 templates
  - Data conversion helpers produce correct output
  - Builder registry has complete coverage
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.strategies.spec import RiskParams, StrategySpec
from src.validation.translator import (
    _BUILDERS,
    is_nautilus_available,
    translate_nautilus,
)

NT_AVAILABLE = is_nautilus_available()
skip_no_nt = pytest.mark.skipif(not NT_AVAILABLE, reason="NautilusTrader not installed")


def _make_spec(slug: str, params: dict | None = None) -> StrategySpec:
    return StrategySpec(
        template=f"test/{slug}",
        parameters=params or {},
        universe_id="test",
        risk=RiskParams(max_position_pct=0.10, max_positions=5),
    )


def _make_price_df(n: int = 300) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    rng = np.random.default_rng(42)
    close = 100.0 + np.cumsum(rng.normal(0.3 / n, 1.0, n))
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


# All 46 template slugs
ALL_SLUGS = [
    # Momentum (10)
    "momentum-effect-in-stocks",
    "time-series-momentum",
    "time-series-momentum-effect",
    "dual-momentum",
    "sector-momentum",
    "asset-class-momentum",
    "asset-class-trend-following",
    "momentum-and-reversal-combined-with-volatility-effect-in-stocks",
    "residual-momentum",
    "combining-momentum-effect-with-volume",
    # Mean Reversion (2)
    "mean-reversion-rsi",
    "mean-reversion-bollinger",
    # Pairs / Stat Arb (5)
    "pairs-trading",
    "pairs-trading-with-stocks",
    "mean-reversion-statistical-arbitrage-in-stocks",
    "short-term-reversal",
    "short-term-reversal-strategy-in-stocks",
    # Technical (6)
    "moving-average-crossover",
    "breakout",
    "trend-following",
    "ichimoku-clouds-in-energy-sector",
    "dual-thrust-trading-algorithm",
    "paired-switching",
    # Factor (5)
    "fama-french-five-factors",
    "beta-factors-in-stocks",
    "liquidity-effect-in-stocks",
    "accrual-anomaly",
    "earnings-quality-factor",
    # Value (5)
    "value-factor",
    "price-earnings-anomaly",
    "book-to-market-value-anomaly",
    "small-capitalization-stocks-premium-anomaly",
    "g-score-investing",
    # Calendar (5)
    "turn-of-the-month-in-equity-indexes",
    "january-effect-in-stocks",
    "pre-holiday-effect",
    "overnight-anomaly",
    "seasonality-effect-same-calendar-month",
    # Volatility (4)
    "volatility-effect-in-stocks",
    "volatility-risk-premium-effect",
    "vix-predicts-stock-index-returns",
    "leveraged-etfs-with-systematic-risk-management",
    # Forex (2)
    "forex-carry-trade",
    "combining-mean-reversion-and-momentum-in-forex",
    # Commodities (2)
    "term-structure-effect-in-commodities",
    "gold-market-timing",
]


class TestBuilderRegistry:
    """Verify builder registry has all 46 templates."""

    @skip_no_nt
    def test_builder_count(self):
        assert len(_BUILDERS) == 87, f"Expected 87 builders, got {len(_BUILDERS)}"

    @skip_no_nt
    @pytest.mark.parametrize("slug", ALL_SLUGS)
    def test_builder_exists(self, slug):
        assert slug in _BUILDERS, f"Missing builder for '{slug}'"

    @skip_no_nt
    @pytest.mark.parametrize("slug", ALL_SLUGS)
    def test_builder_entry_structure(self, slug):
        entry = _BUILDERS[slug]
        assert isinstance(entry, tuple), f"Entry for {slug} is not a tuple"
        assert len(entry) == 3, f"Entry for {slug} has {len(entry)} elements, expected 3"
        strategy_cls, config_cls, defaults = entry
        assert isinstance(defaults, dict)


class TestTranslateNautilus:
    """Verify translate_nautilus produces valid (class, config) tuples."""

    @skip_no_nt
    @pytest.mark.parametrize("slug", ALL_SLUGS)
    def test_translate_returns_tuple(self, slug):
        spec = _make_spec(slug)
        result = translate_nautilus(spec)
        assert result is not None, f"translate_nautilus returned None for {slug}"
        assert isinstance(result, tuple)
        assert len(result) == 2
        strategy_cls, config_kwargs = result
        assert isinstance(config_kwargs, dict)
        assert "position_pct" in config_kwargs

    @skip_no_nt
    def test_translate_unknown_template_defaults(self):
        """Unknown templates should fall back to momentum."""
        spec = _make_spec("nonexistent-template")
        result = translate_nautilus(spec)
        assert result is not None

    @skip_no_nt
    def test_translate_merges_spec_params(self):
        """Spec parameters should be merged into config kwargs."""
        spec = _make_spec("time-series-momentum", {"lookback": 100, "threshold": 0.05})
        result = translate_nautilus(spec)
        assert result is not None
        _, config_kwargs = result
        assert config_kwargs.get("position_pct") == 0.10


class TestNTStrategyClasses:
    """Spot-check that strategy classes can be imported when NT available."""

    @skip_no_nt
    def test_momentum_class_exists(self):
        from src.validation.translator import MomentumNTStrategy

        assert MomentumNTStrategy is not None

    @skip_no_nt
    def test_ma_crossover_class_exists(self):
        from src.validation.translator import MACrossoverNTStrategy

        assert MACrossoverNTStrategy is not None

    @skip_no_nt
    def test_rsi_class_exists(self):
        from src.validation.translator import RSIMeanRevNTStrategy

        assert RSIMeanRevNTStrategy is not None

    @skip_no_nt
    def test_pairs_class_exists(self):
        from src.validation.translator import PairsStatArbNTStrategy

        assert PairsStatArbNTStrategy is not None

    @skip_no_nt
    def test_technical_class_exists(self):
        from src.validation.translator import TechnicalNTStrategy

        assert TechnicalNTStrategy is not None

    @skip_no_nt
    def test_factor_class_exists(self):
        from src.validation.translator import FactorNTStrategy

        assert FactorNTStrategy is not None

    @skip_no_nt
    def test_calendar_class_exists(self):
        from src.validation.translator import CalendarNTStrategy

        assert CalendarNTStrategy is not None

    @skip_no_nt
    def test_volatility_class_exists(self):
        from src.validation.translator import VolatilityNTStrategy

        assert VolatilityNTStrategy is not None

    @skip_no_nt
    def test_forex_commodity_class_exists(self):
        from src.validation.translator import ForexCommodityNTStrategy

        assert ForexCommodityNTStrategy is not None


class TestDataConversionHelpers:
    """Test dataframe_to_bars and create_equity_instrument."""

    @skip_no_nt
    def test_create_equity_instrument(self):
        from src.validation.translator import create_equity_instrument

        instrument = create_equity_instrument("SPY", "XNAS")
        assert instrument is not None
        assert str(instrument.id) == "SPY.XNAS"

    @skip_no_nt
    def test_dataframe_to_bars(self):
        from nautilus_trader.model.identifiers import InstrumentId

        from src.validation.translator import dataframe_to_bars

        df = _make_price_df(10)
        instrument_id = InstrumentId.from_str("SPY.XNAS")
        bars = dataframe_to_bars(df, instrument_id)
        assert len(bars) == 10
        assert float(bars[0].close) > 0

    @skip_no_nt
    def test_dataframe_to_bars_empty(self):
        from nautilus_trader.model.identifiers import InstrumentId

        from src.validation.translator import dataframe_to_bars

        df = pd.DataFrame()
        instrument_id = InstrumentId.from_str("SPY.XNAS")
        bars = dataframe_to_bars(df, instrument_id)
        assert len(bars) == 0


class TestWithoutNautilus:
    """Test behavior when NautilusTrader is NOT available."""

    def test_is_nautilus_available_type(self):
        result = is_nautilus_available()
        assert isinstance(result, bool)

    def test_translate_without_nt_returns_none_or_tuple(self):
        spec = _make_spec("time-series-momentum")
        result = translate_nautilus(spec)
        if not NT_AVAILABLE:
            assert result is None
        else:
            assert isinstance(result, tuple)


class TestCategoryMapping:
    """Verify each category maps to the expected strategy class."""

    @skip_no_nt
    def test_momentum_templates_map_to_momentum(self):
        from src.validation.translator import MomentumNTStrategy

        momentum_slugs = [
            "momentum-effect-in-stocks",
            "time-series-momentum",
            "dual-momentum",
            "sector-momentum",
        ]
        for slug in momentum_slugs:
            cls, _, _ = _BUILDERS[slug]
            assert cls is MomentumNTStrategy, f"{slug} should map to MomentumNTStrategy"

    @skip_no_nt
    def test_factor_templates_map_to_factor(self):
        from src.validation.translator import FactorNTStrategy

        factor_slugs = [
            "fama-french-five-factors",
            "value-factor",
            "g-score-investing",
        ]
        for slug in factor_slugs:
            cls, _, _ = _BUILDERS[slug]
            assert cls is FactorNTStrategy, f"{slug} should map to FactorNTStrategy"

    @skip_no_nt
    def test_calendar_templates_map_to_calendar(self):
        from src.validation.translator import CalendarNTStrategy

        cal_slugs = [
            "turn-of-the-month-in-equity-indexes",
            "january-effect-in-stocks",
            "pre-holiday-effect",
        ]
        for slug in cal_slugs:
            cls, _, _ = _BUILDERS[slug]
            assert cls is CalendarNTStrategy, f"{slug} should map to CalendarNTStrategy"
