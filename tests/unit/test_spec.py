"""Tests for strategy and universe spec data models."""

import pytest

from src.strategies.spec import RiskParams, StrategyResult, StrategySpec
from src.universe.spec import Filter, UniverseSpec


# ── RiskParams tests ─────────────────────────────────────────────────


class TestRiskParams:
    def test_defaults(self):
        rp = RiskParams()
        assert rp.max_position_pct == 0.10
        assert rp.max_positions == 10
        assert rp.position_size_method == "equal_weight"

    def test_invalid_stop_loss(self):
        with pytest.raises(ValueError, match="stop_loss_pct"):
            RiskParams(stop_loss_pct=1.5)

    def test_invalid_position_size_method(self):
        with pytest.raises(ValueError, match="position_size_method"):
            RiskParams(position_size_method="random")

    def test_valid_risk_params(self):
        rp = RiskParams(
            stop_loss_pct=0.05,
            take_profit_pct=0.15,
            trailing_stop_pct=0.03,
            max_position_pct=0.20,
            max_positions=5,
            position_size_method="kelly",
        )
        assert rp.stop_loss_pct == 0.05
        assert rp.take_profit_pct == 0.15


# ── StrategySpec tests ───────────────────────────────────────────────


class TestStrategySpec:
    def test_auto_name(self):
        spec = StrategySpec(
            template="momentum/momentum-effect-in-stocks",
            parameters={"lookback": 12},
            universe_id="test_123",
        )
        assert "momentum-effect-in-stocks" in spec.name
        assert spec.version == 1

    def test_explicit_name(self):
        spec = StrategySpec(
            template="momentum/test",
            parameters={},
            universe_id="u1",
            name="my_strategy",
        )
        assert spec.name == "my_strategy"

    def test_id_generated(self):
        s1 = StrategySpec(template="t", parameters={}, universe_id="u")
        s2 = StrategySpec(template="t", parameters={}, universe_id="u")
        assert s1.id != s2.id

    def test_default_created_by(self):
        spec = StrategySpec(template="t", parameters={}, universe_id="u")
        assert spec.created_by == "human"


# ── Filter tests ─────────────────────────────────────────────────────


class TestFilter:
    def test_valid_filter(self):
        f = Filter(field="market_cap", operator="greater_than", value=1e9)
        assert f.field == "market_cap"

    def test_invalid_field(self):
        with pytest.raises(ValueError, match="Unknown filter field"):
            Filter(field="invalid_field", operator="greater_than", value=1)

    def test_invalid_operator(self):
        with pytest.raises(ValueError, match="Unknown operator"):
            Filter(field="market_cap", operator="invalid_op", value=1)


# ── UniverseSpec tests ───────────────────────────────────────────────


class TestUniverseSpec:
    def test_static_universe(self):
        u = UniverseSpec(
            asset_class="us_equity",
            static_symbols=["AAPL", "MSFT"],
        )
        assert u.is_static
        assert not u.is_computed
        assert "static" in u.name

    def test_filtered_universe(self):
        u = UniverseSpec(
            asset_class="us_equity",
            filters=[Filter(field="market_cap", operator="greater_than", value=1e9)],
        )
        assert not u.is_static
        assert "filtered" in u.name

    def test_computed_universe(self):
        u = UniverseSpec(
            asset_class="us_equity",
            computation="cointegration_pairs",
        )
        assert u.is_computed
        assert "computed" in u.name

    def test_invalid_asset_class(self):
        with pytest.raises(ValueError, match="Unknown asset_class"):
            UniverseSpec(asset_class="bonds")

    def test_invalid_rebalance(self):
        with pytest.raises(ValueError, match="Unknown rebalance_frequency"):
            UniverseSpec(asset_class="us_equity", rebalance_frequency="hourly")


# ── StrategyResult tests ─────────────────────────────────────────────


class TestStrategyResult:
    def test_defaults(self):
        r = StrategyResult(spec_id="test", phase="screen")
        assert r.total_return == 0.0
        assert r.passed is False
        assert r.failure_reason is None
