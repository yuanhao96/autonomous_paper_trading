"""End-to-end test: full Phase A screening pipeline.

Flow:
  1. Create a StrategySpec + UniverseSpec
  2. Resolve universe → list of symbols
  3. Fetch OHLCV data via DataManager
  4. Translate spec → backtesting.py Strategy
  5. Run screening (backtest + optimize + filter)
  6. Check risk engine constraints
  7. Run auditor checks
  8. Save spec + result to registry
  9. Query registry to verify persistence

Run with:
  pytest tests/integration/test_e2e_screening.py -v -s
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine

from src.core.config import load_preferences
from src.core.db import init_db
from src.data.manager import DataManager
from src.risk.auditor import Auditor
from src.risk.engine import RiskEngine
from src.screening.screener import Screener
from src.strategies.registry import StrategyRegistry
from src.strategies.spec import RiskParams, StrategySpec

# ── Fixtures ─────────────────────────────────────────────────────────


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


@pytest.fixture
def risk_engine():
    return RiskEngine(preferences=load_preferences())


@pytest.fixture
def auditor():
    return Auditor(preferences=load_preferences())


# ── E2E: Static universe + momentum strategy ────────────────────────


class TestE2EStaticMomentum:
    """E2E: Screen a momentum strategy on a small static universe."""

    def test_full_pipeline(self, registry, data_manager, risk_engine, auditor):
        # 1. Create strategy spec
        spec = StrategySpec(
            template="momentum/time-series-momentum",
            parameters={"lookback": 126, "threshold": 0.0},
            universe_id="test_static",
            risk=RiskParams(
                max_position_pct=0.10,
                max_positions=5,
                position_size_method="equal_weight",
            ),
            created_by="human",
        )

        # 2. Define universe (small static list for speed)
        symbols = ["SPY", "QQQ"]

        # 3. Risk check — spec should pass
        violations = risk_engine.check_spec(spec)
        assert len(violations) == 0, f"Risk violations: {violations}"

        # 4. Fetch data (2 years for momentum)
        start = date(2023, 1, 1)
        end = date(2024, 12, 31)
        for sym in symbols:
            df = data_manager.get_ohlcv(sym, start=start, end=end)
            assert not df.empty, f"No data for {sym}"
            print(f"  {sym}: {len(df)} bars ({df.index[0].date()} to {df.index[-1].date()})")

        # 5. Screen the strategy
        screener = Screener(data_manager=data_manager)
        result = screener.screen(
            spec=spec,
            symbols=symbols,
            start=start,
            end=end,
            optimize=False,  # Skip optimization for speed
        )

        # 6. Print diagnostics
        print("\n--- Screening Result ---")
        print(f"  Passed: {result.passed}")
        print(f"  Sharpe: {result.sharpe_ratio:.2f}")
        print(f"  Return: {result.total_return:.2%}")
        print(f"  MaxDD:  {result.max_drawdown:.2%}")
        print(f"  Trades: {result.total_trades}")
        print(f"  PF:     {result.profit_factor:.2f}")
        print(f"  Time:   {result.run_duration_seconds:.1f}s")
        if result.failure_reason:
            print(f"  Failure: {result.failure_reason}")
            print(f"  Details: {result.failure_details}")

        # 7. Verify result has meaningful data
        assert result.spec_id == spec.id
        assert result.phase == "screen"
        assert result.run_duration_seconds > 0

        # 8. Run auditor checks
        audit = auditor.audit(result)
        print("\n--- Audit Report ---")
        print(audit.summary())

        # 9. Save to registry
        registry.save_spec(spec)
        registry.save_result(result)

        # 10. Verify persistence
        loaded_spec = registry.get_spec(spec.id)
        assert loaded_spec is not None
        assert loaded_spec.template == spec.template

        loaded_results = registry.get_results(spec.id, phase="screen")
        assert len(loaded_results) == 1
        assert loaded_results[0].sharpe_ratio == result.sharpe_ratio

        print("\n--- Registry ---")
        print(f"  Spec saved: {loaded_spec.id} ({loaded_spec.name})")
        print(f"  Results: {len(loaded_results)}")


# ── E2E: MA crossover strategy ──────────────────────────────────────


class TestE2EMACrossover:
    """E2E: Screen a moving average crossover strategy."""

    def test_full_pipeline(self, registry, data_manager, risk_engine):
        spec = StrategySpec(
            template="technical/moving-average-crossover",
            parameters={"fast_period": 10, "slow_period": 50},
            universe_id="test_etf",
            risk=RiskParams(max_position_pct=0.10, max_positions=3),
        )

        # Risk check
        assert len(risk_engine.check_spec(spec)) == 0

        # Screen against a single liquid ETF
        symbols = ["SPY"]
        screener = Screener(data_manager=data_manager)
        result = screener.screen(
            spec=spec,
            symbols=symbols,
            start=date(2022, 1, 1),
            end=date(2024, 12, 31),
            optimize=False,
        )

        print("\n--- MA Crossover Result ---")
        print(f"  Passed: {result.passed}")
        print(f"  Sharpe: {result.sharpe_ratio:.2f}")
        print(f"  Trades: {result.total_trades}")
        print(f"  Time:   {result.run_duration_seconds:.1f}s")

        assert result.phase == "screen"
        assert result.run_duration_seconds > 0

        # Persist
        registry.save_spec(spec)
        registry.save_result(result)


# ── E2E: RSI mean reversion ─────────────────────────────────────────


class TestE2ERSIMeanReversion:
    """E2E: Screen an RSI mean reversion strategy."""

    def test_full_pipeline(self, registry, data_manager, risk_engine):
        spec = StrategySpec(
            template="mean-reversion/mean-reversion-rsi",
            parameters={"rsi_period": 14, "oversold": 30, "overbought": 70},
            universe_id="test_etf",
            risk=RiskParams(max_position_pct=0.10, max_positions=3),
        )

        assert len(risk_engine.check_spec(spec)) == 0

        screener = Screener(data_manager=data_manager)
        result = screener.screen(
            spec=spec,
            symbols=["QQQ"],
            start=date(2022, 1, 1),
            end=date(2024, 12, 31),
            optimize=False,
        )

        print("\n--- RSI Mean Reversion Result ---")
        print(f"  Passed: {result.passed}")
        print(f"  Sharpe: {result.sharpe_ratio:.2f}")
        print(f"  Trades: {result.total_trades}")

        assert result.phase == "screen"

        registry.save_spec(spec)
        registry.save_result(result)


# ── E2E: Risk violation → clamp → re-screen ─────────────────────────


class TestE2ERiskClamp:
    """E2E: Verify risk engine clamps an out-of-bounds spec."""

    def test_clamp_and_screen(self, registry, data_manager, risk_engine):
        # Create a spec that violates risk limits
        spec = StrategySpec(
            template="momentum/time-series-momentum",
            parameters={"lookback": 126},
            universe_id="test",
            risk=RiskParams(
                max_position_pct=0.50,  # Exceeds 10% limit
                max_positions=100,       # Exceeds 20 limit
            ),
        )

        # Verify violations detected
        violations = risk_engine.check_spec(spec)
        assert len(violations) > 0
        print("\n--- Risk Violations ---")
        for v in violations:
            print(f"  {v.rule}: {v.message}")

        # Clamp to limits
        clamped = risk_engine.clamp_spec(spec)
        assert clamped.risk.max_position_pct <= 0.10
        assert clamped.risk.max_positions <= 20

        # Verify clamped spec passes
        assert len(risk_engine.check_spec(clamped)) == 0

        # Screen the clamped spec
        screener = Screener(data_manager=data_manager)
        result = screener.screen(
            spec=clamped,
            symbols=["SPY"],
            start=date(2023, 1, 1),
            end=date(2024, 12, 31),
            optimize=False,
        )

        print("\n--- Clamped Strategy Result ---")
        print(f"  Passed: {result.passed}")
        print(f"  Sharpe: {result.sharpe_ratio:.2f}")


# ── E2E: Multiple strategies → rank by Sharpe ───────────────────────


class TestE2ERanking:
    """E2E: Screen multiple strategies and rank by Sharpe ratio."""

    def test_rank_strategies(self, registry, data_manager, risk_engine):
        strategies = [
            StrategySpec(
                template="momentum/time-series-momentum",
                parameters={"lookback": 126, "threshold": 0.0},
                universe_id="test",
                risk=RiskParams(max_position_pct=0.10, max_positions=5),
            ),
            StrategySpec(
                template="technical/moving-average-crossover",
                parameters={"fast_period": 10, "slow_period": 50},
                universe_id="test",
                risk=RiskParams(max_position_pct=0.10, max_positions=5),
            ),
            StrategySpec(
                template="mean-reversion/mean-reversion-rsi",
                parameters={"rsi_period": 14, "oversold": 30, "overbought": 70},
                universe_id="test",
                risk=RiskParams(max_position_pct=0.10, max_positions=5),
            ),
        ]

        screener = Screener(data_manager=data_manager)
        symbols = ["SPY"]

        print("\n--- Strategy Ranking ---")
        for spec in strategies:
            assert len(risk_engine.check_spec(spec)) == 0

            result = screener.screen(
                spec=spec,
                symbols=symbols,
                start=date(2022, 1, 1),
                end=date(2024, 12, 31),
                optimize=False,
            )

            registry.save_spec(spec)
            registry.save_result(result)

            template = spec.template.split("/")[-1]
            print(f"  {template:30s} Sharpe={result.sharpe_ratio:6.2f}  "
                  f"Return={result.total_return:7.2%}  Trades={result.total_trades}")

        # Query best from registry (include non-passing for E2E visibility)
        best = registry.get_best_specs(
            phase="screen", metric="sharpe_ratio", limit=3, passed_only=False
        )
        assert len(best) == 3, f"Expected 3 results, got {len(best)}"
        print("\n  Top strategies by Sharpe:")
        for spec, result in best:
            status = "PASS" if result.passed else "FAIL"
            print(f"    [{status}] {spec.name}: Sharpe={result.sharpe_ratio:.2f}")

        # Verify ranking order (descending Sharpe)
        sharpes = [r.sharpe_ratio for _, r in best]
        assert sharpes == sorted(sharpes, reverse=True), f"Not sorted: {sharpes}"


# ── E2E: Walk-forward analysis ───────────────────────────────────────


class TestE2EWalkForward:
    """E2E: Screen a strategy with walk-forward optimization."""

    def test_walk_forward_momentum(self, registry, data_manager, risk_engine, auditor):
        spec = StrategySpec(
            template="momentum/time-series-momentum",
            parameters={"lookback": 126, "threshold": 0.0},
            universe_id="test_wf",
            risk=RiskParams(max_position_pct=0.10, max_positions=5),
        )

        assert len(risk_engine.check_spec(spec)) == 0

        # Use 3 years of data to ensure enough for walk-forward windows
        screener = Screener(data_manager=data_manager)
        result = screener.screen(
            spec=spec,
            symbols=["SPY"],
            start=date(2022, 1, 1),
            end=date(2024, 12, 31),
            optimize=True,
        )

        print("\n--- Walk-Forward Result ---")
        print(f"  Passed: {result.passed}")
        print(f"  OOS Sharpe: {result.sharpe_ratio:.2f}")
        print(f"  IS Sharpe:  {result.in_sample_sharpe:.2f}")
        print(f"  Return:     {result.total_return:.2%}")
        print(f"  MaxDD:      {result.max_drawdown:.2%}")
        print(f"  Trades:     {result.total_trades}")
        print(f"  Optimized:  {result.optimized_parameters}")
        print(f"  Time:       {result.run_duration_seconds:.1f}s")

        assert result.phase == "screen"
        assert result.run_duration_seconds > 0

        # Run audit — should include walk-forward gap check
        audit = auditor.audit(result)
        print("\n--- Audit Report ---")
        print(audit.summary())

        # If walk-forward ran, in_sample_sharpe should be populated
        if result.in_sample_sharpe > 0:
            wf_checks = [c for c in audit.checks if c.name == "walk_forward_gap"]
            assert len(wf_checks) == 1
            print(f"  WF Gap: {wf_checks[0].message}")

        registry.save_spec(spec)
        registry.save_result(result)
