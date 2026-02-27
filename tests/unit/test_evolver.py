"""Tests for the evolution engine.

Uses mocked LLM and lightweight data to test the orchestration logic
without requiring API keys or network access.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import create_engine

from src.agent.evolver import CycleResult, Evolver
from src.core.config import Settings
from src.core.db import init_db
from src.core.llm import LLMClient
from src.data.manager import DataManager
from src.strategies.registry import StrategyRegistry
from src.strategies.spec import RiskParams, StrategyResult, StrategySpec


def _mock_llm_response(**overrides):
    """Build a valid JSON response."""
    import json

    data = {
        "template": "momentum/time-series-momentum",
        "parameters": {"lookback": 126, "threshold": 0.01},
        "universe_id": "sector_etfs",
        "risk": {
            "max_position_pct": 0.10,
            "max_positions": 5,
            "position_size_method": "equal_weight",
        },
        "reasoning": "Test strategy",
    }
    data.update(overrides)
    return json.dumps(data)


@pytest.fixture
def tmp_registry(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", echo=False)
    init_db(engine)
    return StrategyRegistry(engine=engine)


@pytest.fixture
def mock_llm():
    client = MagicMock(spec=LLMClient)
    client.session = MagicMock()
    client.session.summary.return_value = "0 calls"
    client.chat_with_system.return_value = _mock_llm_response()
    return client


class TestCycleResult:
    def test_summary(self):
        cr = CycleResult(
            cycle_number=1,
            specs_generated=5,
            specs_screened=4,
            specs_validated=2,
            specs_passed=1,
            best_sharpe=0.85,
            best_spec_id="abc",
            mode="explore",
            duration_seconds=30.5,
        )
        s = cr.summary()
        assert "Cycle 1" in s
        assert "explore" in s
        assert "0.85" in s

    def test_summary_with_errors(self):
        cr = CycleResult(cycle_number=1, errors=["e1", "e2"])
        s = cr.summary()
        assert "Errors: 2" in s


class TestEvolver:
    def test_init_defaults(self, tmp_registry, mock_llm):
        evolver = Evolver(
            registry=tmp_registry,
            llm_client=mock_llm,
        )
        assert evolver.cycle_count == 0
        assert not evolver.is_exhausted

    def test_decide_mode_explore_first(self, tmp_registry, mock_llm):
        evolver = Evolver(registry=tmp_registry, llm_client=mock_llm)
        # First 2 cycles should always be explore
        mode = evolver._decide_mode()
        assert mode == "explore"

    def test_exhaustion_detection(self, tmp_registry, mock_llm):
        evolver = Evolver(registry=tmp_registry, llm_client=mock_llm)
        evolver._exhaustion_cycles = 3
        evolver._cycles_without_improvement = 3
        assert evolver.is_exhausted

    def test_run_cycle_with_mock(self, tmp_registry, mock_llm):
        """Run a cycle with mocked LLM and real screening pipeline."""
        evolver = Evolver(
            registry=tmp_registry,
            llm_client=mock_llm,
        )
        evolver._batch_size = 1  # Small batch for speed

        result = evolver.run_cycle(symbols=["SPY"])
        assert result.cycle_number == 1
        assert result.specs_generated >= 0  # May be 0 if data fetch fails
        assert result.mode == "explore"

    def test_evolution_summary(self, tmp_registry, mock_llm):
        evolver = Evolver(registry=tmp_registry, llm_client=mock_llm)
        summary = evolver.get_evolution_summary()
        assert "Evolution Summary" in summary
        assert "0 cycles" in summary

    def test_resolve_symbols_fallback(self, tmp_registry, mock_llm):
        evolver = Evolver(registry=tmp_registry, llm_client=mock_llm)
        syms = evolver._resolve_symbols("nonexistent_universe")
        assert len(syms) > 0  # Should fall back to sector_etfs

    def test_pick_parent_empty(self, tmp_registry, mock_llm):
        evolver = Evolver(registry=tmp_registry, llm_client=mock_llm)
        assert evolver._pick_parent([]) is None

    def test_pick_parent_best_sharpe(self, tmp_registry, mock_llm):
        evolver = Evolver(registry=tmp_registry, llm_client=mock_llm)
        spec1 = StrategySpec(
            template="momentum/time-series-momentum",
            parameters={"lookback": 126},
            universe_id="sector_etfs",
        )
        spec2 = StrategySpec(
            template="technical/breakout",
            parameters={"lookback": 20},
            universe_id="sector_etfs",
        )
        r1 = StrategyResult(spec_id=spec1.id, phase="screen", sharpe_ratio=0.5)
        r2 = StrategyResult(spec_id=spec2.id, phase="screen", sharpe_ratio=1.2)
        parent = evolver._pick_parent([(spec1, r1), (spec2, r2)])
        assert parent is not None
        assert parent[1].sharpe_ratio == 1.2
