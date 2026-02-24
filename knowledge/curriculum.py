"""Curriculum progression tracker.

Loads a structured curriculum from YAML and tracks per-topic mastery
scores in markdown files via ``MarkdownMemory``.  The trading agent
advances through stages sequentially: stage N+1 unlocks only when every
topic in stage N reaches the configured mastery threshold.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from knowledge.store import MarkdownMemory


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
    memory_root:
        Root directory for the markdown memory store.
    """

    def __init__(
        self,
        curriculum_path: str = "config/curriculum.yaml",
        memory_root: str = "knowledge/memory/trading",
    ) -> None:
        self._curriculum_path = curriculum_path
        self._memory = MarkdownMemory(memory_root=memory_root)

        # Load curriculum definition from YAML.
        with open(self._curriculum_path, "r") as fh:
            self._curriculum: dict[str, Any] = yaml.safe_load(fh)

        self._mastery_threshold: float = float(
            self._curriculum.get("mastery_threshold", 0.7)
        )

        # Parse stages and topics.
        self._stages: dict[int, list[Topic]] = {}
        self._topic_stage: dict[str, int] = {}
        for stage in self._curriculum.get("stages", []):
            stage_number: int = int(stage["stage_number"])
            topics: list[Topic] = []
            for t in stage.get("topics", []):
                topic = Topic(
                    id=t["id"],
                    name=t["name"],
                    description=t.get("description", ""),
                    mastery_criteria=t.get("mastery_criteria", ""),
                    stage_number=stage_number,
                )
                topics.append(topic)
                self._topic_stage[topic.id] = stage_number
            self._stages[stage_number] = topics

        # Parse ongoing tasks (kept as raw dicts).
        self._ongoing: list[dict[str, Any]] = list(
            self._curriculum.get("ongoing", [])
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _slugify_topic_id(self, name: str) -> str:
        """Convert a human-readable topic name into a stable topic_id."""
        slug = name.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "_", slug)
        slug = slug.strip("_")
        return slug or "discovered_topic"

    def _persist_curriculum(self) -> None:
        """Persist in-memory curriculum updates back to curriculum YAML."""
        stage_payloads: list[dict[str, Any]] = []
        existing_stages = {
            int(stage.get("stage_number", 0)): stage
            for stage in self._curriculum.get("stages", [])
            if isinstance(stage, dict) and "stage_number" in stage
        }

        for stage_number in sorted(self._stages.keys()):
            stage_obj = existing_stages.get(stage_number, {})
            topics = self._stages.get(stage_number, [])
            stage_payload = dict(stage_obj) if stage_obj else {
                "name": f"Stage {stage_number}",
                "stage_number": stage_number,
                "description": "",
            }
            stage_payload["stage_number"] = stage_number
            stage_payload["topics"] = [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "mastery_criteria": t.mastery_criteria,
                }
                for t in topics
            ]
            stage_payloads.append(stage_payload)

        self._curriculum["stages"] = stage_payloads
        with open(self._curriculum_path, "w") as fh:
            yaml.safe_dump(self._curriculum, fh, sort_keys=False)

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
        stage = self._topic_stage.get(topic_id)
        if stage is None:
            return 0.0
        return self._memory.get_mastery(topic_id, stage)

    def set_mastery(
        self, topic_id: str, score: float, notes: str = ""
    ) -> None:
        """Record or update the mastery score for *topic_id*."""
        stage = self._topic_stage.get(topic_id)
        if stage is None:
            return
        self._memory.set_mastery(
            topic_id, stage, score, reasoning=notes
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

    def add_discovered_topic(
        self,
        name: str,
        description: str = "",
        mastery_criteria: str = "",
        stage_number: int | None = None,
    ) -> tuple[bool, str]:
        """Add a newly discovered topic to the curriculum and persist it.

        Returns
        -------
        tuple[bool, str]
            ``(added, topic_id)``, where ``added`` indicates whether a new topic
            was created (``False`` when a duplicate already exists).
        """
        clean_name = name.strip()
        if not clean_name:
            return False, ""

        topic_id = self._slugify_topic_id(clean_name)
        if topic_id in self._topic_stage:
            return False, topic_id

        target_stage = stage_number or self.get_current_stage()
        topic = Topic(
            id=topic_id,
            name=clean_name,
            description=description.strip(),
            mastery_criteria=(
                mastery_criteria.strip()
                or f"Can explain and apply {clean_name} in a concrete trading scenario"
            ),
            stage_number=target_stage,
        )
        self._stages.setdefault(target_stage, []).append(topic)
        self._topic_stage[topic_id] = target_stage
        self._persist_curriculum()
        return True, topic_id
