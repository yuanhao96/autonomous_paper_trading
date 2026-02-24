"""Curriculum progression tracker.

Loads a structured curriculum from YAML and tracks per-topic mastery
scores in a local SQLite database.  The trading agent advances through
stages sequentially: stage N+1 unlocks only when every topic in stage N
reaches the configured mastery threshold.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Topic:
    """A single curriculum topic."""

    id: str
    name: str
    description: str
    mastery_criteria: str
    stage_number: int


class CurriculumTracker:
    """Tracks learning progression through a staged curriculum.

    Parameters
    ----------
    curriculum_path:
        Path to the YAML curriculum definition file.
    db_path:
        Path to the SQLite database that persists mastery scores.
    """

    def __init__(
        self,
        curriculum_path: str = "config/curriculum.yaml",
        db_path: str = "data/curriculum_state.db",
    ) -> None:
        self._curriculum_path = curriculum_path
        self._db_path = db_path

        # Load curriculum definition from YAML.
        with open(self._curriculum_path, "r") as fh:
            self._curriculum: dict[str, Any] = yaml.safe_load(fh)

        self._mastery_threshold: float = float(
            self._curriculum.get("mastery_threshold", 0.7)
        )

        # Parse stages and topics.
        self._stages: dict[int, list[Topic]] = {}
        for stage in self._curriculum.get("stages", []):
            stage_number: int = int(stage["stage_number"])
            topics: list[Topic] = []
            for t in stage.get("topics", []):
                topics.append(
                    Topic(
                        id=t["id"],
                        name=t["name"],
                        description=t.get("description", ""),
                        mastery_criteria=t.get("mastery_criteria", ""),
                        stage_number=stage_number,
                    )
                )
            self._stages[stage_number] = topics

        # Parse ongoing tasks (kept as raw dicts).
        self._ongoing: list[dict[str, Any]] = list(
            self._curriculum.get("ongoing", [])
        )

        # Ensure the database directory exists and initialise the table.
        os.makedirs(Path(self._db_path).parent, exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mastery_scores (
                    topic_id      TEXT PRIMARY KEY,
                    score         REAL NOT NULL DEFAULT 0.0,
                    last_assessed TEXT,
                    notes         TEXT DEFAULT ''
                )
                """
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_current_stage(self) -> int:
        """Return the current stage number (lowest stage not yet fully mastered).

        If all stages are complete the highest stage number is returned.
        """
        for stage_number in sorted(self._stages.keys()):
            if not self.is_stage_complete(stage_number):
                return stage_number
        # All stages mastered – return the highest one.
        return max(self._stages.keys()) if self._stages else 1

    def get_mastery(self, topic_id: str) -> float:
        """Return the mastery score for *topic_id* (``0.0`` if never assessed)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT score FROM mastery_scores WHERE topic_id = ?",
                (topic_id,),
            ).fetchone()
        return float(row[0]) if row else 0.0

    def set_mastery(
        self, topic_id: str, score: float, notes: str = ""
    ) -> None:
        """Record or update the mastery score for *topic_id*."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO mastery_scores (topic_id, score, last_assessed, notes)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(topic_id)
                DO UPDATE SET score = excluded.score,
                              last_assessed = excluded.last_assessed,
                              notes = excluded.notes
                """,
                (topic_id, score, now, notes),
            )

    def get_stage_progress(self, stage_number: int) -> dict[str, float]:
        """Return ``{topic_id: score}`` for every topic in *stage_number*."""
        topics = self._stages.get(stage_number, [])
        return {topic.id: self.get_mastery(topic.id) for topic in topics}

    def is_stage_complete(self, stage_number: int) -> bool:
        """Return ``True`` if every topic in *stage_number* meets the mastery threshold."""
        topics = self._stages.get(stage_number, [])
        if not topics:
            return True
        return all(
            self.get_mastery(t.id) >= self._mastery_threshold for t in topics
        )

    def get_next_learning_tasks(self, max_tasks: int = 3) -> list[Topic]:
        """Return up to *max_tasks* topics with the lowest mastery in the current stage."""
        stage_number = self.get_current_stage()
        topics = self._stages.get(stage_number, [])

        scored: list[tuple[float, Topic]] = [
            (self.get_mastery(t.id), t) for t in topics
        ]
        # Filter to topics that still need work.
        unmastered = [
            (score, topic)
            for score, topic in scored
            if score < self._mastery_threshold
        ]
        # Sort ascending by score so the weakest topics come first.
        unmastered.sort(key=lambda pair: pair[0])
        return [topic for _, topic in unmastered[:max_tasks]]

    def get_all_topics(self) -> list[Topic]:
        """Return all topics across every stage, ordered by stage number."""
        result: list[Topic] = []
        for stage_number in sorted(self._stages.keys()):
            result.extend(self._stages[stage_number])
        return result

    def get_ongoing_tasks(self) -> list[dict[str, Any]]:
        """Return the list of ongoing (non-staged) task definitions."""
        return list(self._ongoing)
