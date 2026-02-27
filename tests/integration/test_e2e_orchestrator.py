"""End-to-end test: full pipeline through the Orchestrator.

Flow:
  1. Computed equity screening (momentum, volume, sector rotation)
  2. LLM generates strategy spec (mocked)
  3. Screen via backtesting.py (real data)
  4. Validate top candidate (real regime detection)
  5. Deploy to PaperBroker
  6. Rebalance, monitor, evaluate promotion
  7. Rich diagnostics reporting

Run with:
  pytest tests/integration/test_e2e_orchestrator.py -v -s
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import create_engine

from src.agent.evolver import Evolver
from src.core.db import init_db
from src.core.llm import LLMClient
from src.data.manager import DataManager
from src.live.broker import PaperBroker
from src.live.deployer import Deployer
from src.live.models import Deployment, LiveSnapshot, Position
from src.live.monitor import Monitor
from src.live.promoter import Promoter
from src.live.signals import compute_signals, compute_target_weights
from src.orchestrator import Orchestrator, PipelineResult
from src.reporting.reporter import (
    evolution_summary_report,
    format_deployment,
    format_result,
    format_spec,
    pipeline_status_report,
    strategy_lifecycle_report,
)
from src.strategies.registry import StrategyRegistry
from src.strategies.spec import RiskParams, StrategyResult, StrategySpec
from src.universe.computed import compute_universe, get_available_computations
from src.universe.static import get_static_universe


def _make_llm_response(
    template="momentum/time-series-momentum",
    parameters=None,
    universe_id="sector_etfs",
):
    if parameters is None:
        parameters = {"lookback": 126, "threshold": 0.0}
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
def engine(tmp_dir):
    eng = create_engine(f"sqlite:///{tmp_dir / 'test.db'}", echo=False)
    init_db(eng)
    return eng


@pytest.fixture
def registry(engine):
    return StrategyRegistry(engine=engine)


@pytest.fixture
def data_manager(tmp_dir):
    return DataManager(cache_dir=tmp_dir / "cache")


class TestE2EComputedUniverses:
    """E2E: Computed equity screening with real market data."""

    def test_momentum_screen_real_data(self, data_manager):
        """Screen S&P 500 sample by momentum — top 5."""

        print(f"\n{'='*70}")
        print("E2E: MOMENTUM EQUITY SCREENING (REAL DATA)")
        print(f"{'='*70}")

        # Use a small subset for speed
        base_pool = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV"]

        result = compute_universe(
            "momentum_screen",
            base_pool,
            data_manager,
            params={"lookback_days": 126, "top_n": 5, "min_bars": 200},
        )

        print(f"\n  Base pool: {base_pool}")
        print(f"  Top 5 by 6-month momentum: {result}")
        print(f"  Selected: {len(result)} symbols")

        assert len(result) <= 5
        assert len(result) >= 1
        # All returned symbols should be from the base pool
        for s in result:
            assert s in base_pool

    def test_volume_screen_real_data(self, data_manager):
        """Filter by volume — real data."""

        print(f"\n{'='*70}")
        print("E2E: VOLUME EQUITY SCREENING (REAL DATA)")
        print(f"{'='*70}")

        base_pool = ["SPY", "QQQ", "IWM", "XLK"]

        result = compute_universe(
            "volume_screen",
            base_pool,
            data_manager,
            params={"min_adv": 1_000_000, "period_days": 20, "min_bars": 50},
        )

        print(f"\n  Base pool: {base_pool}")
        print(f"  Passed volume filter (>1M ADV): {result}")

        # Major ETFs should all pass the volume filter
        assert len(result) >= 1

    def test_sector_rotation_real_data(self, data_manager):
        """Sector rotation — pick top sectors by momentum."""

        print(f"\n{'='*70}")
        print("E2E: SECTOR ROTATION SCREENING (REAL DATA)")
        print(f"{'='*70}")

        sectors = ["XLK", "XLV", "XLF", "XLY", "XLP", "XLE", "XLI", "XLU"]

        result = compute_universe(
            "sector_rotation",
            sectors,
            data_manager,
            params={"lookback_days": 63, "top_n": 3},
        )

        print(f"\n  All sectors: {sectors}")
        print(f"  Top 3 by 3-month momentum: {result}")

        assert len(result) <= 3
        assert len(result) >= 1

    def test_all_computations_available(self):
        """All 5 computed builders should be registered."""
        available = get_available_computations()
        print(f"\n  Available computations: {available}")
        assert "momentum_screen" in available
        assert "volume_screen" in available
        assert "sector_rotation" in available
        assert "cointegration_pairs" in available
        assert "mean_reversion_screen" in available


class TestE2EFullPipeline:
    """E2E: Full pipeline from equity screening → evolution → deploy → monitor → report."""

    def test_full_orchestrated_pipeline(self, engine, registry, data_manager):
        """Complete lifecycle through Orchestrator with computed universe."""

        print(f"\n{'='*70}")
        print("PHASE E E2E: FULL ORCHESTRATED PIPELINE")
        print(f"{'='*70}")

        # ── Step 1: Computed equity screening ────────────────────────
        print("\n[1/10] Computed equity screening...")

        base_pool = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF"]
        screened_symbols = compute_universe(
            "momentum_screen",
            base_pool,
            data_manager,
            params={"lookback_days": 126, "top_n": 3, "min_bars": 200},
        )
        print(f"  Base pool: {base_pool}")
        print(f"  Momentum-screened: {screened_symbols}")
        assert len(screened_symbols) >= 1

        # Use the screened symbols (or fallback to SPY/QQQ for test stability)
        symbols = screened_symbols if len(screened_symbols) >= 2 else ["SPY", "QQQ"]

        # ── Step 2: LLM generates strategy (mocked) ─────────────────
        print(f"\n[2/10] Generating strategy via mocked LLM...")

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.session = MagicMock()
        mock_llm.session.summary.return_value = "1 call, 500 tokens"
        mock_llm.chat_with_system.return_value = _make_llm_response(
            "momentum/time-series-momentum",
            {"lookback": 126, "threshold": 0.0},
        )

        evolver = Evolver(
            registry=registry,
            data_manager=data_manager,
            llm_client=mock_llm,
        )
        evolver._batch_size = 1
        evolver._top_n_screen = 1

        cycle_result = evolver.run_cycle(symbols=symbols)
        print(f"  {cycle_result.summary()}")
        assert cycle_result.specs_generated >= 1

        # ── Step 3: Retrieve screened spec and results ───────────────
        print(f"\n[3/10] Retrieving results from registry...")

        all_specs = registry.list_specs()
        assert len(all_specs) >= 1
        spec = all_specs[0]
        results = registry.get_results(spec.id)
        screen_result = next((r for r in results if r.phase == "screen"), None)
        assert screen_result is not None

        validation_result = next((r for r in results if r.phase == "validate"), None)
        if validation_result is None:
            validation_result = screen_result

        print(f"  Strategy: {spec.template}")
        print(f"  Params:   {spec.parameters}")
        print(f"  Screen Sharpe: {screen_result.sharpe_ratio:.2f}")

        # ── Step 4: Rich diagnostics — strategy report ───────────────
        print(f"\n[4/10] Generating rich diagnostics...")

        spec_text = format_spec(spec)
        print(f"\n{spec_text}")

        result_text = format_result(screen_result)
        print(f"\n{result_text}")

        # ── Step 5: Deploy to paper trading ──────────────────────────
        print(f"\n[5/10] Deploying to paper trading...")

        paper_broker = PaperBroker(initial_cash=100_000, commission_rate=0.002)
        paper_broker.connect()

        deployer = Deployer(broker=paper_broker, engine=engine)
        deployment = deployer.deploy(spec, symbols=symbols, mode="paper")

        dep_text = format_deployment(deployment)
        print(f"\n{dep_text}")
        assert deployment.is_active

        # ── Step 6: Fetch data and rebalance ─────────────────────────
        print(f"\n[6/10] Fetching real data and rebalancing...")

        prices: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            df = data_manager.get_ohlcv(symbol, period="2y")
            prices[symbol] = df
            print(f"  {symbol}: {len(df)} bars")

        current_prices = {s: float(df["Close"].iloc[-1]) for s, df in prices.items()}
        paper_broker.set_prices(current_prices)

        trades = deployer.rebalance(deployment, spec, prices)
        print(f"  Trades executed: {len(trades)}")
        for t in trades:
            print(f"    {t.side.upper()} {t.quantity} {t.symbol} @ ${t.price:.2f}")

        # ── Step 7: Simulate multi-day monitoring ────────────────────
        print(f"\n[7/10] Simulating 5 days of paper trading...")

        random.seed(42)
        account = paper_broker.get_account_summary()
        base_equity = account["equity"]
        positions = paper_broker.get_positions()

        for day in range(5):
            daily_return = random.gauss(0.0003, 0.008)
            base_equity *= (1 + daily_return)
            snapshot = LiveSnapshot(
                deployment_id=deployment.id,
                timestamp=datetime.utcnow() - timedelta(days=4 - day),
                equity=base_equity,
                cash=base_equity * 0.3,
                positions=[
                    Position(
                        pos.symbol, pos.quantity, pos.avg_cost,
                        pos.quantity * current_prices.get(pos.symbol, pos.avg_cost) * (1 + daily_return),
                        0,
                    )
                    for pos in positions
                ] if positions else [],
            )
            deployment.snapshots.append(snapshot)
            print(f"  Day {day+1}: equity=${snapshot.equity:,.2f} ({daily_return:+.2%})")

        deployment.started_at = datetime.utcnow() - timedelta(days=25)

        # ── Step 8: Monitor and compare ──────────────────────────────
        print(f"\n[8/10] Running monitor comparison...")

        monitor = Monitor()
        comparison = monitor.compare(deployment, validation_result)
        print(f"\n  {comparison.summary()}")

        violations = monitor.check_risk(deployment)
        print(f"  Risk violations: {len(violations)}")

        live_result = monitor.compute_live_result(deployment, spec.id)
        registry.save_result(live_result)
        print(f"  Live result: return={live_result.total_return:+.2%}, "
              f"sharpe={live_result.sharpe_ratio:.2f}")

        # ── Step 9: Evaluate promotion ───────────────────────────────
        print(f"\n[9/10] Evaluating promotion readiness...")

        promoter = Promoter(monitor=monitor)
        promo_summary = promoter.get_promotion_summary(deployment, validation_result)
        print(f"\n{promo_summary}")

        # ── Step 10: Full lifecycle report ───────────────────────────
        print(f"\n[10/10] Generating full lifecycle report...")

        all_results = registry.get_results(spec.id)
        lifecycle_report = strategy_lifecycle_report(
            spec, all_results,
            deployment=deployment,
            comparison=comparison,
        )
        print(f"\n{lifecycle_report}")

        # Evolution summary
        evo_report = evolution_summary_report(
            cycle_results=[{
                "cycle_number": cycle_result.cycle_number,
                "mode": cycle_result.mode,
                "specs_generated": cycle_result.specs_generated,
                "specs_screened": cycle_result.specs_screened,
                "specs_passed": cycle_result.specs_passed,
                "best_sharpe": cycle_result.best_sharpe,
                "duration_seconds": cycle_result.duration_seconds,
            }],
            best_specs=[(spec, screen_result)],
            llm_usage=mock_llm.session.summary(),
        )
        print(f"\n{evo_report}")

        # Pipeline status
        phases = {"screened": 0, "validated": 0, "live": 0}
        for r in all_results:
            if r.phase in phases:
                phases[r.phase] += 1
        status = pipeline_status_report(
            total_specs=len(all_specs),
            phases=phases,
            active_deployments=1 if deployment.is_active else 0,
            best_sharpe=screen_result.sharpe_ratio,
        )
        print(f"\n{status}")

        # ── Assertions ───────────────────────────────────────────────
        result_phases = [r.phase for r in all_results]
        assert "screen" in result_phases
        assert "live" in result_phases
        assert deployment.is_active
        assert len(deployment.snapshots) >= 5

        # Stop deployment
        deployer.stop(deployment)
        assert deployment.status == "stopped"

        print(f"\n{'='*70}")
        print("E2E PHASE E COMPLETE — ALL CHECKS PASSED")
        print(f"{'='*70}")


class TestE2ESignalWithComputedUniverse:
    """E2E: Signal computation using symbols from computed universe."""

    def test_signal_from_screened_universe(self, data_manager):
        """Screen universe by momentum, then compute signals for screened symbols."""

        print(f"\n{'='*70}")
        print("E2E: SIGNALS FROM COMPUTED UNIVERSE")
        print(f"{'='*70}")

        # Screen for top momentum symbols
        base_pool = ["SPY", "QQQ", "IWM", "XLK", "XLF", "XLE"]
        screened = compute_universe(
            "momentum_screen",
            base_pool,
            data_manager,
            params={"lookback_days": 126, "top_n": 4, "min_bars": 200},
        )
        print(f"\n  Screened symbols: {screened}")

        if not screened:
            pytest.skip("No symbols passed momentum screen")

        # Fetch data for screened symbols
        prices: dict[str, pd.DataFrame] = {}
        for s in screened:
            df = data_manager.get_ohlcv(s, period="2y")
            if not df.empty:
                prices[s] = df

        # Test multiple strategy templates on the screened universe
        templates = [
            ("momentum/time-series-momentum", {"lookback": 126, "threshold": 0.0}),
            ("technical/moving-average-crossover", {"fast_period": 10, "slow_period": 50}),
            ("technical/breakout", {"lookback": 20}),
        ]

        for template, params in templates:
            spec = StrategySpec(
                template=template,
                parameters=params,
                universe_id="computed",
                risk=RiskParams(max_position_pct=0.10, max_positions=5),
            )
            signals = compute_signals(spec, prices)
            weights = compute_target_weights(spec, signals)

            name = template.split("/")[-1]
            print(f"\n  {name}:")
            for s in screened:
                if s in signals:
                    print(f"    {s}: signal={signals[s]:5s}  weight={weights[s]:.2f}")

        print(f"\n{'='*70}")
        print("SIGNAL COMPUTATION FROM COMPUTED UNIVERSE COMPLETE")
        print(f"{'='*70}")


class TestE2EOrchestratorReporting:
    """E2E: Orchestrator reporting with registry data."""

    def test_orchestrator_reports(self, engine, registry, data_manager):
        """Orchestrator generates correct pipeline and evolution reports."""

        print(f"\n{'='*70}")
        print("E2E: ORCHESTRATOR REPORTING")
        print(f"{'='*70}")

        # Seed the registry with a spec and result
        spec = StrategySpec(
            template="momentum/time-series-momentum",
            parameters={"lookback": 126},
            universe_id="sector_etfs",
            risk=RiskParams(max_position_pct=0.10, max_positions=5),
        )
        registry.save_spec(spec)
        registry.save_result(StrategyResult(
            spec_id=spec.id,
            phase="screen",
            passed=True,
            sharpe_ratio=1.8,
            annual_return=0.15,
            max_drawdown=-0.12,
            total_trades=45,
        ))

        # Create orchestrator and point it at our test DB
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.session = MagicMock()
        mock_llm.session.summary.return_value = "0 calls"

        orch = Orchestrator(universe_id="sector_etfs")
        orch._engine = engine
        orch._dm = data_manager
        orch._registry = registry
        orch._llm = mock_llm
        orch._evolver = Evolver(
            registry=registry,
            data_manager=data_manager,
            llm_client=mock_llm,
        )

        # Pipeline status
        status = orch.get_pipeline_status()
        print(f"\n{status}")
        assert "PIPELINE" in status

        # Strategy report
        report = orch.get_strategy_report(spec.id)
        print(f"\n{report}")
        assert "LIFECYCLE" in report
        assert "time-series-momentum" in report

        # Evolution report
        evo = orch.get_evolution_report()
        print(f"\n{evo}")
        assert "EVOLUTION" in evo

        print(f"\n{'='*70}")
        print("ORCHESTRATOR REPORTING COMPLETE")
        print(f"{'='*70}")
