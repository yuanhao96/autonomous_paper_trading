"""Tests for the main orchestrator."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine

from src.core.db import init_db
from src.data.manager import DataManager
from src.live.deployer import Deployer
from src.live.models import Deployment
from src.orchestrator import Orchestrator, PipelineResult
from src.risk.engine import RiskViolation
from src.strategies.registry import StrategyRegistry
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


    def test_run_monitoring_auto_stops_on_violations(self, tmp_engine, mock_dm):
        """run_monitoring() should auto-stop deployments with risk violations."""
        orch = Orchestrator()
        orch._engine = tmp_engine
        orch._dm = mock_dm
        orch._registry = StrategyRegistry(engine=tmp_engine)

        # Create a mock deployment
        deployment = MagicMock(spec=Deployment)
        deployment.id = "test-deploy"
        deployment.spec_id = "test-spec"
        deployment.is_active = True
        deployment.snapshots = []
        orch._deployments = [deployment]

        # Mock deployer to return our deployment list
        mock_deployer = MagicMock(spec=Deployer)
        mock_deployer.list_deployments.return_value = [deployment]
        orch._deployer = mock_deployer

        # Mock monitor to return violations
        violation = RiskViolation(
            rule="max_portfolio_drawdown",
            limit=0.25,
            actual=0.30,
            message="Drawdown 30% exceeds limit 25%",
        )
        mock_monitor = MagicMock()
        mock_monitor.compare.return_value = MagicMock(within_tolerance=True)
        mock_monitor.check_risk.return_value = [violation]
        orch._monitor = mock_monitor

        # Mock monitor_deployment to return report with violations
        with patch.object(orch, "monitor_deployment") as mock_md:
            mock_md.return_value = {
                "deployment_id": "test-deploy",
                "risk_violations": [violation],
                "risk_ok": False,
            }
            reports = orch.run_monitoring()

        assert len(reports) == 1
        assert reports[0].get("auto_stopped") is True
        mock_deployer.stop.assert_called_once_with(deployment)


class TestCLIInfo:
    def test_available_computations(self):
        computations = get_available_computations()
        assert len(computations) >= 5
