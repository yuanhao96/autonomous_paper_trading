"""Tests for the deployer module."""

import pandas as pd
import pytest
from sqlalchemy import create_engine

from src.core.db import init_db
from src.live.broker import IBKRBroker, PaperBroker
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

    def test_validate_readiness_fails_validation_drawdown(self, db_engine, paper_broker):
        """Validation drawdown exceeding limit should also fail readiness."""
        deployer = Deployer(broker=paper_broker, engine=db_engine)
        spec = _make_spec()
        screen = _make_result(spec.id, "screen", max_drawdown=-0.10)  # OK
        validation = _make_result(spec.id, "validate", max_drawdown=-0.50)  # Bad
        checks = deployer.validate_readiness(spec, screen, validation)
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

    def test_stop_liquidates_positions(self, db_engine):
        """stop() should sell all positions, not just mark status."""
        broker = PaperBroker(initial_cash=100_000, commission_rate=0.0)
        broker.connect()
        broker.set_prices({"SPY": 200.0})
        deployer = Deployer(broker=broker, engine=db_engine)
        spec = _make_spec()
        deployment = deployer.deploy(spec, symbols=["SPY"])
        prices = _make_prices()
        trades = deployer.rebalance(deployment, spec, prices)
        assert len(trades) >= 1
        # Verify positions exist before stop
        positions_before = broker.get_positions()
        assert len(positions_before) > 0
        total_qty_before = sum(p.quantity for p in positions_before)
        assert total_qty_before > 0
        # Stop should liquidate
        deployer.stop(deployment)
        positions_after = broker.get_positions()
        total_qty_after = sum(p.quantity for p in positions_after)
        assert total_qty_after == 0, (
            f"Expected 0 shares after stop, got {total_qty_after}"
        )
        assert deployment.status == "stopped"

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

    def test_get_broker_paper_always_local(self, db_engine):
        """mode='paper' always creates PaperBroker, regardless of ib_insync."""
        deployer = Deployer(engine=db_engine)
        broker = deployer._get_broker("paper")
        assert isinstance(broker, PaperBroker)

    def test_get_broker_ibkr_paper_mode(self, db_engine):
        """mode='ibkr_paper' creates IBKRBroker with port 7497."""
        deployer = Deployer(engine=db_engine)
        broker = deployer._get_broker("ibkr_paper")
        assert isinstance(broker, IBKRBroker)
        assert broker._port == 7497

    def test_get_broker_live_mode(self, db_engine):
        """mode='live' creates IBKRBroker with live port."""
        deployer = Deployer(engine=db_engine)
        broker = deployer._get_broker("live")
        assert isinstance(broker, IBKRBroker)
        assert broker._port == 7496

    def test_rebalance_sets_paper_prices(self, db_engine):
        """rebalance() should auto-set PaperBroker prices from price data."""
        broker = PaperBroker(initial_cash=100_000, commission_rate=0.001)
        broker.connect()
        deployer = Deployer(broker=broker, engine=db_engine)
        spec = _make_spec()
        deployment = deployer.deploy(spec, symbols=["SPY", "QQQ"])
        prices = _make_prices()
        # Don't manually set prices — rebalance should auto-set them
        deployer.rebalance(deployment, spec, prices)
        # Verify prices were set (broker should have traded)
        assert len(broker._current_prices) > 0
        assert broker._current_prices["SPY"] > 0

    def test_get_broker_per_deployment_isolation(self, db_engine):
        """Different deployment IDs get different broker instances."""
        deployer = Deployer(engine=db_engine)
        b1 = deployer._get_broker("paper", "dep1")
        b2 = deployer._get_broker("paper", "dep2")
        assert isinstance(b1, PaperBroker)
        assert isinstance(b2, PaperBroker)
        assert b1 is not b2
        # Same deployment_id returns cached instance
        assert deployer._get_broker("paper", "dep1") is b1

    def test_two_paper_deployments_isolated(self, db_engine):
        """Two paper deployments should not share broker state."""
        deployer = Deployer(engine=db_engine)
        spec = _make_spec()
        d1 = deployer.deploy(spec, symbols=["SPY"], mode="paper")
        d2 = deployer.deploy(spec, symbols=["QQQ"], mode="paper")
        # Each deployment should have its own broker
        b1 = deployer._get_broker("paper", d1.id)
        b2 = deployer._get_broker("paper", d2.id)
        assert b1 is not b2

    def test_restart_rebalance_no_duplicate_trades(self, db_engine):
        """After restart (broker=None), rebalance should not re-enter positions.

        Reproduces Finding 1: first rebalance buys, restart creates fresh
        PaperBroker, second rebalance should see existing positions via
        rehydration and NOT double-buy.
        """
        # Phase 1: Deploy and rebalance normally
        broker1 = PaperBroker(initial_cash=100_000, commission_rate=0.0)
        broker1.connect()
        broker1.set_prices({"SPY": 200.0})
        deployer1 = Deployer(broker=broker1, engine=db_engine)
        spec = _make_spec()
        deployment = deployer1.deploy(spec, symbols=["SPY"])
        prices = _make_prices()
        first_trades = deployer1.rebalance(deployment, spec, prices)
        assert len(first_trades) >= 1

        # Phase 2: Simulate restart — new deployer, no broker
        deployer2 = Deployer(engine=db_engine)
        assert len(deployer2._brokers) == 0  # No brokers after "restart"

        # Reload deployment from DB (as run_rebalance does)
        loaded = deployer2.list_deployments(status="active")
        assert len(loaded) == 1
        dep = loaded[0]

        # Ensure broker is created, then rehydrate from snapshot
        broker2 = deployer2._get_broker(dep.mode, dep.id)
        broker2.connect()
        if isinstance(broker2, PaperBroker) and dep.snapshots:
            latest_snap = dep.snapshots[-1]
            broker2.rehydrate(
                cash=latest_snap.cash, positions=latest_snap.positions,
            )

        # Now rebalance — positions already match target, so 0 trades
        after_restart_trades = deployer2.rebalance(dep, spec, prices)
        assert len(after_restart_trades) == 0, (
            f"Expected 0 trades after restart rehydration, got {len(after_restart_trades)}"
        )
