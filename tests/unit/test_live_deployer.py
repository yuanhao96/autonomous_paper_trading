"""Tests for the deployer module."""

from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest
from sqlalchemy import create_engine

from src.core.db import init_db
from src.live.broker import PaperBroker
from src.live.deployer import Deployer
from src.strategies.spec import RiskParams, StrategyResult, StrategySpec


def _make_spec(**kwargs) -> StrategySpec:
    defaults = {
        "template": "momentum/time-series-momentum",
        "parameters": {"lookback": 252, "threshold": 0.0},
        "universe_id": "sp500",
        "risk": RiskParams(max_position_pct=0.10, max_positions=10),
    }
    defaults.update(kwargs)
    return StrategySpec(**defaults)


def _make_result(spec_id: str, phase: str = "screen", passed: bool = True, **kwargs) -> StrategyResult:
    defaults = {
        "spec_id": spec_id,
        "phase": phase,
        "passed": passed,
        "sharpe_ratio": 1.5,
        "max_drawdown": -0.15,
        "total_trades": 50,
        "profit_factor": 1.8,
        "annual_return": 0.12,
    }
    defaults.update(kwargs)
    return StrategyResult(**defaults)


def _make_prices() -> dict[str, pd.DataFrame]:
    n = 310
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    close = pd.Series([100 + i * 0.5 for i in range(n)], index=idx)
    df = pd.DataFrame({
        "Open": close * 0.99, "High": close * 1.01,
        "Low": close * 0.98, "Close": close,
        "Volume": [1_000_000] * n,
    })
    return {"SPY": df, "QQQ": df}


@pytest.fixture
def db_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", echo=False)
    init_db(engine)
    return engine


@pytest.fixture
def paper_broker():
    broker = PaperBroker(initial_cash=100_000, commission_rate=0.001)
    broker.connect()
    broker.set_prices({"SPY": 230.0, "QQQ": 199.0})
    return broker


class TestDeployer:
    def test_validate_readiness_passes(self, db_engine, paper_broker):
        deployer = Deployer(broker=paper_broker, engine=db_engine)
        spec = _make_spec()
        screen = _make_result(spec.id, "screen")
        validation = _make_result(spec.id, "validate")
        checks = deployer.validate_readiness(spec, screen, validation)
        assert all(c.passed for c in checks), [c.message for c in checks if not c.passed]

    def test_validate_readiness_fails_screening(self, db_engine, paper_broker):
        deployer = Deployer(broker=paper_broker, engine=db_engine)
        spec = _make_spec()
        screen = _make_result(spec.id, "screen", passed=False, failure_reason="Low sharpe")
        checks = deployer.validate_readiness(spec, screen)
        names = [c.name for c in checks if not c.passed]
        assert "screening_passed" in names

    def test_validate_readiness_fails_drawdown(self, db_engine, paper_broker):
        deployer = Deployer(broker=paper_broker, engine=db_engine)
        spec = _make_spec()
        screen = _make_result(spec.id, "screen", max_drawdown=-0.50)
        checks = deployer.validate_readiness(spec, screen)
        names = [c.name for c in checks if not c.passed]
        assert "drawdown_limit" in names

    def test_deploy_creates_active_deployment(self, db_engine, paper_broker):
        deployer = Deployer(broker=paper_broker, engine=db_engine)
        spec = _make_spec()
        deployment = deployer.deploy(spec, symbols=["SPY", "QQQ"], mode="paper")
        assert deployment.status == "active"
        assert deployment.spec_id == spec.id
        assert deployment.mode == "paper"
        assert len(deployment.symbols) == 2

    def test_deploy_persists_to_db(self, db_engine, paper_broker):
        deployer = Deployer(broker=paper_broker, engine=db_engine)
        spec = _make_spec()
        deployment = deployer.deploy(spec, symbols=["SPY"])
        loaded = deployer.get_deployment(deployment.id)
        assert loaded is not None
        assert loaded.spec_id == spec.id
        assert loaded.status == "active"

    def test_rebalance_places_orders(self, db_engine, paper_broker):
        deployer = Deployer(broker=paper_broker, engine=db_engine)
        spec = _make_spec()
        deployment = deployer.deploy(spec, symbols=["SPY", "QQQ"])
        prices = _make_prices()
        trades = deployer.rebalance(deployment, spec, prices)
        # Should have placed buy orders for SPY and QQQ
        assert len(trades) >= 1
        assert all(t.side == "buy" for t in trades)

    def test_rebalance_inactive_deployment(self, db_engine, paper_broker):
        deployer = Deployer(broker=paper_broker, engine=db_engine)
        spec = _make_spec()
        deployment = deployer.deploy(spec, symbols=["SPY"])
        deployment.status = "stopped"
        trades = deployer.rebalance(deployment, spec, _make_prices())
        assert len(trades) == 0

    def test_stop_deployment(self, db_engine, paper_broker):
        deployer = Deployer(broker=paper_broker, engine=db_engine)
        spec = _make_spec()
        deployment = deployer.deploy(spec, symbols=["SPY"])
        deployer.stop(deployment)
        assert deployment.status == "stopped"
        assert deployment.stopped_at is not None

    def test_list_deployments(self, db_engine, paper_broker):
        deployer = Deployer(broker=paper_broker, engine=db_engine)
        spec = _make_spec()
        deployer.deploy(spec, symbols=["SPY"])
        deployer.deploy(spec, symbols=["QQQ"])
        all_deps = deployer.list_deployments()
        assert len(all_deps) == 2
        active = deployer.list_deployments(status="active")
        assert len(active) == 2

    def test_rebalance_takes_snapshot(self, db_engine, paper_broker):
        deployer = Deployer(broker=paper_broker, engine=db_engine)
        spec = _make_spec()
        deployment = deployer.deploy(spec, symbols=["SPY"])
        deployer.rebalance(deployment, spec, _make_prices())
        assert len(deployment.snapshots) == 1
        snap = deployment.snapshots[0]
        assert snap.equity > 0
        assert snap.deployment_id == deployment.id

    def test_validate_readiness_fails_without_validation(
        self, db_engine, paper_broker,
    ):
        """Passing validation_result=None must fail the validation_passed check."""
        deployer = Deployer(broker=paper_broker, engine=db_engine)
        spec = _make_spec()
        screen = _make_result(spec.id, "screen")
        checks = deployer.validate_readiness(spec, screen, None)
        names = {c.name: c.passed for c in checks}
        assert "validation_passed" in names
        assert names["validation_passed"] is False

    def test_list_deployments_loads_snapshots(
        self, db_engine, paper_broker,
    ):
        """Deployments loaded from DB should have snapshots hydrated."""
        deployer = Deployer(broker=paper_broker, engine=db_engine)
        spec = _make_spec()
        deployment = deployer.deploy(spec, symbols=["SPY"])
        deployer.rebalance(deployment, spec, _make_prices())
        # Reload from DB
        loaded = deployer.list_deployments(status="active")
        assert len(loaded) == 1
        assert len(loaded[0].snapshots) >= 1
        assert loaded[0].snapshots[0].equity > 0

    def test_get_deployment_loads_snapshots(
        self, db_engine, paper_broker,
    ):
        """get_deployment() should hydrate snapshots and trades."""
        deployer = Deployer(broker=paper_broker, engine=db_engine)
        spec = _make_spec()
        deployment = deployer.deploy(spec, symbols=["SPY"])
        deployer.rebalance(deployment, spec, _make_prices())
        # Reload from DB
        loaded = deployer.get_deployment(deployment.id)
        assert loaded is not None
        assert len(loaded.snapshots) >= 1
        assert len(loaded.trades) >= 1
