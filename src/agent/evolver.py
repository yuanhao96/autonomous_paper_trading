"""Evolution engine — orchestrates the explore/exploit loop.

The evolver is the top-level orchestrator that:
1. Generates batches of strategy specs (mix of explore + exploit)
2. Screens them via Phase 1 (backtesting.py)
3. Validates top candidates via Phase 2 (multi-regime)
4. Runs audit checks
5. Stores everything to the registry
6. Decides whether to explore or exploit next cycle
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date

from src.agent.generator import AVAILABLE_UNIVERSES, StrategyGenerator
from src.agent.reviewer import format_history_for_llm, format_result_for_llm
from src.core.config import Settings, load_preferences
from src.core.llm import LLMClient
from src.data.manager import DataManager
from src.risk.auditor import Auditor
from src.risk.engine import RiskEngine
from src.screening.screener import Screener
from src.strategies.registry import StrategyRegistry
from src.strategies.spec import StrategyResult, StrategySpec
from src.universe.static import STATIC_UNIVERSES, get_static_universe
from src.validation.validator import Validator

logger = logging.getLogger(__name__)


@dataclass
class CycleResult:
    """Result of a single evolution cycle."""

    cycle_number: int
    specs_generated: int = 0
    specs_screened: int = 0
    specs_validated: int = 0
    specs_passed: int = 0
    best_sharpe: float = 0.0
    best_spec_id: str = ""
    mode: str = ""  # explore | exploit | mixed
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Cycle {self.cycle_number} ({self.mode}): "
            f"{self.specs_generated} generated → {self.specs_screened} screened → "
            f"{self.specs_validated} validated → {self.specs_passed} passed",
        ]
        if self.best_sharpe > 0:
            lines.append(f"  Best Sharpe: {self.best_sharpe:.2f} (spec {self.best_spec_id})")
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
        lines.append(f"  Duration: {self.duration_seconds:.1f}s")
        return "\n".join(lines)


class Evolver:
    """Evolution engine — runs the explore/exploit loop.

    Configuration (from settings.yaml):
        evolution.batch_size: Strategies per cycle (default 5)
        evolution.top_n_screen: Candidates advancing from screen → validation (default 3)
        evolution.explore_ratio: Fraction of batch for new templates (default 0.4)
        evolution.exhaustion_cycles: Cycles without improvement before pause (default 10)
    """

    def __init__(
        self,
        registry: StrategyRegistry | None = None,
        data_manager: DataManager | None = None,
        llm_client: LLMClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or Settings()
        self._registry = registry or StrategyRegistry()
        self._dm = data_manager or DataManager()
        self._llm = llm_client or LLMClient(settings=self._settings)
        self._generator = StrategyGenerator(llm_client=self._llm, settings=self._settings)
        self._screener = Screener(data_manager=self._dm, settings=self._settings)
        self._validator = Validator(data_manager=self._dm, settings=self._settings)
        self._risk_engine = RiskEngine()
        self._auditor = Auditor()

        # Evolution parameters
        self._batch_size = self._settings.get("evolution.batch_size", 5)
        self._top_n_screen = self._settings.get("evolution.top_n_screen", 3)
        self._explore_ratio = self._settings.get("evolution.explore_ratio", 0.4)
        self._exhaustion_cycles = self._settings.get("evolution.exhaustion_cycles", 10)

        # State
        self._cycle_count = 0
        self._best_sharpe_ever = -999.0
        self._cycles_without_improvement = 0
        self._cycle_results: list[CycleResult] = []

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def is_exhausted(self) -> bool:
        return self._cycles_without_improvement >= self._exhaustion_cycles

    @property
    def llm_session(self):
        return self._llm.session

    def run_cycle(
        self,
        symbols: list[str] | None = None,
        force_mode: str | None = None,
    ) -> CycleResult:
        """Run a single evolution cycle.

        Args:
            symbols: Override symbol list (default: use universe from generated specs).
            force_mode: Force "explore" or "exploit" mode (default: auto-balance).

        Returns:
            CycleResult with diagnostics.
        """
        t0 = time.time()
        self._cycle_count += 1
        cycle = CycleResult(cycle_number=self._cycle_count)

        # Determine mode
        mode = force_mode or self._decide_mode()
        cycle.mode = mode
        logger.info("Evolution cycle %d: mode=%s", self._cycle_count, mode)

        # Load history from registry
        history = self._registry.get_best_specs(
            phase="screen", metric="sharpe_ratio", limit=20, passed_only=False
        )

        # Generate batch
        specs = self._generate_batch(mode, history)
        cycle.specs_generated = len(specs)

        if not specs:
            cycle.errors.append("No specs generated")
            cycle.duration_seconds = time.time() - t0
            return cycle

        # Screen each spec
        screen_results: list[tuple[StrategySpec, StrategyResult]] = []
        for spec in specs:
            try:
                # Resolve symbols from universe
                syms = symbols or self._resolve_symbols(spec.universe_id)
                if not syms:
                    cycle.errors.append(f"No symbols for universe {spec.universe_id}")
                    continue

                # Risk check
                violations = self._risk_engine.check_spec(spec)
                if violations:
                    spec = self._risk_engine.clamp_spec(spec)

                # Screen
                result = self._screener.screen(
                    spec=spec,
                    symbols=syms,
                    start=date(2019, 1, 1),
                    end=date(2024, 12, 31),
                    optimize=False,
                )
                self._registry.save_spec(spec)
                self._registry.save_result(result)
                screen_results.append((spec, result))
                cycle.specs_screened += 1

            except Exception as e:
                logger.warning("Screening failed for %s: %s", spec.template, e)
                cycle.errors.append(f"Screen {spec.template}: {e}")

        # Select top candidates for validation
        screen_results.sort(key=lambda x: x[1].sharpe_ratio, reverse=True)
        top_candidates = screen_results[:self._top_n_screen]

        # Validate top candidates
        for spec, screen_result in top_candidates:
            try:
                syms = symbols or self._resolve_symbols(spec.universe_id)
                if not syms:
                    continue

                val_result = self._validator.validate(
                    spec=spec, symbols=syms, benchmark="SPY"
                )
                self._registry.save_result(val_result)
                cycle.specs_validated += 1

                # Audit
                audit = self._auditor.audit(screen_result, val_result)
                if audit.passed and val_result.passed:
                    cycle.specs_passed += 1
                    logger.info("Strategy PASSED audit: %s (Sharpe: %.2f)",
                                spec.template, val_result.sharpe_ratio)

                # Track best
                if val_result.sharpe_ratio > cycle.best_sharpe:
                    cycle.best_sharpe = val_result.sharpe_ratio
                    cycle.best_spec_id = spec.id

                # Log diagnostics
                diag = format_result_for_llm(spec, screen_result, val_result)
                logger.info("Cycle %d diagnostics:\n%s", self._cycle_count, diag)

            except Exception as e:
                logger.warning("Validation failed for %s: %s", spec.template, e)
                cycle.errors.append(f"Validate {spec.template}: {e}")

        # Update evolution state
        if cycle.best_sharpe > self._best_sharpe_ever:
            self._best_sharpe_ever = cycle.best_sharpe
            self._cycles_without_improvement = 0
        else:
            self._cycles_without_improvement += 1

        cycle.duration_seconds = time.time() - t0
        self._cycle_results.append(cycle)

        logger.info(cycle.summary())
        return cycle

    def run_cycles(
        self,
        n_cycles: int,
        symbols: list[str] | None = None,
    ) -> list[CycleResult]:
        """Run multiple evolution cycles.

        Stops early if exhaustion threshold is reached.
        """
        results = []
        for i in range(n_cycles):
            if self.is_exhausted:
                logger.info("Evolution exhausted after %d cycles without improvement",
                            self._cycles_without_improvement)
                break
            result = self.run_cycle(symbols=symbols)
            results.append(result)
        return results

    def get_evolution_summary(self) -> str:
        """Generate a summary of all evolution cycles."""
        lines = [
            f"Evolution Summary: {self._cycle_count} cycles",
            f"Best Sharpe ever: {self._best_sharpe_ever:.2f}",
            f"Cycles without improvement: {self._cycles_without_improvement}",
            f"Exhausted: {self.is_exhausted}",
            f"LLM usage: {self._llm.session.summary()}",
            "",
        ]
        for cr in self._cycle_results:
            lines.append(cr.summary())
            lines.append("")
        return "\n".join(lines)

    def _decide_mode(self) -> str:
        """Decide explore vs exploit based on evolution state."""
        if self._cycle_count <= 2:
            return "explore"  # Always explore first

        if self._cycles_without_improvement >= 5:
            return "explore"  # Plateau → explore new templates

        # Mix based on explore_ratio
        n_explore = int(self._batch_size * self._explore_ratio)
        if n_explore >= self._batch_size:
            return "explore"
        if n_explore == 0:
            return "exploit"
        return "mixed"

    def _generate_batch(
        self,
        mode: str,
        history: list[tuple[StrategySpec, StrategyResult]],
    ) -> list[StrategySpec]:
        """Generate a batch of strategies based on mode."""
        specs: list[StrategySpec] = []

        if mode == "explore":
            for _ in range(self._batch_size):
                try:
                    spec = self._generator.explore(history=history)
                    specs.append(spec)
                except Exception as e:
                    logger.warning("Explore generation failed: %s", e)
            return specs

        if mode == "exploit":
            parent = self._pick_parent(history)
            if parent is None:
                logger.warning("No parent for exploitation, falling back to explore")
                return self._generate_batch("explore", history)

            parent_spec, parent_result = parent
            for _ in range(self._batch_size):
                try:
                    spec = self._generator.exploit(
                        parent_spec=parent_spec,
                        screen_result=parent_result,
                        history=history,
                    )
                    specs.append(spec)
                except Exception as e:
                    logger.warning("Exploit generation failed: %s", e)
            return specs

        # Mixed mode
        n_explore = max(1, int(self._batch_size * self._explore_ratio))
        n_exploit = self._batch_size - n_explore

        for _ in range(n_explore):
            try:
                specs.append(self._generator.explore(history=history))
            except Exception as e:
                logger.warning("Explore generation failed: %s", e)

        parent = self._pick_parent(history)
        if parent:
            parent_spec, parent_result = parent
            for _ in range(n_exploit):
                try:
                    specs.append(self._generator.exploit(
                        parent_spec=parent_spec,
                        screen_result=parent_result,
                        history=history,
                    ))
                except Exception as e:
                    logger.warning("Exploit generation failed: %s", e)

        return specs

    def _pick_parent(
        self, history: list[tuple[StrategySpec, StrategyResult]]
    ) -> tuple[StrategySpec, StrategyResult] | None:
        """Pick the best parent strategy for exploitation."""
        if not history:
            return None
        # Pick the one with highest Sharpe ratio
        return max(history, key=lambda p: p[1].sharpe_ratio)

    def _resolve_symbols(self, universe_id: str) -> list[str]:
        """Resolve a universe ID to a list of symbols."""
        if universe_id in STATIC_UNIVERSES:
            return get_static_universe(universe_id)
        # Try common aliases
        aliases = {
            "sp500_sample": "sp500",
            "nasdaq100_sample": "nasdaq100",
        }
        canonical = aliases.get(universe_id, universe_id)
        if canonical in STATIC_UNIVERSES:
            return get_static_universe(canonical)
        # Fallback
        logger.warning("Unknown universe %s, using sector_etfs", universe_id)
        return get_static_universe("sector_etfs")
