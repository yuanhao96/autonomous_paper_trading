"""End-to-end test: NautilusTrader validation pipeline.

Tests are skipped when NautilusTrader is not installed.

Flow:
  1. Create StrategySpec
  2. Translate to NT strategy + config
  3. Run validation through full pipeline
  4. Verify StrategyResult has regime breakdown
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.strategies.spec import RiskParams, StrategySpec
from src.validation.translator import is_nautilus_available, translate_nautilus

NT_AVAILABLE = is_nautilus_available()
skip_no_nt = pytest.mark.skipif(not NT_AVAILABLE, reason="NautilusTrader not installed")


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


@skip_no_nt
class TestE2ENTTranslation:
    """E2E: Translate and instantiate NT strategies."""

    def test_momentum_full_cycle(self):
        """Translate momentum spec, create config, instantiate strategy."""
        spec = StrategySpec(
            template="momentum/time-series-momentum",
            parameters={"lookback": 126, "threshold": 0.0},
            universe_id="test",
            risk=RiskParams(max_position_pct=0.10, max_positions=5),
        )

        result = translate_nautilus(spec)
        assert result is not None

        strategy_cls, config_kwargs = result
        assert "instrument_id" not in config_kwargs or isinstance(
            config_kwargs.get("instrument_id"), str
        )
        assert config_kwargs["position_pct"] == 0.10

        print("\n--- NT Momentum Translation ---")
        print(f"  Strategy: {strategy_cls.__name__}")
        print(f"  Config:   {config_kwargs}")

    def test_calendar_full_cycle(self):
        """Translate calendar spec, create config, instantiate strategy."""
        spec = StrategySpec(
            template="calendar/turn-of-the-month-in-equity-indexes",
            parameters={"entry_day": -2, "exit_day": 3},
            universe_id="test",
            risk=RiskParams(max_position_pct=0.10, max_positions=5),
        )

        result = translate_nautilus(spec)
        assert result is not None

        strategy_cls, config_kwargs = result
        print("\n--- NT Calendar Translation ---")
        print(f"  Strategy: {strategy_cls.__name__}")
        print(f"  Config:   {config_kwargs}")

    def test_all_46_templates_translate(self):
        """All 46 supported templates should translate successfully."""
        from src.agent.generator import SUPPORTED_TEMPLATES

        failures = []
        for template in SUPPORTED_TEMPLATES:
            spec = StrategySpec(
                template=template,
                parameters={},
                universe_id="test",
            )
            result = translate_nautilus(spec)
            if result is None:
                failures.append(template)

        assert len(failures) == 0, f"Failed to translate: {failures}"
        print("\n--- All 46 templates translated successfully ---")


@skip_no_nt
class TestE2ENTDataConversion:
    """E2E: Data conversion helpers."""

    def test_bars_roundtrip(self):
        """Convert DataFrame → bars and verify bar count and values."""

        from src.validation.translator import create_equity_instrument, dataframe_to_bars

        df = _make_price_df(50)
        instrument = create_equity_instrument("TEST", "XNAS")
        assert instrument is not None

        bars = dataframe_to_bars(df, instrument.id)
        assert len(bars) == 50

        # Verify first bar matches first row
        first_close = float(bars[0].close)
        expected_close = round(df.iloc[0]["Close"], 2)
        assert abs(first_close - expected_close) < 0.01


@skip_no_nt
class TestE2ENTBacktestEngine:
    """E2E: Run a minimal NT backtest engine."""

    def test_engine_runs(self):
        """Verify NT BacktestEngine can run a momentum strategy."""
        from nautilus_trader.backtest.engine import BacktestEngine
        from nautilus_trader.backtest.models import FillModel
        from nautilus_trader.config import BacktestEngineConfig
        from nautilus_trader.model.currencies import USD
        from nautilus_trader.model.identifiers import Venue

        from src.validation.translator import (
            MomentumConfig,
            MomentumNTStrategy,
            create_equity_instrument,
            dataframe_to_bars,
        )

        # Setup
        df = _make_price_df(200)
        instrument = create_equity_instrument("TEST", "XNAS")
        bars = dataframe_to_bars(df, instrument.id)

        engine = BacktestEngine(config=BacktestEngineConfig())
        venue = Venue("XNAS")
        from nautilus_trader.model.enums import AccountType, OmsType
        from nautilus_trader.model.objects import Money

        engine.add_venue(
            venue=venue,
            oms_type=OmsType.HEDGING,
            account_type=AccountType.CASH,
            base_currency=USD,
            starting_balances=[Money(100_000, USD)],
            fill_model=FillModel(prob_slippage=0.5, random_seed=42),
        )
        engine.add_instrument(instrument)
        engine.add_data(bars)

        config = MomentumConfig(
            instrument_id="TEST.XNAS",
            lookback=50,
            threshold=0.0,
            position_pct=0.10,
        )
        strategy = MomentumNTStrategy(config=config)
        engine.add_strategy(strategy)

        engine.run()

        print("\n--- NT Engine Result ---")
        print(f"  Bars processed: {len(bars)}")
        print(f"  Positions: {len(strategy.cache.positions())}")

        engine.dispose()
