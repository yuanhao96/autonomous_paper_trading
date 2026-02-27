"""SQLite-backed strategy and results storage."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.core.db import get_engine, init_db
from src.strategies.spec import RiskParams, StrategyResult, StrategySpec


class StrategyRegistry:
    """CRUD interface for strategy specs and backtest results."""

    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or get_engine()
        init_db(self._engine)

    # ── Strategy CRUD ───────────────────────────────────────────────

    def save_spec(self, spec: StrategySpec) -> None:
        """Insert or update a strategy spec."""
        spec_dict = {
            "id": spec.id,
            "name": spec.name,
            "template": spec.template,
            "version": spec.version,
            "spec_json": json.dumps(_spec_to_dict(spec)),
            "parent_id": spec.parent_id,
            "generation": spec.generation,
            "created_at": spec.created_at.isoformat(),
            "created_by": spec.created_by,
        }
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT OR REPLACE INTO strategies
                    (id, name, template, version, spec_json, parent_id, generation, created_at, created_by)
                VALUES
                    (:id, :name, :template, :version, :spec_json, :parent_id, :generation, :created_at, :created_by)
            """), spec_dict)

    def get_spec(self, spec_id: str) -> StrategySpec | None:
        """Load a strategy spec by ID."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT spec_json FROM strategies WHERE id = :id"),
                {"id": spec_id},
            ).fetchone()
        if row is None:
            return None
        return _dict_to_spec(json.loads(row[0]))

    def list_specs(
        self,
        template: str | None = None,
        created_by: str | None = None,
        limit: int = 100,
    ) -> list[StrategySpec]:
        """List strategy specs with optional filters."""
        query = "SELECT spec_json FROM strategies WHERE 1=1"
        params: dict[str, Any] = {}
        if template is not None:
            query += " AND template = :template"
            params["template"] = template
        if created_by is not None:
            query += " AND created_by = :created_by"
            params["created_by"] = created_by
        query += " ORDER BY created_at DESC LIMIT :limit"
        params["limit"] = limit

        with self._engine.connect() as conn:
            rows = conn.execute(text(query), params).fetchall()
        return [_dict_to_spec(json.loads(row[0])) for row in rows]

    def delete_spec(self, spec_id: str) -> bool:
        """Delete a strategy spec and its results."""
        with self._engine.begin() as conn:
            conn.execute(text("DELETE FROM results WHERE spec_id = :id"), {"id": spec_id})
            result = conn.execute(text("DELETE FROM strategies WHERE id = :id"), {"id": spec_id})
        return result.rowcount > 0

    # ── Results CRUD ────────────────────────────────────────────────

    def save_result(self, result: StrategyResult) -> None:
        """Save a backtest/validation result."""
        metrics = {
            "total_return": result.total_return,
            "annual_return": result.annual_return,
            "sharpe_ratio": result.sharpe_ratio,
            "sortino_ratio": result.sortino_ratio,
            "max_drawdown": result.max_drawdown,
            "max_drawdown_duration_days": result.max_drawdown_duration_days,
            "win_rate": result.win_rate,
            "profit_factor": result.profit_factor,
            "total_trades": result.total_trades,
            "total_fees": result.total_fees,
            "total_slippage": result.total_slippage,
            "backtest_start": result.backtest_start,
            "backtest_end": result.backtest_end,
            "run_duration_seconds": result.run_duration_seconds,
            "optimized_parameters": result.optimized_parameters,
        }
        row = {
            "spec_id": result.spec_id,
            "phase": result.phase,
            "passed": 1 if result.passed else 0,
            "metrics_json": json.dumps(metrics),
            "failure_reason": result.failure_reason,
            "failure_details": result.failure_details,
            "created_at": datetime.utcnow().isoformat(),
        }
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO results
                    (spec_id, phase, passed, metrics_json, failure_reason, failure_details, created_at)
                VALUES
                    (:spec_id, :phase, :passed, :metrics_json, :failure_reason, :failure_details, :created_at)
            """), row)

    def get_results(self, spec_id: str, phase: str | None = None) -> list[StrategyResult]:
        """Get all results for a strategy, optionally filtered by phase."""
        query = "SELECT spec_id, phase, passed, metrics_json, failure_reason, failure_details FROM results WHERE spec_id = :spec_id"
        params: dict[str, Any] = {"spec_id": spec_id}
        if phase is not None:
            query += " AND phase = :phase"
            params["phase"] = phase
        query += " ORDER BY created_at DESC"

        with self._engine.connect() as conn:
            rows = conn.execute(text(query), params).fetchall()

        results = []
        for row in rows:
            metrics = json.loads(row[3])
            results.append(StrategyResult(
                spec_id=row[0],
                phase=row[1],
                passed=bool(row[2]),
                total_return=metrics.get("total_return", 0.0),
                annual_return=metrics.get("annual_return", 0.0),
                sharpe_ratio=metrics.get("sharpe_ratio", 0.0),
                sortino_ratio=metrics.get("sortino_ratio", 0.0),
                max_drawdown=metrics.get("max_drawdown", 0.0),
                max_drawdown_duration_days=metrics.get("max_drawdown_duration_days", 0),
                win_rate=metrics.get("win_rate", 0.0),
                profit_factor=metrics.get("profit_factor", 0.0),
                total_trades=metrics.get("total_trades", 0),
                total_fees=metrics.get("total_fees", 0.0),
                total_slippage=metrics.get("total_slippage", 0.0),
                backtest_start=metrics.get("backtest_start", ""),
                backtest_end=metrics.get("backtest_end", ""),
                run_duration_seconds=metrics.get("run_duration_seconds", 0.0),
                optimized_parameters=metrics.get("optimized_parameters", {}),
                failure_reason=row[4],
                failure_details=row[5],
            ))
        return results

    def get_best_specs(self, phase: str = "screen", metric: str = "sharpe_ratio", limit: int = 10, passed_only: bool = True) -> list[tuple[StrategySpec, StrategyResult]]:
        """Get top specs ranked by a metric from their results."""
        if passed_only:
            where = "WHERE r.phase = :phase AND r.passed = 1"
        else:
            where = "WHERE r.phase = :phase"
        with self._engine.connect() as conn:
            rows = conn.execute(text(f"""
                SELECT s.spec_json, r.spec_id, r.phase, r.passed, r.metrics_json,
                       r.failure_reason, r.failure_details
                FROM results r
                JOIN strategies s ON s.id = r.spec_id
                {where}
                ORDER BY r.created_at DESC
                LIMIT :limit
            """), {"phase": phase, "limit": limit * 3}).fetchall()

        pairs: list[tuple[StrategySpec, StrategyResult]] = []
        seen_ids: set[str] = set()
        for row in rows:
            spec = _dict_to_spec(json.loads(row[0]))
            if spec.id in seen_ids:
                continue
            seen_ids.add(spec.id)
            metrics = json.loads(row[4])
            result = StrategyResult(
                spec_id=row[1],
                phase=row[2],
                passed=bool(row[3]),
                sharpe_ratio=metrics.get("sharpe_ratio", 0.0),
                total_return=metrics.get("total_return", 0.0),
                annual_return=metrics.get("annual_return", 0.0),
                max_drawdown=metrics.get("max_drawdown", 0.0),
                total_trades=metrics.get("total_trades", 0),
                failure_reason=row[5],
                failure_details=row[6],
            )
            pairs.append((spec, result))

        pairs.sort(key=lambda p: getattr(p[1], metric, 0.0), reverse=True)
        return pairs[:limit]


