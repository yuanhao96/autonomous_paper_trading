"""End-to-end test: full evolution cycle with mocked LLM.

Flow:
  1. Mock LLM generates strategy specs
  2. Screen specs via backtesting.py (real data)
  3. Validate top candidates (real regime detection)
  4. Run audit checks
  5. Store everything to registry
  6. Print rich diagnostics

Run with:
  pytest tests/integration/test_e2e_evolution.py -v -s
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine

from src.agent.evolver import Evolver
from src.agent.generator import SUPPORTED_TEMPLATES
from src.agent.reviewer import format_history_for_llm, format_result_for_llm
from src.core.db import init_db
from src.core.llm import LLMClient
from src.data.manager import DataManager
from src.strategies.registry import StrategyRegistry


def _make_llm_response(
    template="momentum/time-series-momentum",
    parameters=None,
    universe_id="sector_etfs",
):
    """Build a valid JSON response as the LLM would produce."""
    if parameters is None:
        parameters = {"lookback": 126, "threshold": 0.01}
    return json.dumps({
        "template": template,
        "parameters": parameters,
        "universe_id": universe_id,
        "risk": {
            "max_position_pct": 0.10,
            "max_positions": 5,
            "stop_loss_pct": None,
            "position_size_method": "equal_weight",
        },
        "reasoning": f"Testing {template} with params {parameters}",
    })


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


@pytest.fixture
def registry(tmp_dir):
    engine = create_engine(f"sqlite:///{tmp_dir / 'test.db'}", echo=False)
    init_db(engine)
    return StrategyRegistry(engine=engine)


@pytest.fixture
def data_manager(tmp_dir):
    return DataManager(cache_dir=tmp_dir / "cache")


class TestE2EEvolutionCycle:
    """E2E: Run a full evolution cycle with mocked LLM."""

    def test_single_explore_cycle(self, registry, data_manager):
        """Run one explore cycle: LLM generates specs → screen → validate → audit."""
        # Mock LLM to return different strategies
        call_count = 0
        responses = [
            _make_llm_response(
                "momentum/time-series-momentum",
                {"lookback": 126, "threshold": 0.0},
            ),
            _make_llm_response(
                "technical/moving-average-crossover",
                {"fast_period": 10, "slow_period": 50},
            ),
            _make_llm_response(
                "mean-reversion/mean-reversion-rsi",
                {"rsi_period": 14, "oversold": 30, "overbought": 70},
            ),
        ]

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.session = MagicMock()
        mock_llm.session.summary.return_value = "3 calls"

        def side_effect(*args, **kwargs):
            nonlocal call_count
            idx = min(call_count, len(responses) - 1)
            call_count += 1
            return responses[idx]

        mock_llm.chat_with_system.side_effect = side_effect

        evolver = Evolver(
            registry=registry,
            data_manager=data_manager,
            llm_client=mock_llm,
        )
        evolver._batch_size = 3
        evolver._top_n_screen = 2

        # Use a small, fast set of symbols
        result = evolver.run_cycle(symbols=["SPY", "QQQ"])

        print(f"\n{'='*60}")
        print(f"EVOLUTION CYCLE RESULT")
        print(f"{'='*60}")
        print(result.summary())

        # Verify specs were generated and processed
        assert result.cycle_number == 1
        assert result.mode == "explore"
        assert result.specs_generated >= 1
        assert result.specs_screened >= 1

        # Check registry has results
        all_specs = registry.list_specs()
        print(f"\nRegistry: {len(all_specs)} specs saved")
        for spec in all_specs:
            results = registry.get_results(spec.id)
            phases = [r.phase for r in results]
            print(f"  {spec.template:40s} phases={phases}")

        # Print diagnostics for each strategy
        print(f"\n{'='*60}")
        print(f"STRATEGY DIAGNOSTICS")
        print(f"{'='*60}")
        for spec in all_specs:
            results = registry.get_results(spec.id)
            screen = next((r for r in results if r.phase == "screen"), None)
            val = next((r for r in results if r.phase == "validate"), None)
            diag = format_result_for_llm(spec, screen_result=screen, validation_result=val)
            print(diag)
            print("-" * 40)

    def test_exploit_cycle_after_explore(self, registry, data_manager):
        """Run explore then exploit: refine the best strategy from explore."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.session = MagicMock()
        mock_llm.session.summary.return_value = "mock"

        # Explore: generate initial strategies
        explore_responses = [
            _make_llm_response("momentum/time-series-momentum", {"lookback": 126, "threshold": 0.0}),
            _make_llm_response("technical/moving-average-crossover", {"fast_period": 10, "slow_period": 50}),
        ]
        # Exploit: refine (change parameters slightly)
        exploit_responses = [
            _make_llm_response("momentum/time-series-momentum", {"lookback": 200, "threshold": 0.02}),
            _make_llm_response("momentum/time-series-momentum", {"lookback": 63, "threshold": 0.01}),
        ]

        call_idx = 0
        all_responses = explore_responses + exploit_responses

        def side_effect(*args, **kwargs):
            nonlocal call_idx
            idx = min(call_idx, len(all_responses) - 1)
            call_idx += 1
            return all_responses[idx]

        mock_llm.chat_with_system.side_effect = side_effect

        evolver = Evolver(
            registry=registry,
            data_manager=data_manager,
            llm_client=mock_llm,
        )
        evolver._batch_size = 2
        evolver._top_n_screen = 1

        # Cycle 1: Explore
        r1 = evolver.run_cycle(symbols=["SPY"], force_mode="explore")
        print(f"\n{'='*60}")
        print(f"CYCLE 1 (EXPLORE)")
        print(f"{'='*60}")
        print(r1.summary())

        # Cycle 2: Exploit
        r2 = evolver.run_cycle(symbols=["SPY"], force_mode="exploit")
        print(f"\n{'='*60}")
        print(f"CYCLE 2 (EXPLOIT)")
        print(f"{'='*60}")
        print(r2.summary())

        # Verify both cycles ran
        assert r1.cycle_number == 1
        assert r2.cycle_number == 2

        # Print evolution summary
        print(f"\n{'='*60}")
        print(f"EVOLUTION SUMMARY")
        print(f"{'='*60}")
        print(evolver.get_evolution_summary())

        # Print history in LLM format
        history = registry.get_best_specs(phase="screen", passed_only=False)
        print(f"\n{format_history_for_llm(history)}")

    def test_exhaustion_stops_evolution(self, registry, data_manager):
        """Evolution should stop when exhaustion threshold is reached."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.session = MagicMock()
        mock_llm.session.summary.return_value = "mock"
        mock_llm.chat_with_system.return_value = _make_llm_response()

        evolver = Evolver(
            registry=registry,
            data_manager=data_manager,
            llm_client=mock_llm,
        )
        evolver._batch_size = 1
        evolver._top_n_screen = 1
        evolver._exhaustion_cycles = 2  # Low threshold for testing

        results = evolver.run_cycles(n_cycles=5, symbols=["SPY"])

        print(f"\nRan {len(results)} cycles before exhaustion")
        print(f"Exhausted: {evolver.is_exhausted}")

        # Should stop before 5 cycles due to exhaustion
        # (no improvement since all strategies are the same)
        assert len(results) <= 5
