"""End-to-end test: full screen → validate pipeline.

Flow:
  1. Create a StrategySpec
  2. Screen it (Phase 1)
  3. Validate it across market regimes (Phase 2)
  4. Run audit checks
  5. Save everything to registry
  6. Print rich diagnostics

Run with:
  pytest tests/integration/test_e2e_validation.py -v -s
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
from src.validation.validator import Validator


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


class TestE2EScreenToValidate:
    """E2E: Screen a strategy, then validate across market regimes."""

    def test_full_pipeline(self, registry, data_manager, risk_engine, auditor):
        # 1. Create strategy spec
        spec = StrategySpec(
            template="momentum/time-series-momentum",
            parameters={"lookback": 126, "threshold": 0.0},
            universe_id="test_static",
            risk=RiskParams(max_position_pct=0.10, max_positions=5),
            created_by="human",
        )

        symbols = ["SPY", "QQQ"]

        # 2. Risk check
        violations = risk_engine.check_spec(spec)
        assert len(violations) == 0

        # 3. Phase 1: Screen
        screener = Screener(data_manager=data_manager)
        screen_result = screener.screen(
            spec=spec,
            symbols=symbols,
            start=date(2020, 1, 1),
            end=date(2024, 12, 31),
            optimize=False,
        )

        print(f"\n{'='*60}")
        print(f"PHASE 1: SCREENING")
        print(f"{'='*60}")
        print(f"  Strategy: {spec.template} ({spec.name})")
        print(f"  Symbols:  {symbols}")
        print(f"  Sharpe:   {screen_result.sharpe_ratio:.2f}")
        print(f"  Return:   {screen_result.total_return:.2%}")
        print(f"  MaxDD:    {screen_result.max_drawdown:.2%}")
        print(f"  Trades:   {screen_result.total_trades}")
        print(f"  Passed:   {screen_result.passed}")
        if screen_result.failure_reason:
            print(f"  Failure:  {screen_result.failure_reason}")

        # 4. Phase 2: Validate across regimes
        validator = Validator(data_manager=data_manager)
        val_result = validator.validate(
            spec=spec,
            symbols=symbols,
            benchmark="SPY",
        )

        print(f"\n{'='*60}")
        print(f"PHASE 2: VALIDATION")
        print(f"{'='*60}")
        print(f"  Sharpe:   {val_result.sharpe_ratio:.2f}")
        print(f"  Return:   {val_result.total_return:.2%}")
        print(f"  MaxDD:    {val_result.max_drawdown:.2%}")
        print(f"  Trades:   {val_result.total_trades}")
        print(f"  Fees:     {val_result.total_fees:.4f}")
        print(f"  Slippage: {val_result.total_slippage:.4f}")
        print(f"  Passed:   {val_result.passed}")
        if val_result.failure_reason:
            print(f"  Failure:  {val_result.failure_reason}")

        # 5. Regime breakdown
        if val_result.regime_results:
            print(f"\n  Regime Breakdown:")
            for rr in val_result.regime_results:
                status = "+" if rr.annual_return > 0 else "-"
                print(
                    f"    [{status}] {rr.regime:10s} "
                    f"Return={rr.annual_return:7.2%}  "
                    f"Sharpe={rr.sharpe_ratio:5.2f}  "
                    f"MaxDD={rr.max_drawdown:7.2%}  "
                    f"Trades={rr.total_trades}"
                )

        # 6. Audit
        audit = auditor.audit(screen_result, val_result)
        print(f"\n{'='*60}")
        print(f"AUDIT GATE")
        print(f"{'='*60}")
        print(audit.summary())

        # 7. Sharpe degradation check
        if screen_result.sharpe_ratio > 0:
            degradation = screen_result.sharpe_ratio - val_result.sharpe_ratio
            pct = degradation / screen_result.sharpe_ratio * 100
            print(f"\n  Sharpe Degradation: {degradation:.2f} ({pct:.0f}%)")

        # 8. Save to registry
        registry.save_spec(spec)
        registry.save_result(screen_result)
        registry.save_result(val_result)

        # 9. Verify persistence
        loaded = registry.get_spec(spec.id)
        assert loaded is not None

        all_results = registry.get_results(spec.id)
        assert len(all_results) == 2  # screen + validate

        screen_results = registry.get_results(spec.id, phase="screen")
        assert len(screen_results) == 1

        validate_results = registry.get_results(spec.id, phase="validate")
        assert len(validate_results) == 1

        # 10. Verify result integrity
        assert val_result.phase == "validate"
        assert val_result.run_duration_seconds > 0

        print(f"\n{'='*60}")
        print(f"REGISTRY: {len(all_results)} results saved for {spec.name}")
        print(f"{'='*60}")


class TestE2EMultiStrategyValidation:
    """E2E: Screen + validate multiple strategies, compare results."""

    def test_compare_strategies(self, registry, data_manager, risk_engine):
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
        ]

        symbols = ["SPY"]
        screener = Screener(data_manager=data_manager)
        validator = Validator(data_manager=data_manager)

        print(f"\n{'='*60}")
        print(f"MULTI-STRATEGY COMPARISON")
        print(f"{'='*60}")
        print(
            f"{'Strategy':30s} {'Scr.Sharpe':>10s} {'Val.Sharpe':>10s} "
            f"{'Degradation':>12s} {'Regimes+':>9s}"
        )
        print("-" * 75)

        for spec in strategies:
            # Screen
            screen = screener.screen(
                spec=spec, symbols=symbols,
                start=date(2020, 1, 1), end=date(2024, 12, 31),
                optimize=False,
            )
            # Validate
            val = validator.validate(spec=spec, symbols=symbols)

            registry.save_spec(spec)
            registry.save_result(screen)
            registry.save_result(val)

            positive_regimes = sum(1 for r in val.regime_results if r.annual_return > 0)
            degradation = screen.sharpe_ratio - val.sharpe_ratio

            template = spec.template.split("/")[-1]
            print(
                f"{template:30s} {screen.sharpe_ratio:10.2f} {val.sharpe_ratio:10.2f} "
                f"{degradation:12.2f} {positive_regimes:9d}"
            )

        # Verify all stored
        all_specs = registry.list_specs()
        assert len(all_specs) == 2
