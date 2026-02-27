"""End-to-end test: full live trading pipeline with PaperBroker.

Flow:
  1. Mock LLM generates strategy spec
  2. Screen spec via backtesting.py (real data)
  3. Validate top candidate (real regime detection)
  4. Run audit checks
  5. Pre-deployment validation
  6. Deploy to PaperBroker (simulated paper trading)
  7. Rebalance positions (compute signals from real data)
  8. Monitor live performance vs validation baseline
  9. Evaluate promotion readiness
  10. Print rich diagnostics

Run with:
  pytest tests/integration/test_e2e_live_trading.py -v -s
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pandas as pd
import pytest
from sqlalchemy import create_engine

from src.agent.evolver import Evolver
from src.agent.reviewer import format_result_for_llm
from src.core.db import init_db
from src.core.llm import LLMClient
from src.live.broker import PaperBroker
from src.live.deployer import Deployer
from src.live.models import Deployment, LiveSnapshot, Position
from src.live.monitor import Monitor
from src.live.promoter import Promoter
from src.live.signals import compute_signals, compute_target_weights
from src.risk.auditor import Auditor
from src.risk.engine import RiskEngine
from src.strategies.registry import StrategyRegistry
from src.strategies.spec import RiskParams, StrategyResult, StrategySpec


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
def engine(tmp_dir):
    eng = create_engine(f"sqlite:///{tmp_dir / 'test.db'}", echo=False)
    init_db(eng)
    return eng


@pytest.fixture
def registry(engine):
    return StrategyRegistry(engine=engine)


class TestE2ELiveTrading:
    """E2E: Full pipeline from LLM generation → screen → validate → deploy → monitor → promote."""

    def test_full_pipeline_paper_trading(self, engine, registry, data_manager):
        """Complete lifecycle: generate → screen → validate → deploy → monitor → promote."""

        print(f"\n{'='*70}")
        print("PHASE D E2E: FULL LIVE TRADING PIPELINE")
        print(f"{'='*70}")

        # ── Step 1: Generate strategy via mocked LLM ─────────────────
        print("\n[1/8] Generating strategy spec via mocked LLM...")

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.session = MagicMock()
        mock_llm.session.summary.return_value = "1 call"
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

        cycle_result = evolver.run_cycle(symbols=["SPY", "QQQ"])
        print(f"  Evolution cycle: {cycle_result.specs_generated} generated, "
              f"{cycle_result.specs_screened} screened")
        print(cycle_result.summary())

        assert cycle_result.specs_generated >= 1

        # Get the screened spec and its results
        all_specs = registry.list_specs()
        assert len(all_specs) >= 1
        spec = all_specs[0]
        results = registry.get_results(spec.id)
        screen_result = next((r for r in results if r.phase == "screen"), None)
        assert screen_result is not None

        print(f"\n  Strategy: {spec.template}")
        print(f"  Params:   {spec.parameters}")
        print(f"  Screen:   Sharpe={screen_result.sharpe_ratio:.2f}, "
              f"Return={screen_result.annual_return:.1%}, "
              f"MaxDD={screen_result.max_drawdown:.1%}, "
              f"Trades={screen_result.total_trades}")

        # ── Step 2: Get validation result (if available) ─────────────
        print("\n[2/8] Checking validation results...")

        validation_result = next((r for r in results if r.phase == "validate"), None)
        if validation_result:
            print(f"  Validation: Sharpe={validation_result.sharpe_ratio:.2f}, "
                  f"Return={validation_result.annual_return:.1%}")
        else:
            print("  No validation result (using screen result as baseline)")
            validation_result = screen_result

        # ── Step 3: Pre-deployment validation ─────────────────────────
        print("\n[3/8] Running pre-deployment validation...")

        paper_broker = PaperBroker(initial_cash=100_000, commission_rate=0.002)
        paper_broker.connect()

        deployer = Deployer(broker=paper_broker, engine=engine)
        checks = deployer.validate_readiness(spec, screen_result, validation_result)

        for check in checks:
            status = "[OK]" if check.passed else "[FAIL]"
            print(f"  {status} {check.name}: {check.message}")

        all_passed = all(c.passed for c in checks)
        print(f"\n  Pre-deployment: {'ALL PASSED' if all_passed else 'SOME FAILED'}")

        # ── Step 4: Deploy to paper trading ───────────────────────────
        print("\n[4/8] Deploying to paper trading...")

        symbols = ["SPY", "QQQ"]
        deployment = deployer.deploy(spec, symbols=symbols, mode="paper")

        print(f"  Deployment ID: {deployment.id}")
        print(f"  Mode: {deployment.mode}")
        print(f"  Status: {deployment.status}")
        print(f"  Symbols: {deployment.symbols}")
        print(f"  Initial cash: ${deployment.initial_cash:,.0f}")

        assert deployment.is_active

        # ── Step 5: Fetch real market data and compute signals ────────
        print("\n[5/8] Computing signals from real market data...")

        prices: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            df = data_manager.get_ohlcv(symbol, period="2y")
            prices[symbol] = df
            print(f"  {symbol}: {len(df)} bars, "
                  f"{df.index[0].strftime('%Y-%m-%d')} → {df.index[-1].strftime('%Y-%m-%d')}")

        signals = compute_signals(spec, prices)
        target_weights = compute_target_weights(spec, signals)
        print(f"\n  Signals: {signals}")
        print(f"  Target weights: {target_weights}")

        # Set current prices in broker for order execution
        current_prices = {s: float(df["Close"].iloc[-1]) for s, df in prices.items()}
        paper_broker.set_prices(current_prices)
        print(f"  Current prices: {current_prices}")

        # ── Step 6: Rebalance positions ───────────────────────────────
        print("\n[6/8] Executing rebalance...")

        trades = deployer.rebalance(deployment, spec, prices)
        print(f"  Trades executed: {len(trades)}")
        for t in trades:
            print(f"    {t.side.upper()} {t.quantity} {t.symbol} @ ${t.price:.2f} "
                  f"(commission: ${t.commission:.2f})")

        # Check positions after rebalance
        positions = paper_broker.get_positions()
        account = paper_broker.get_account_summary()
        print(f"\n  Account after rebalance:")
        print(f"    Equity: ${account['equity']:,.2f}")
        print(f"    Cash: ${account['cash']:,.2f}")
        print(f"    Positions: {len(positions)}")
        for p in positions:
            print(f"      {p.symbol}: {p.quantity} shares @ ${p.avg_cost:.2f} "
                  f"(value: ${p.market_value:,.2f})")

        # ── Step 7: Simulate multi-day monitoring ─────────────────────
        print("\n[7/8] Simulating multi-day paper trading monitoring...")

        # Simulate 5 days of "trading" by adding snapshots with slight variations
        import random
        random.seed(42)

        base_equity = account["equity"]
        for day in range(5):
            # Simulate daily P&L variation
            daily_return = random.gauss(0.0003, 0.008)  # Slight positive drift + noise
            base_equity *= (1 + daily_return)

            snapshot = LiveSnapshot(
                deployment_id=deployment.id,
                timestamp=datetime.utcnow() - timedelta(days=4 - day),
                equity=base_equity,
                cash=base_equity * 0.3,
                positions=[
                    Position(s, p.quantity, p.avg_cost,
                             p.quantity * current_prices.get(s, p.avg_cost) * (1 + daily_return),
                             0)
                    for s, p in [(pos.symbol, pos) for pos in positions]
                ] if positions else [],
            )
            deployment.snapshots.append(snapshot)
            print(f"  Day {day+1}: equity=${snapshot.equity:,.2f} "
                  f"(daily={daily_return:+.2%})")

        # Backdate deployment start for realistic days_elapsed
        deployment.started_at = datetime.utcnow() - timedelta(days=25)

        # ── Step 8: Monitor and evaluate promotion ────────────────────
        print("\n[8/8] Running monitoring and promotion evaluation...")

        monitor = Monitor()

        # Compare live to validation baseline
        comparison = monitor.compare(deployment, validation_result)
        print(f"\n  Comparison Report:")
        print(f"  {comparison.summary()}")

        # Check risk violations
        violations = monitor.check_risk(deployment)
        print(f"\n  Risk violations: {len(violations)}")
        for v in violations:
            print(f"    [{v.rule}] {v.message}")

        # Compile live result
        live_result = monitor.compute_live_result(deployment, spec.id)
        print(f"\n  Live Result:")
        print(f"    Return: {live_result.total_return:+.2%}")
        print(f"    Sharpe: {live_result.sharpe_ratio:.2f}")
        print(f"    MaxDD:  {live_result.max_drawdown:.2%}")
        print(f"    Trades: {live_result.total_trades}")
        print(f"    Passed: {live_result.passed}")

        # Save live result to registry
        registry.save_result(live_result)

        # Evaluate promotion
        promoter = Promoter(monitor=monitor)
        promo_summary = promoter.get_promotion_summary(deployment, validation_result)
        print(f"\n{promo_summary}")

        # ── Final diagnostics ─────────────────────────────────────────
        print(f"\n{'='*70}")
        print("STRATEGY LIFECYCLE DIAGNOSTICS")
        print(f"{'='*70}")

        # All phases for this strategy
        all_results = registry.get_results(spec.id)
        phases = [r.phase for r in all_results]
        print(f"\n  Strategy: {spec.template} (id={spec.id})")
        print(f"  Phases completed: {phases}")

        for r in all_results:
            print(f"\n  [{r.phase.upper()}] {'PASSED' if r.passed else 'FAILED'}")
            print(f"    Sharpe={r.sharpe_ratio:.2f}, Return={r.annual_return:.1%}, "
                  f"MaxDD={r.max_drawdown:.1%}, Trades={r.total_trades}")
            if r.failure_reason:
                print(f"    Failure: {r.failure_reason}")

        # Verify the full pipeline completed
        assert "screen" in phases
        assert "live" in phases
        assert deployment.is_active
        assert len(deployment.snapshots) >= 5

        # Stop deployment
        deployer.stop(deployment)
        assert deployment.status == "stopped"
        print(f"\n  Deployment stopped. Final status: {deployment.status}")

        print(f"\n{'='*70}")
        print("E2E PHASE D COMPLETE")
        print(f"{'='*70}")

    def test_signal_computation_real_data(self, data_manager):
        """Test signal computation with real market data for multiple templates."""

        print(f"\n{'='*70}")
        print("SIGNAL COMPUTATION WITH REAL DATA")
        print(f"{'='*70}")

        # Fetch real data
        symbols = ["SPY", "QQQ"]
        prices: dict[str, pd.DataFrame] = {}
        for s in symbols:
            prices[s] = data_manager.get_ohlcv(s, period="2y")

        templates_and_params = [
            ("momentum/time-series-momentum", {"lookback": 126, "threshold": 0.0}),
            ("momentum/time-series-momentum", {"lookback": 252, "threshold": 0.02}),
            ("technical/moving-average-crossover", {"fast_period": 10, "slow_period": 50}),
            ("technical/moving-average-crossover", {"fast_period": 50, "slow_period": 200}),
            ("mean-reversion/mean-reversion-rsi", {"rsi_period": 14, "oversold": 30, "overbought": 70}),
            ("mean-reversion/mean-reversion-bollinger", {"bb_period": 20, "bb_std": 2.0}),
            ("technical/breakout", {"lookback": 20}),
            ("technical/trend-following", {"fast_period": 20, "slow_period": 100}),
        ]

        for template, params in templates_and_params:
            spec = StrategySpec(
                template=template,
                parameters=params,
                universe_id="test",
                risk=RiskParams(max_position_pct=0.10, max_positions=5),
            )
            signals = compute_signals(spec, prices)
            weights = compute_target_weights(spec, signals)

            template_name = template.split("/")[-1]
            print(f"\n  {template_name:30s} params={params}")
            for s in symbols:
                print(f"    {s}: signal={signals[s]:5s}  weight={weights[s]:.2f}")

        # Just verify no crashes — signals are market-dependent
        assert True

    def test_paper_broker_rebalance_cycle(self, engine, data_manager):
        """Test multiple rebalance cycles with real data through PaperBroker."""

        print(f"\n{'='*70}")
        print("MULTI-CYCLE REBALANCE TEST")
        print(f"{'='*70}")

        spec = StrategySpec(
            template="momentum/time-series-momentum",
            parameters={"lookback": 126, "threshold": 0.0},
            universe_id="sp500",
            risk=RiskParams(max_position_pct=0.10, max_positions=5),
        )

        symbols = ["SPY", "QQQ"]
        prices: dict[str, pd.DataFrame] = {}
        for s in symbols:
            prices[s] = data_manager.get_ohlcv(s, period="2y")

        # Set up broker with current prices
        current_prices = {s: float(df["Close"].iloc[-1]) for s, df in prices.items()}
        paper_broker = PaperBroker(initial_cash=100_000, commission_rate=0.002)
        paper_broker.connect()
        paper_broker.set_prices(current_prices)

        deployer = Deployer(broker=paper_broker, engine=engine)
        deployment = deployer.deploy(spec, symbols=symbols)

        print(f"\n  Initial: ${paper_broker.get_account_summary()['equity']:,.2f}")

        # Run 3 rebalance cycles
        for cycle in range(3):
            trades = deployer.rebalance(deployment, spec, prices)
            account = paper_broker.get_account_summary()
            positions = paper_broker.get_positions()
            print(f"\n  Cycle {cycle+1}:")
            print(f"    Trades: {len(trades)}")
            print(f"    Equity: ${account['equity']:,.2f}")
            print(f"    Cash: ${account['cash']:,.2f}")
            print(f"    Positions: {len(positions)}")
            for p in positions:
                print(f"      {p.symbol}: {p.quantity} shares")

        # Verify deployment tracking
        assert len(deployment.snapshots) == 3
        assert deployment.is_active

        # Check persisted deployment
        loaded = deployer.get_deployment(deployment.id)
        assert loaded is not None
        assert loaded.status == "active"

        # List all deployments
        all_deps = deployer.list_deployments()
        print(f"\n  Total deployments in DB: {len(all_deps)}")

        print(f"\n{'='*70}")
        print("MULTI-CYCLE REBALANCE COMPLETE")
        print(f"{'='*70}")
