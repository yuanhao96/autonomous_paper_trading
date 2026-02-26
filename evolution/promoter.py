"""Strategy promotion lifecycle manager.

Tracks strategies through: candidate → paper_testing → promoted → retired.
Tournament survivors are submitted as candidates, then progress through
a paper-testing period before being promoted to live trading.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Valid status transitions.
_VALID_STATUSES = {"candidate", "paper_testing", "promoted", "retired"}


class StrategyPromoter:
    """Manages strategy promotion lifecycle in SQLite."""

    def __init__(self, db_path: str = "data/evolution.db") -> None:
        self._db_path = Path(db_path)
        if not self._db_path.is_absolute():
            self._db_path = _PROJECT_ROOT / self._db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_promotion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spec_name TEXT NOT NULL UNIQUE,
                    spec_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'candidate',
                    composite_score REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    testing_started_at TEXT,
                    promoted_at TEXT,
                    retired_at TEXT,
                    signals_generated INTEGER DEFAULT 0,
                    notes TEXT DEFAULT ''
                )
            """)

    def submit_candidate(
        self,
        name: str,
        spec_json: str,
        score: float = 0.0,
    ) -> None:
        """Submit a tournament survivor as a promotion candidate.

        If a strategy with the same name already exists in a non-retired
        state, it is skipped (no duplicate entries).
        """
        now = datetime.now(tz=timezone.utc).isoformat()
        with sqlite3.connect(str(self._db_path)) as conn:
            # Skip if already tracked and not retired.
            row = conn.execute(
                "SELECT status FROM strategy_promotion WHERE spec_name = ?",
                (name,),
            ).fetchone()
            if row and row[0] != "retired":
                logger.debug("Strategy '%s' already tracked (status=%s); skipping", name, row[0])
                return

            # If retired, remove old entry so it can be re-submitted.
            if row and row[0] == "retired":
                conn.execute(
                    "DELETE FROM strategy_promotion WHERE spec_name = ?",
                    (name,),
                )

            conn.execute(
                "INSERT INTO strategy_promotion "
                "(spec_name, spec_json, status, composite_score, created_at) "
                "VALUES (?, ?, 'candidate', ?, ?)",
                (name, spec_json, score, now),
            )
            logger.info("Submitted candidate: %s (score=%.3f)", name, score)

    def start_testing(self, name: str) -> bool:
        """Move a candidate to paper_testing status.

        Returns True if the transition succeeded, False otherwise.
        """
        now = datetime.now(tz=timezone.utc).isoformat()
        with sqlite3.connect(str(self._db_path)) as conn:
            result = conn.execute(
                "UPDATE strategy_promotion "
                "SET status = 'paper_testing', testing_started_at = ? "
                "WHERE spec_name = ? AND status = 'candidate'",
                (now, name),
            )
            if result.rowcount > 0:
                logger.info("Started paper-testing for '%s'", name)
                return True
            return False

    def record_signals(self, name: str, count: int = 1) -> None:
        """Increment the signal count for a paper-testing strategy."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "UPDATE strategy_promotion "
                "SET signals_generated = signals_generated + ? "
                "WHERE spec_name = ? AND status = 'paper_testing'",
                (count, name),
            )

    def check_ready_for_promotion(
        self,
        testing_days: int = 5,
        min_signals: int = 1,
    ) -> list[str]:
        """Return names of strategies ready for promotion.

        A strategy is ready when:
        - It has been in paper_testing for at least ``testing_days`` days.
        - It has generated at least ``min_signals`` signals.
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute(
                "SELECT spec_name, testing_started_at, signals_generated "
                "FROM strategy_promotion "
                "WHERE status = 'paper_testing'",
            ).fetchall()

        now = datetime.now(tz=timezone.utc)
        ready: list[str] = []
        for spec_name, started_at, signals in rows:
            if not started_at:
                continue
            started = datetime.fromisoformat(started_at)
            elapsed = (now - started).days
            if elapsed >= testing_days and signals >= min_signals:
                ready.append(spec_name)

        return ready

    def promote(self, name: str) -> bool:
        """Promote a paper-testing strategy to live trading.

        Returns True if successful.
        """
        now = datetime.now(tz=timezone.utc).isoformat()
        with sqlite3.connect(str(self._db_path)) as conn:
            result = conn.execute(
                "UPDATE strategy_promotion "
                "SET status = 'promoted', promoted_at = ? "
                "WHERE spec_name = ? AND status = 'paper_testing'",
                (now, name),
            )
            if result.rowcount > 0:
                logger.info("Promoted strategy '%s' to live trading", name)
                return True
            return False

    def retire(self, name: str, reason: str = "") -> bool:
        """Retire a strategy (remove from live trading).

        Can retire from any non-retired status.
        """
        now = datetime.now(tz=timezone.utc).isoformat()
        with sqlite3.connect(str(self._db_path)) as conn:
            result = conn.execute(
                "UPDATE strategy_promotion "
                "SET status = 'retired', retired_at = ?, notes = ? "
                "WHERE spec_name = ? AND status != 'retired'",
                (now, reason, name),
            )
            if result.rowcount > 0:
                logger.info("Retired strategy '%s': %s", name, reason)
                return True
            return False

    def get_promoted(self) -> list[dict]:
        """Return spec_json dicts for all promoted strategies."""
        import json

        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute(
                "SELECT spec_json FROM strategy_promotion "
                "WHERE status = 'promoted' "
                "ORDER BY composite_score DESC",
            ).fetchall()

        specs: list[dict] = []
        for (spec_json,) in rows:
            try:
                specs.append(json.loads(spec_json))
            except Exception:
                logger.warning("Failed to parse promoted spec JSON")
        return specs

    def get_paper_testing(self) -> list[str]:
        """Return names of strategies currently in paper-testing."""
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute(
                "SELECT spec_name FROM strategy_promotion "
                "WHERE status = 'paper_testing'",
            ).fetchall()
        return [r[0] for r in rows]

    def get_candidates(self) -> list[str]:
        """Return names of strategies in candidate status."""
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute(
                "SELECT spec_name FROM strategy_promotion "
                "WHERE status = 'candidate'",
            ).fetchall()
        return [r[0] for r in rows]
