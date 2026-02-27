"""Tests for the main orchestrator."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import create_engine

from src.core.db import init_db
from src.core.llm import LLMClient
from src.data.manager import DataManager
from src.orchestrator import Orchestrator, PipelineResult
from src.strategies.registry import StrategyRegistry
from src.strategies.spec import RiskParams, StrategyResult, StrategySpec
from src.universe.computed import get_available_computations


def _make_llm_response(template="momentum/time-series-momentum", params=None):
    if params is None:
        params = {"lookback": 126, "threshold": 0.01}
    return json.dumps({
        "template": template,
        "parameters": params,
        "universe_id": "sector_etfs",
        "risk": {
            "max_position_pct": 0.10,
            "max_positions": 5,
            "position_size_method": "equal_weight",
        },
        "reasoning": f"Testing {template}",
    })


class TestPipelineResult:
    def test_summary(self):
        r = PipelineResult(
            specs_generated=5, specs_screened=3,
            specs_validated=2, specs_passed=1,
            best_sharpe=1.5, best_spec_id="abc123",
            duration_seconds=10.0,
        )
        summary = r.summary()
        assert "5 generated" in summary
        assert "1.50" in summary

    def test_empty_result(self):
        r = PipelineResult()
        summary = r.summary()
        assert "0 generated" in summary


class TestOrchestrator:
    @pytest.fixture
    def tmp_engine(self, tmp_path):
        eng = create_engine(f"sqlite:///{tmp_path / 'test.db'}", echo=False)
        init_db(eng)
        return eng

    @pytest.fixture
    def mock_dm(self, tmp_path):
        return DataManager(cache_dir=tmp_path / "cache")

    def test_resolve_symbols_static(self, tmp_engine, mock_dm):
        orch = Orchestrator(universe_id="sector_etfs")
        orch._engine = tmp_engine
        orch._dm = mock_dm
        init_db(tmp_engine)
        symbols = orch.resolve_symbols()
        assert len(symbols) > 0
        assert "XLK" in symbols

    def test_resolve_symbols_override(self, tmp_engine, mock_dm):
        orch = Orchestrator(symbols=["AAPL", "MSFT"])
        orch._engine = tmp_engine
        orch._dm = mock_dm
        symbols = orch.resolve_symbols()
        assert symbols == ["AAPL", "MSFT"]

    def test_resolve_symbols_unknown_fallback(self, tmp_engine, mock_dm):
        orch = Orchestrator(universe_id="nonexistent_universe")
        orch._engine = tmp_engine
        orch._dm = mock_dm
        symbols = orch.resolve_symbols()
        # Should fallback to sector_etfs
        assert len(symbols) > 0

    def test_get_pipeline_status(self, tmp_engine, mock_dm):
        orch = Orchestrator()
        orch._engine = tmp_engine
        orch._dm = mock_dm
        orch._registry = StrategyRegistry(engine=tmp_engine)
        status = orch.get_pipeline_status()
        assert "PIPELINE" in status

    def test_get_strategy_report_not_found(self, tmp_engine, mock_dm):
        orch = Orchestrator()
        orch._engine = tmp_engine
        orch._dm = mock_dm
        orch._registry = StrategyRegistry(engine=tmp_engine)
        report = orch.get_strategy_report("nonexistent")
        assert "not found" in report

    def test_get_evolution_report(self, tmp_engine, mock_dm):
        orch = Orchestrator()
        orch._engine = tmp_engine
        orch._dm = mock_dm
        orch._registry = StrategyRegistry(engine=tmp_engine)
        report = orch.get_evolution_report()
        assert "EVOLUTION" in report


class TestCLIInfo:
    def test_available_computations(self):
        computations = get_available_computations()
        assert len(computations) >= 5
