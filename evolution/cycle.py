"""Top-level evolution cycle orchestrator.

Wires together: planner → generator → compiler → tournament → auditor → store.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agents.auditor.agent import AuditorAgent, AuditReport
from agents.auditor.layer2 import Layer2Auditor
from evaluation.multi_period import (
    MultiPeriodBacktester,
    load_evolution_settings,
)
from evaluation.tournament import Tournament, TournamentResult
from evolution.planner import EvolutionPlanner
from evolution.promoter import StrategyPromoter
from evolution.store import EvolutionStore
from knowledge.store import MarkdownMemory
from strategies.generator import StrategyGenerator
from strategies.spec import StrategySpec
from strategies.template_engine import TemplateStrategy, compile_spec

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class EvolutionCycleResult:
    """Outcome of one evolution cycle."""

    cycle_id: int = 0
    specs_generated: int = 0
    specs_compiled: int = 0
    compile_failures: int = 0
    tournament_result: TournamentResult | None = None
    audit_results: list[AuditReport] = field(default_factory=list)
    best_score: float = 0.0
    exhaustion_detected: bool = False


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class EvolutionCycle:
    """Complete evolution cycle from generation to persistence."""

    def __init__(
        self,
        planner: EvolutionPlanner | None = None,
        backtester: MultiPeriodBacktester | None = None,
        tournament: Tournament | None = None,
        auditor: AuditorAgent | None = None,
        layer2_auditor: Layer2Auditor | None = None,
        store: EvolutionStore | None = None,
        promoter: StrategyPromoter | None = None,
        settings: dict[str, Any] | None = None,
    ) -> None:
        self._settings = settings or load_evolution_settings()
        self._store = store or EvolutionStore()
        self._promoter = promoter or StrategyPromoter()

        batch_size = int(self._settings.get("batch_size", 10))
        survivor_count = int(self._settings.get("survivor_count", 3))
        min_sharpe_floor = float(self._settings.get("min_sharpe_floor", -0.5))
        ticker = self._settings.get("backtest_ticker", "SPY")

        generator = StrategyGenerator(batch_size=batch_size)
        memory = MarkdownMemory()

        self._planner = planner or EvolutionPlanner(memory, generator, self._store)
        self._backtester = backtester or MultiPeriodBacktester(
            min_sharpe_floor=min_sharpe_floor,
            ticker=ticker,
        )
        self._tournament = tournament or Tournament(self._backtester, survivor_count)
        self._auditor = auditor or AuditorAgent()
        self._layer2_auditor = layer2_auditor or Layer2Auditor()

    def run(self, trigger: str = "manual") -> EvolutionCycleResult:
        """Execute one full evolution cycle.

        Steps:
        1. Check daily limit.
        2. Start cycle in store.
        3. Generate strategy specs via planner.
        4. Compile specs into executable strategies.
        5. Run tournament.
        6. Audit survivors.
        7. Persist everything.
        8. Check exhaustion.
        """
        result = EvolutionCycleResult()

        # 1. Check daily limit.
        if not self._store.can_run_today():
            logger.info("Evolution cycle already ran today; skipping.")
            return result

        # 1b. Check exhaustion — skip if recent cycles show no improvement.
        exhaustion_cfg = self._settings.get("exhaustion_detection", {})
        plateau_cycles = int(exhaustion_cfg.get("plateau_cycles", 5))
        min_improvement = float(
            exhaustion_cfg.get("min_score_improvement", 0.01)
        )
        if self._store.check_exhaustion(plateau_cycles, min_improvement):
            logger.warning(
                "Evolution exhaustion detected (last %d cycles show "
                "< %.4f improvement); skipping generation.",
                plateau_cycles, min_improvement,
            )
            result.exhaustion_detected = True
            return result

        # 2. Start cycle.
        cycle_id = self._store.start_cycle(trigger)
        result.cycle_id = cycle_id
        logger.info("Evolution cycle %d started (trigger=%s)", cycle_id, trigger)

        # 3. Generate specs.
        try:
            context = self._planner.plan_generation()
            specs = self._planner.generate(context)
        except Exception:
            logger.exception("Evolution cycle %d: generation failed", cycle_id)
            self._store.complete_cycle(cycle_id, 0.0)
            return result

        result.specs_generated = len(specs)
        logger.info("Cycle %d: generated %d specs", cycle_id, len(specs))

        # 4. Compile specs.
        compiled: list[TemplateStrategy] = []
        spec_map: dict[str, StrategySpec] = {}
        for spec in specs:
            try:
                strategy = compile_spec(spec)
                compiled.append(strategy)
                spec_map[strategy.name] = spec
            except ValueError as exc:
                logger.warning("Cycle %d: compile failed for '%s': %s", cycle_id, spec.name, exc)
                result.compile_failures += 1

        result.specs_compiled = len(compiled)
        logger.info(
            "Cycle %d: compiled %d, failures %d",
            cycle_id, len(compiled), result.compile_failures,
        )

        if not compiled:
            logger.warning("Cycle %d: no strategies compiled; aborting", cycle_id)
            self._store.complete_cycle(cycle_id, 0.0)
            return result

        # 5. Tournament.
        tournament_result = self._tournament.run(compiled, cycle_number=cycle_id)
        result.tournament_result = tournament_result

        # Save all results to store.
        for rank_idx, mp_result in enumerate(tournament_result.all_results):
            is_survivor = mp_result in tournament_result.survivors
            spec = spec_map.get(mp_result.strategy_name)
            spec_json = json.dumps(spec.to_dict()) if spec else "{}"
            self._store.save_spec_result(
                cycle_id=cycle_id,
                spec_json=spec_json,
                name=mp_result.strategy_name,
                score=mp_result.composite_score,
                rank=rank_idx + 1,
                is_survivor=is_survivor,
            )

        # 6. Audit survivors — track which ones pass.
        audit_passed: set[str] = set()
        for mp_result in tournament_result.survivors:
            spec = spec_map.get(mp_result.strategy_name)
            if spec is None:
                logger.warning(
                    "Cycle %d: no spec found for survivor '%s'; skipping audit",
                    cycle_id, mp_result.strategy_name,
                )
                continue

            try:
                audit_report = self._auditor.audit_strategy_spec(
                    spec, mp_result,
                )
                result.audit_results.append(audit_report)

                findings_dicts = [
                    {
                        "check_name": f.check_name,
                        "severity": f.severity,
                        "description": f.description,
                    }
                    for f in audit_report.findings
                ]
                self._store.save_feedback(
                    cycle_id=cycle_id,
                    spec_name=mp_result.strategy_name,
                    feedback=audit_report.feedback,
                    findings=findings_dicts,
                )

                if audit_report.passed:
                    audit_passed.add(mp_result.strategy_name)
                else:
                    logger.warning(
                        "Cycle %d: audit FAILED for '%s' — "
                        "will not promote",
                        cycle_id, mp_result.strategy_name,
                    )
            except Exception:
                logger.exception(
                    "Cycle %d: audit exception for '%s' — "
                    "will not promote",
                    cycle_id, mp_result.strategy_name,
                )

        # 7. Submit only audit-passed survivors as promotion candidates.
        for mp_result in tournament_result.survivors:
            if mp_result.strategy_name not in audit_passed:
                continue
            spec = spec_map.get(mp_result.strategy_name)
            if spec is None:
                continue
            try:
                self._promoter.submit_candidate(
                    name=mp_result.strategy_name,
                    spec_json=json.dumps(spec.to_dict()),
                    score=mp_result.composite_score,
                )
                self._promoter.start_testing(mp_result.strategy_name)
            except Exception:
                logger.exception(
                    "Cycle %d: failed to submit candidate '%s'",
                    cycle_id, mp_result.strategy_name,
                )

        # 8. Check if any paper-testing strategies are ready for promotion.
        promo_cfg = self._settings.get("promotion", {})
        testing_days = int(promo_cfg.get("testing_days", 5))
        min_signals = int(promo_cfg.get("min_signals", 1))
        ready = self._promoter.check_ready_for_promotion(testing_days, min_signals)
        for name in ready:
            try:
                self._promoter.promote(name)
            except Exception:
                logger.exception("Cycle %d: failed to promote '%s'", cycle_id, name)

        # 9. Complete cycle.
        best_score = max(
            (r.composite_score for r in tournament_result.all_results),
            default=0.0,
        )
        result.best_score = best_score
        self._store.complete_cycle(cycle_id, best_score)

        # 10. Check exhaustion (post-cycle — for reporting only).
        result.exhaustion_detected = self._store.check_exhaustion(
            plateau_cycles, min_improvement,
        )

        logger.info(
            "Evolution cycle %d complete: generated=%d, compiled=%d, best=%.4f, exhaustion=%s",
            cycle_id,
            result.specs_generated,
            result.specs_compiled,
            result.best_score,
            result.exhaustion_detected,
        )

        return result
