"""SQLite persistence for evolution cycle state.

Tracks cycles, strategy specs, audit feedback, and exhaustion detection.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class EvolutionStore:
    """Persistent store for evolution cycle data."""

    def __init__(self, db_path: str = "data/evolution.db") -> None:
        self._db_path = Path(db_path)
        if not self._db_path.is_absolute():
            self._db_path = _PROJECT_ROOT / self._db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS cycles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    trigger TEXT NOT NULL DEFAULT 'manual',
                    status TEXT NOT NULL DEFAULT 'running',
                    best_score REAL DEFAULT 0.0
                );

                CREATE TABLE IF NOT EXISTS strategy_specs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    composite_score REAL DEFAULT 0.0,
                    rank INTEGER DEFAULT 0,
                    is_survivor INTEGER DEFAULT 0,
                    FOREIGN KEY (cycle_id) REFERENCES cycles(id)
                );

                CREATE TABLE IF NOT EXISTS audit_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spec_id INTEGER,
                    cycle_id INTEGER NOT NULL,
                    feedback_text TEXT DEFAULT '',
                    findings_json TEXT DEFAULT '[]',
                    FOREIGN KEY (cycle_id) REFERENCES cycles(id)
                );

                CREATE TABLE IF NOT EXISTS exhaustion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id INTEGER NOT NULL,
                    best_score REAL DEFAULT 0.0,
                    plateau_count INTEGER DEFAULT 0,
                    FOREIGN KEY (cycle_id) REFERENCES cycles(id)
                );
            """)

    def start_cycle(self, trigger: str = "manual") -> int:
        """Create a new cycle record. Returns the cycle ID."""
        now = datetime.now(tz=timezone.utc).isoformat()
        with sqlite3.connect(str(self._db_path)) as conn:
            cursor = conn.execute(
                "INSERT INTO cycles (timestamp, trigger, status) VALUES (?, ?, 'running')",
                (now, trigger),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def complete_cycle(self, cycle_id: int, best_score: float) -> None:
        """Mark a cycle as completed with its best score."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "UPDATE cycles SET status = 'completed', best_score = ? WHERE id = ?",
                (best_score, cycle_id),
            )

    def save_spec_result(
        self,
        cycle_id: int,
        spec_json: str,
        name: str,
        score: float,
        rank: int,
        is_survivor: bool,
    ) -> int:
        """Save a strategy spec result. Returns the spec ID."""
        with sqlite3.connect(str(self._db_path)) as conn:
            cursor = conn.execute(
                "INSERT INTO strategy_specs "
                "(cycle_id, name, spec_json, composite_score, "
                "rank, is_survivor) VALUES (?, ?, ?, ?, ?, ?)",
                (cycle_id, name, spec_json, score, rank, int(is_survivor)),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def save_feedback(
        self,
        cycle_id: int,
        spec_name: str,
        feedback: str,
        findings: list[dict],
    ) -> None:
        """Save audit feedback for a strategy."""
        # Find the spec_id.
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute(
                "SELECT id FROM strategy_specs WHERE cycle_id = ? AND name = ?",
                (cycle_id, spec_name),
            ).fetchone()
            spec_id = row[0] if row else None

            conn.execute(
                "INSERT INTO audit_feedback (spec_id, cycle_id, feedback_text, findings_json) "
                "VALUES (?, ?, ?, ?)",
                (spec_id, cycle_id, feedback, json.dumps(findings)),
            )

    def get_recent_winners(self, limit: int = 10) -> list[dict]:
        """Return serialized specs of recent tournament survivors."""
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute(
                "SELECT spec_json FROM strategy_specs "
                "WHERE is_survivor = 1 "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()

        winners: list[dict] = []
        for (spec_json,) in rows:
            try:
                winners.append(json.loads(spec_json))
            except json.JSONDecodeError:
                pass
        return winners

    def get_recent_feedback(self, limit: int = 20) -> list[str]:
        """Return recent feedback strings."""
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute(
                "SELECT feedback_text FROM audit_feedback "
                "WHERE feedback_text != '' "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()

        return [row[0] for row in rows]

    def can_run_today(self) -> bool:
        """Check if a cycle has already completed today (UTC)."""
        today_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM cycles WHERE status = 'completed' AND timestamp LIKE ?",
                (f"{today_utc}%",),
            ).fetchone()
            count = row[0] if row else 0
        return count == 0

    def check_exhaustion(
        self,
        plateau_cycles: int = 5,
        min_improvement: float = 0.01,
    ) -> bool:
        """Check if the last N cycles show no improvement."""
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute(
                "SELECT best_score FROM cycles "
                "WHERE status = 'completed' "
                "ORDER BY id DESC LIMIT ?",
                (plateau_cycles,),
            ).fetchall()

        if len(rows) < plateau_cycles:
            return False

        scores = [r[0] for r in rows]
        improvement = max(scores) - min(scores)
        return improvement < min_improvement