# ── Serialization helpers ───────────────────────────────────────────

def _universe_spec_to_dict(us: Any) -> dict[str, Any] | None:
    """Convert a UniverseSpec to a JSON-serializable dict."""
    if us is None:
        return None
    return {
        "id": us.id,
        "name": us.name,
        "asset_class": us.asset_class,
        "filters": [
            {"field": f.field, "operator": f.operator, "value": f.value}
            for f in us.filters
        ],
        "max_securities": us.max_securities,
        "min_securities": us.min_securities,
        "rebalance_frequency": us.rebalance_frequency,
        "static_symbols": us.static_symbols,
        "computation": us.computation,
        "computation_params": us.computation_params,
    }


def _dict_to_universe_spec(d: dict[str, Any] | None) -> Any:
    """Reconstruct a UniverseSpec from a dict, or return None."""
    if d is None:
        return None
    from src.universe.spec import Filter, UniverseSpec

    filters = [
        Filter(field=f["field"], operator=f["operator"], value=f["value"])
        for f in d.get("filters", [])
    ]
    return UniverseSpec(
        asset_class=d["asset_class"],
        filters=filters,
        max_securities=d.get("max_securities", 50),
        min_securities=d.get("min_securities", 1),
        rebalance_frequency=d.get("rebalance_frequency", "monthly"),
        static_symbols=d.get("static_symbols"),
        computation=d.get("computation"),
        computation_params=d.get("computation_params", {}),
        id=d.get("id", ""),
        name=d.get("name", ""),
    )


def _spec_to_dict(spec: StrategySpec) -> dict[str, Any]:
    """Convert StrategySpec to a JSON-serializable dict."""
    return {
        "id": spec.id,
        "name": spec.name,
        "template": spec.template,
        "version": spec.version,
        "parameters": spec.parameters,
        "universe_id": spec.universe_id,
        "universe_spec": _universe_spec_to_dict(spec.universe_spec),
        "risk": {
            "stop_loss_pct": spec.risk.stop_loss_pct,
            "take_profit_pct": spec.risk.take_profit_pct,
            "trailing_stop_pct": spec.risk.trailing_stop_pct,
            "max_position_pct": spec.risk.max_position_pct,
            "max_positions": spec.risk.max_positions,
            "position_size_method": spec.risk.position_size_method,
        },
        "combination": spec.combination,
        "combination_method": spec.combination_method,
        "parent_id": spec.parent_id,
        "generation": spec.generation,
        "created_at": spec.created_at.isoformat(),
        "created_by": spec.created_by,
    }


def _dict_to_spec(d: dict[str, Any]) -> StrategySpec:
    """Reconstruct a StrategySpec from a dict."""
    risk_data = d.get("risk", {})
    spec = StrategySpec(
        id=d["id"],
        name=d["name"],
        template=d["template"],
        version=d.get("version", 1),
        parameters=d["parameters"],
        universe_id=d["universe_id"],
        risk=RiskParams(
            stop_loss_pct=risk_data.get("stop_loss_pct"),
            take_profit_pct=risk_data.get("take_profit_pct"),
            trailing_stop_pct=risk_data.get("trailing_stop_pct"),
            max_position_pct=risk_data.get("max_position_pct", 0.10),
            max_positions=risk_data.get("max_positions", 10),
            position_size_method=risk_data.get("position_size_method", "equal_weight"),
        ),
        combination=d.get("combination", []),
        combination_method=d.get("combination_method", "equal_weight"),
        parent_id=d.get("parent_id"),
        generation=d.get("generation", 0),
        created_at=datetime.fromisoformat(d["created_at"]),
        created_by=d.get("created_by", "human"),
    )
    spec.universe_spec = _dict_to_universe_spec(d.get("universe_spec"))
    return spec
