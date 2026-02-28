"""Main orchestrator — ties together the full autonomous trading pipeline.

Pipeline:
  1. Equity screening: Select trading targets via computed universes
  2. Strategy generation: LLM picks from 87 templates, sets parameters
  3. Phase 1 screening: Fast backtest via backtesting.py
  4. Phase 2 validation: Multi-regime walkforward
  5. Audit gate: Risk + consistency checks
  6. Deployment: Paper/live trading via IBKR
  7. Monitoring: Track live performance vs backtest expectations
  8. Promotion: Evaluate paper → live readiness

Usage:
    from src.orchestrator import Orchestrator
    orch = Orchestrator()
    orch.run_full_cycle()
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd

from src.agent.evolver import CycleResult, Evolver
from src.core.config import Settings, load_preferences
from src.core.db import get_engine, init_db
from src.core.llm import LLMClient
from src.data.manager import DataManager
from src.live.broker import IBKRBroker, PaperBroker
from src.live.deployer import Deployer
from src.live.models import Deployment
from src.live.monitor import Monitor
from src.live.promoter import Promoter
from src.reporting.reporter import (
    evolution_summary_report,
    format_deployment,
    format_result,
    format_spec,
    pipeline_status_report,
    strategy_lifecycle_report,
)
from src.strategies.registry import StrategyRegistry
from src.strategies.spec import StrategyResult, StrategySpec
from src.universe.computed import compute_universe, get_available_computations
from src.universe.static import STATIC_UNIVERSES, get_static_universe

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of a full pipeline run."""

    specs_generated: int = 0
    specs_screened: int = 0
    specs_validated: int = 0
    specs_passed: int = 0
    specs_deployed: int = 0
    best_sharpe: float = 0.0
    best_spec_id: str = ""
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    cycle_results: list[CycleResult] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Pipeline: {self.specs_generated} generated → "
            f"{self.specs_screened} screened → {self.specs_validated} validated → "
            f"{self.specs_passed} passed → {self.specs_deployed} deployed",
        ]
        if self.best_sharpe > 0:
            lines.append(f"  Best Sharpe: {self.best_sharpe:.2f} (spec {self.best_spec_id})")
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
        lines.append(f"  Duration: {self.duration_seconds:.1f}s")
        return "\n".join(lines)


