"""Tests for StrategySpec round-trip serialization including universe_spec."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from src.core.db import init_db
from src.strategies.registry import StrategyRegistry
from src.strategies.spec import RiskParams, StrategySpec
from src.universe.spec import Filter, UniverseSpec


def _make_spec_with_universe() -> StrategySpec:
    """Create a StrategySpec with a populated universe_spec."""
    spec = StrategySpec(
        template="momentum/time-series-momentum",
        parameters={"lookback": 126, "threshold": 0.01},
        universe_id="sector_etfs",
        risk=RiskParams(max_position_pct=0.10, max_positions=5),
    )
    spec.universe_spec = UniverseSpec(
        asset_class="etf",
        static_symbols=["SPY", "QQQ", "IWM"],
        filters=[
            Filter(field="avg_daily_volume", operator="greater_than", value=1_000_000),
        ],
        max_securities=20,
        min_securities=3,
        rebalance_frequency="monthly",
        id="test-universe",
        name="test-universe",
    )
    return spec


class TestRegistryRoundTrip:
    """Verify that StrategySpec survives save → load round-trip."""

    @pytest.fixture
    def registry(self, tmp_path):
        engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", echo=False)
        init_db(engine)
        return StrategyRegistry(engine=engine)

    def test_universe_spec_survives_round_trip(self, registry):
        """universe_spec should be preserved after save → load."""
        spec = _make_spec_with_universe()
        registry.save_spec(spec)

        loaded = registry.get_spec(spec.id)
        assert loaded is not None
        assert loaded.universe_spec is not None
        assert loaded.universe_spec.asset_class == "etf"
        assert loaded.universe_spec.static_symbols == ["SPY", "QQQ", "IWM"]
        assert loaded.universe_spec.max_securities == 20
        assert loaded.universe_spec.min_securities == 3
        assert loaded.universe_spec.rebalance_frequency == "monthly"
        assert loaded.universe_spec.id == "test-universe"
        assert loaded.universe_spec.name == "test-universe"

    def test_universe_spec_filters_survive(self, registry):
        """Filters within universe_spec should serialize correctly."""
        spec = _make_spec_with_universe()
        registry.save_spec(spec)

        loaded = registry.get_spec(spec.id)
        assert loaded is not None
        assert loaded.universe_spec is not None
        assert len(loaded.universe_spec.filters) == 1
        f = loaded.universe_spec.filters[0]
        assert f.field == "avg_daily_volume"
        assert f.operator == "greater_than"
        assert f.value == 1_000_000

    def test_none_universe_spec_round_trip(self, registry):
        """A spec with universe_spec=None should remain None after load."""
        spec = StrategySpec(
            template="momentum/time-series-momentum",
            parameters={"lookback": 252},
            universe_id="sector_etfs",
        )
        assert spec.universe_spec is None
        registry.save_spec(spec)

        loaded = registry.get_spec(spec.id)
        assert loaded is not None
        assert loaded.universe_spec is None

    def test_computed_universe_round_trip(self, registry):
        """A computed universe with computation params should survive."""
        spec = StrategySpec(
            template="pairs-trading",
            parameters={"lookback": 60},
            universe_id="cointegration_pairs",
        )
        spec.universe_spec = UniverseSpec(
            asset_class="us_equity",
            computation="cointegration_pairs",
            computation_params={"min_half_life": 5, "max_half_life": 120},
            id="coint-pairs",
            name="coint-pairs",
        )
        registry.save_spec(spec)

        loaded = registry.get_spec(spec.id)
        assert loaded is not None
        assert loaded.universe_spec is not None
        assert loaded.universe_spec.computation == "cointegration_pairs"
        assert loaded.universe_spec.computation_params == {
            "min_half_life": 5, "max_half_life": 120,
        }

    def test_core_fields_survive_round_trip(self, registry):
        """Non-universe fields should still round-trip correctly."""
        spec = _make_spec_with_universe()
        registry.save_spec(spec)

        loaded = registry.get_spec(spec.id)
        assert loaded is not None
        assert loaded.id == spec.id
        assert loaded.template == spec.template
        assert loaded.parameters == spec.parameters
        assert loaded.universe_id == spec.universe_id
        assert loaded.risk.max_position_pct == spec.risk.max_position_pct
        assert loaded.risk.max_positions == spec.risk.max_positions
