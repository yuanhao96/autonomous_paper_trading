"""Tests for strategy registry (SQLite storage)."""

import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from src.core.db import init_db
from src.strategies.registry import StrategyRegistry
from src.strategies.spec import RiskParams, StrategyResult, StrategySpec


@pytest.fixture
def registry(tmp_path):
    """Create a registry with a temporary database."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    init_db(engine)
    return StrategyRegistry(engine=engine)


@pytest.fixture
def sample_spec():
    return StrategySpec(
        template="momentum/momentum-effect-in-stocks",
        parameters={"lookback": 12, "hold_period": 1},
        universe_id="sp500",
        risk=RiskParams(max_position_pct=0.10, max_positions=10),
    )


class TestRegistrySpecs:
    def test_save_and_get(self, registry, sample_spec):
        registry.save_spec(sample_spec)
        loaded = registry.get_spec(sample_spec.id)
        assert loaded is not None
        assert loaded.id == sample_spec.id
        assert loaded.template == sample_spec.template
        assert loaded.parameters == sample_spec.parameters

    def test_get_nonexistent(self, registry):
        assert registry.get_spec("nonexistent") is None

    def test_list_specs(self, registry, sample_spec):
        registry.save_spec(sample_spec)
        specs = registry.list_specs()
        assert len(specs) == 1
        assert specs[0].id == sample_spec.id

    def test_list_by_template(self, registry, sample_spec):
        registry.save_spec(sample_spec)
        specs = registry.list_specs(template="momentum/momentum-effect-in-stocks")
        assert len(specs) == 1
        specs = registry.list_specs(template="other/template")
        assert len(specs) == 0

    def test_delete_spec(self, registry, sample_spec):
        registry.save_spec(sample_spec)
        assert registry.delete_spec(sample_spec.id)
        assert registry.get_spec(sample_spec.id) is None

    def test_delete_nonexistent(self, registry):
        assert not registry.delete_spec("nonexistent")

    def test_upsert(self, registry, sample_spec):
        registry.save_spec(sample_spec)
        sample_spec.name = "updated_name"
        registry.save_spec(sample_spec)
        specs = registry.list_specs()
        assert len(specs) == 1


class TestRegistryResults:
    def test_save_and_get_result(self, registry, sample_spec):
        registry.save_spec(sample_spec)

        result = StrategyResult(
            spec_id=sample_spec.id,
            phase="screen",
            passed=True,
            sharpe_ratio=1.5,
            total_return=0.25,
            max_drawdown=-0.15,
            total_trades=50,
        )
        registry.save_result(result)

        results = registry.get_results(sample_spec.id)
        assert len(results) == 1
        assert results[0].sharpe_ratio == 1.5
        assert results[0].passed is True

    def test_filter_by_phase(self, registry, sample_spec):
        registry.save_spec(sample_spec)

        registry.save_result(StrategyResult(
            spec_id=sample_spec.id, phase="screen", passed=True, sharpe_ratio=1.0
        ))
        registry.save_result(StrategyResult(
            spec_id=sample_spec.id, phase="validate", passed=False, sharpe_ratio=0.3
        ))

        screen_results = registry.get_results(sample_spec.id, phase="screen")
        assert len(screen_results) == 1
        assert screen_results[0].phase == "screen"

    def test_get_best_specs(self, registry):
        for i in range(3):
            spec = StrategySpec(
                template="momentum/test",
                parameters={"lookback": i},
                universe_id="test",
            )
            registry.save_spec(spec)
            registry.save_result(StrategyResult(
                spec_id=spec.id,
                phase="screen",
                passed=True,
                sharpe_ratio=float(i),
            ))

        best = registry.get_best_specs(phase="screen", metric="sharpe_ratio", limit=2)
        assert len(best) == 2
        assert best[0][1].sharpe_ratio >= best[1][1].sharpe_ratio