class Orchestrator:
    """Main pipeline orchestrator.

    Coordinates all components: evolution, screening, validation, deployment,
    monitoring, and promotion.

    Args:
        settings: Runtime settings (from settings.yaml).
        universe_id: Default universe for equity screening.
        symbols: Override symbols list (skips universe resolution).
        mode: Trading mode — "paper" or "live".
    """

    def __init__(
        self,
        settings: Settings | None = None,
        universe_id: str = "sector_etfs",
        symbols: list[str] | None = None,
        mode: str = "paper",
    ) -> None:
        self._settings = settings or Settings()
        self._prefs = load_preferences()
        self._universe_id = universe_id
        self._override_symbols = symbols
        self._mode = mode

        # Core components
        self._dm = DataManager(cache_dir=self._settings.cache_dir)
        self._engine = get_engine()
        init_db(self._engine)
        self._registry = StrategyRegistry(engine=self._engine)
        self._llm = LLMClient(settings=self._settings)

        # Pipeline stages
        self._evolver = Evolver(
            registry=self._registry,
            data_manager=self._dm,
            llm_client=self._llm,
            settings=self._settings,
        )
        self._monitor = Monitor()
        self._promoter = Promoter(monitor=self._monitor)

        # State — load persisted active deployments from DB
        self._deployer = Deployer(engine=self._engine, settings=self._settings)
        self._deployments: list[Deployment] = self._deployer.list_deployments(status="active")

    @property
    def registry(self) -> StrategyRegistry:
        return self._registry

    @property
    def evolver(self) -> Evolver:
        return self._evolver

    # ── Universe resolution ──────────────────────────────────────────

    def resolve_symbols(
        self,
        universe_id: str | None = None,
        computation: str | None = None,
        computation_params: dict[str, Any] | None = None,
    ) -> list[str]:
        """Resolve a universe to a concrete list of symbols.

        Three resolution paths:
        1. Override symbols (provided at init)
        2. Computed universe (dynamic equity screening)
        3. Static universe (fixed list)
        """
        if self._override_symbols:
            return self._override_symbols

        uid = universe_id or self._universe_id

        # Try computed universe — use the selected universe as base pool
        if computation:
            base_uid = uid if uid in STATIC_UNIVERSES else "sp500"
            base_pool = get_static_universe(base_uid)
            return compute_universe(
                name=computation,
                base_symbols=base_pool,
                data_manager=self._dm,
                params=computation_params or {},
            )

        # Try static universe
        if uid in STATIC_UNIVERSES:
            return get_static_universe(uid)

        logger.warning("Unknown universe %s, using sector_etfs", uid)
        return get_static_universe("sector_etfs")

    # ── Full pipeline ────────────────────────────────────────────────

    def run_full_cycle(
        self,
        n_evolution_cycles: int = 1,
        deploy_best: bool = True,
        universe_id: str | None = None,
        computation: str | None = None,
        computation_params: dict[str, Any] | None = None,
    ) -> PipelineResult:
        """Run the full pipeline: evolve → screen → validate → deploy → monitor.

        Args:
            n_evolution_cycles: Number of evolution cycles to run.
            deploy_best: Whether to deploy the best passing strategy.
            universe_id: Override universe ID.
            computation: Computed universe builder name.
            computation_params: Parameters for computed universe builder.

        Returns:
            PipelineResult with comprehensive diagnostics.
        """
        t0 = time.time()
        result = PipelineResult()

        # Only pass explicit symbol overrides to evolver; otherwise let each
        # spec resolve its own universe_id inside evolver._resolve_symbols().
        explicit_symbols = None
        if self._override_symbols or computation:
            explicit_symbols = self.resolve_symbols(
                universe_id, computation, computation_params,
            )
            if not explicit_symbols:
                result.errors.append("No symbols resolved from universe")
                return result

        # Resolve symbols for logging even when not overriding
        log_symbols = explicit_symbols or self.resolve_symbols(universe_id)
        if not log_symbols:
            result.errors.append("No symbols resolved from universe")
            return result

        logger.info(
            "Pipeline starting: %d symbols from %s, mode=%s",
            len(log_symbols), universe_id or self._universe_id, self._mode,
        )

        # ── Phase 1-3: Evolution cycles (generate → screen → validate) ──
        cycle_results = self._evolver.run_cycles(
            n_evolution_cycles, symbols=explicit_symbols,
        )
        result.cycle_results = cycle_results

        for cr in cycle_results:
            result.specs_generated += cr.specs_generated
            result.specs_screened += cr.specs_screened
            result.specs_validated += cr.specs_validated
            result.specs_passed += cr.specs_passed
            result.errors.extend(cr.errors)
            if cr.best_sharpe > result.best_sharpe:
                result.best_sharpe = cr.best_sharpe
                result.best_spec_id = cr.best_spec_id

        # ── Phase 4: Deploy best strategy ────────────────────────────
        if deploy_best and result.best_spec_id:
            try:
                deploy_syms = explicit_symbols or self._resolve_deploy_symbols(
                    result.best_spec_id,
                )
                deployment = self._deploy_best(result.best_spec_id, deploy_syms)
                if deployment:
                    result.specs_deployed += 1
            except Exception as e:
                logger.warning("Deployment failed: %s", e)
                result.errors.append(f"Deploy: {e}")

        result.duration_seconds = time.time() - t0
        logger.info(result.summary())
        return result

    def run_evolution(
        self,
        n_cycles: int = 1,
        symbols: list[str] | None = None,
    ) -> list[CycleResult]:
        """Run evolution cycles only (no deployment)."""
        syms = symbols or self.resolve_symbols()
        return self._evolver.run_cycles(n_cycles, symbols=syms)

    def _resolve_deploy_symbols(self, spec_id: str) -> list[str]:
        """Resolve symbols from a spec's universe_id for deployment."""
        spec = self._registry.get_spec(spec_id)
        if spec is not None and spec.universe_id:
            return self.resolve_symbols(universe_id=spec.universe_id)
        return self.resolve_symbols()

    # ── Deployment ───────────────────────────────────────────────────

    def deploy_strategy(
        self,
        spec_id: str,
        symbols: list[str] | None = None,
        mode: str | None = None,
    ) -> Deployment | None:
        """Deploy a strategy by spec ID."""
        syms = symbols or self._resolve_deploy_symbols(spec_id)
        return self._deploy_best(spec_id, syms, mode=mode or self._mode)

    def _deploy_best(
        self,
        spec_id: str,
        symbols: list[str],
        mode: str | None = None,
    ) -> Deployment | None:
        """Deploy the best strategy from the registry.

        Runs validate_readiness() before deploying. Refuses to deploy
        if any pre-deployment check fails.
        """
        spec = self._registry.get_spec(spec_id)
        if spec is None:
            logger.warning("Spec %s not found in registry", spec_id)
            return None

        # Pre-deployment safety gate: require passing readiness checks
        deploy_mode = mode or self._mode
        deployer = Deployer(engine=self._engine, settings=self._settings)

        results = self._registry.get_results(spec_id)
        screen_result = next((r for r in results if r.phase == "screen"), None)
        val_result = next((r for r in results if r.phase == "validate"), None)
        if screen_result is None:
            logger.warning("Spec %s has no screen result, refusing to deploy", spec_id)
            return None
        if val_result is None:
            logger.warning("Spec %s has no validation result, refusing to deploy", spec_id)
            return None

        checks = deployer.validate_readiness(spec, screen_result, val_result)
        failed = [c for c in checks if not c.passed]
        if failed:
            names = [c.name for c in failed]
            logger.warning(
                "Spec %s failed pre-deployment checks %s, refusing to deploy",
                spec_id, names,
            )
            return None

        # Set up broker based on mode
        if deploy_mode == "paper":
            initial_cash = self._settings.get("live.initial_cash", 100_000)
            broker = PaperBroker(initial_cash=initial_cash)
            broker.connect()
        elif deploy_mode == "ibkr_paper":
            host = self._settings.get("live.ibkr_host", "127.0.0.1")
            port = self._settings.get("live.ibkr_paper_port", 7497)
            client_id = self._settings.get("live.ibkr_client_id", 1)
            broker = IBKRBroker(host=host, port=port, client_id=client_id)
            broker.connect()
        else:  # "live"
            host = self._settings.get("live.ibkr_host", "127.0.0.1")
            port = self._settings.get("live.ibkr_live_port", 7496)
            client_id = self._settings.get("live.ibkr_client_id", 1)
            broker = IBKRBroker(host=host, port=port, client_id=client_id)
            broker.connect()

        deployer._brokers[deploy_mode] = broker
        deployment = deployer.deploy(spec, symbols=symbols, mode=deploy_mode)
        self._deployments.append(deployment)

        # Fetch prices and do initial rebalance
        prices = self._dm.get_bulk_ohlcv(symbols, period="2y")
        if prices:
            # Set current prices for PaperBroker
            if isinstance(broker, PaperBroker):
                current_prices = {
                    s: float(df["Close"].iloc[-1])
                    for s, df in prices.items()
                }
                broker.set_prices(current_prices)

            trades = deployer.rebalance(deployment, spec, prices)
            logger.info(
                "Initial rebalance: %d trades for deployment %s",
                len(trades), deployment.id,
            )

        return deployment

    # ── Monitoring ───────────────────────────────────────────────────

    def monitor_deployment(
        self,
        deployment: Deployment,
        validation_result: StrategyResult | None = None,
    ) -> dict[str, Any]:
        """Monitor a deployment: compare live vs validation, check risk."""
        report: dict[str, Any] = {"deployment_id": deployment.id}

        if validation_result:
            comparison = self._monitor.compare(deployment, validation_result)
            report["comparison"] = comparison
            report["within_tolerance"] = comparison.within_tolerance

        violations = self._monitor.check_risk(deployment)
        report["risk_violations"] = violations
        report["risk_ok"] = len(violations) == 0

        return report

    def evaluate_promotion(
        self,
        deployment: Deployment,
        validation_result: StrategyResult,
    ) -> str:
        """Evaluate whether a deployment should be promoted to live."""
        return self._promoter.get_promotion_summary(deployment, validation_result)

    def run_monitoring(self) -> list[dict[str, Any]]:
        """Monitor all active deployments: check risk, compare vs validation.

        Reloads active deployments from DB so restarts don't lose state.
        Returns a list of monitoring reports, one per active deployment.
        """
        # Reload from DB to survive restarts
        self._deployments = self._deployer.list_deployments(status="active")
        reports: list[dict[str, Any]] = []

        for deployment in self._deployments:
            # Fetch the latest validation result for comparison
            val_results = self._registry.get_results(deployment.spec_id, phase="validate")
            val_result = val_results[0] if val_results else None

            report = self.monitor_deployment(deployment, val_result)

            # Auto-stop on risk violations
            violations = report.get("risk_violations", [])
            if violations:
                logger.warning(
                    "Deployment %s has %d risk violations: %s",
                    deployment.id, len(violations),
                    [v.message for v in violations],
                )
                logger.warning(
                    "Auto-stopping deployment %s due to risk violations",
                    deployment.id,
                )
                try:
                    self._deployer.stop(deployment)
                except Exception as e:
                    logger.error(
                        "Failed to auto-stop deployment %s: %s",
                        deployment.id, e,
                    )
                report["auto_stopped"] = True

            if not report.get("within_tolerance", True) and val_result:
                logger.warning(
                    "Deployment %s live performance diverges from validation",
                    deployment.id,
                )

            reports.append(report)

        logger.info("Monitoring complete: %d active deployments checked", len(reports))
        return reports

    def run_rebalance(self) -> list[dict[str, Any]]:
        """Rebalance all active deployments.

        Reloads active deployments from DB, fetches latest prices,
        and rebalances each.
        """
        self._deployments = self._deployer.list_deployments(
            status="active",
        )
        results: list[dict[str, Any]] = []

        for deployment in self._deployments:
            try:
                spec = self._registry.get_spec(deployment.spec_id)
                if spec is None:
                    logger.warning(
                        "Spec %s not found for deployment %s",
                        deployment.spec_id, deployment.id,
                    )
                    continue

                prices = self._dm.get_bulk_ohlcv(
                    deployment.symbols, period="2y",
                )
                if not prices:
                    logger.warning(
                        "No price data for deployment %s",
                        deployment.id,
                    )
                    continue

                # Ensure broker exists (may be None after restart),
                # then rehydrate PaperBroker from last snapshot
                broker = self._deployer._get_broker(deployment.mode)
                if not broker.is_connected():
                    broker.connect()
                if isinstance(broker, PaperBroker) and deployment.snapshots:
                    latest = deployment.snapshots[-1]
                    broker.rehydrate(
                        cash=latest.cash, positions=latest.positions,
                    )

                trades = self._deployer.rebalance(
                    deployment, spec, prices,
                )
                results.append({
                    "deployment_id": deployment.id,
                    "trades": len(trades),
                    "status": "ok",
                })
                logger.info(
                    "Rebalanced deployment %s: %d trades",
                    deployment.id, len(trades),
                )
            except Exception as e:
                logger.warning(
                    "Rebalance failed for deployment %s: %s",
                    deployment.id, e,
                )
                results.append({
                    "deployment_id": deployment.id,
                    "trades": 0,
                    "status": f"error: {e}",
                })

        logger.info(
            "Rebalance complete: %d deployments processed",
            len(results),
        )
        return results

    # ── Reporting ────────────────────────────────────────────────────

    def get_pipeline_status(self) -> str:
        """Get a summary of the full pipeline."""
        total_specs = len(self._registry.list_specs())
        phases: dict[str, int] = {"screened": 0, "validated": 0, "passed": 0}

        for spec in self._registry.list_specs():
            results = self._registry.get_results(spec.id)
            for r in results:
                if r.phase == "screen":
                    phases["screened"] += 1
                elif r.phase == "validate":
                    phases["validated"] += 1
                if r.passed:
                    phases["passed"] += 1

        # Reload from DB for accurate count
        db_deployments = self._deployer.list_deployments(status="active")
        active_deps = len(db_deployments)
        best = self._registry.get_best_specs(
            phase="validate", metric="sharpe_ratio", limit=1, passed_only=True,
        )
        best_sharpe = best[0][1].sharpe_ratio if best else 0.0

        return pipeline_status_report(total_specs, phases, active_deps, best_sharpe)

    def get_strategy_report(self, spec_id: str) -> str:
        """Get a full lifecycle report for a single strategy."""
        spec = self._registry.get_spec(spec_id)
        if spec is None:
            return f"Strategy {spec_id} not found."

        results = self._registry.get_results(spec_id)
        deployment = None
        for d in self._deployments:
            if d.spec_id == spec_id:
                deployment = d
                break

        return strategy_lifecycle_report(spec, results, deployment=deployment)

    def get_evolution_report(self) -> str:
        """Get a report of all evolution cycles."""
        cycle_dicts = []
        for cr in self._evolver._cycle_results:
            cycle_dicts.append({
                "cycle_number": cr.cycle_number,
                "mode": cr.mode,
                "specs_generated": cr.specs_generated,
                "specs_screened": cr.specs_screened,
                "specs_passed": cr.specs_passed,
                "best_sharpe": cr.best_sharpe,
                "duration_seconds": cr.duration_seconds,
            })

        best = self._registry.get_best_specs(
            phase="screen", metric="sharpe_ratio", limit=5, passed_only=False,
        )

        return evolution_summary_report(
            cycle_dicts, best, self._llm.session.summary()
        )
