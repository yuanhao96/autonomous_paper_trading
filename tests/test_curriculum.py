"""Tests for knowledge.curriculum — curriculum progression tracking."""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge.curriculum import CurriculumTracker, Topic

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CURRICULUM_YAML_PATH = str(
    Path(__file__).resolve().parent.parent / "config" / "curriculum.yaml"
)


@pytest.fixture
def tracker(tmp_path: Path) -> CurriculumTracker:
    """Create a CurriculumTracker using the real curriculum YAML and temp memory."""
    return CurriculumTracker(
        curriculum_path=_CURRICULUM_YAML_PATH,
        memory_root=str(tmp_path / "memory"),
    )


# ---------------------------------------------------------------------------
# Tests — loading
# ---------------------------------------------------------------------------


class TestCurriculumLoading:
    def test_loads_curriculum_yaml(self, tracker: CurriculumTracker) -> None:
        """CurriculumTracker should parse all stages from curriculum.yaml."""
        all_topics = tracker.get_all_topics()
        assert len(all_topics) > 0
        assert all(isinstance(t, Topic) for t in all_topics)

    def test_has_four_stages(self, tracker: CurriculumTracker) -> None:
        # The curriculum YAML defines stages 1-4.
        assert 1 in tracker._stages
        assert 2 in tracker._stages
        assert 3 in tracker._stages
        assert 4 in tracker._stages


# ---------------------------------------------------------------------------
# Tests — stage progression
# ---------------------------------------------------------------------------


class TestCurrentStage:
    def test_starts_at_stage_1(self, tracker: CurriculumTracker) -> None:
        assert tracker.get_current_stage() == 1

    def test_stays_at_1_until_all_topics_mastered(self, tracker: CurriculumTracker) -> None:
        # Set mastery for some but not all stage-1 topics.
        stage_1_topics = tracker._stages[1]
        if len(stage_1_topics) > 1:
            tracker.set_mastery(stage_1_topics[0].id, 0.9)
            assert tracker.get_current_stage() == 1

    def test_advances_to_stage_2(self, tracker: CurriculumTracker) -> None:
        for topic in tracker._stages[1]:
            tracker.set_mastery(topic.id, 0.8)  # above threshold of 0.7
        assert tracker.get_current_stage() == 2


# ---------------------------------------------------------------------------
# Tests — mastery scores
# ---------------------------------------------------------------------------


class TestMastery:
    def test_default_mastery_is_zero(self, tracker: CurriculumTracker) -> None:
        assert tracker.get_mastery("market_microstructure") == 0.0

    def test_set_and_get_mastery(self, tracker: CurriculumTracker) -> None:
        tracker.set_mastery("market_microstructure", 0.65, notes="initial study")
        assert tracker.get_mastery("market_microstructure") == pytest.approx(0.65)

    def test_update_mastery(self, tracker: CurriculumTracker) -> None:
        tracker.set_mastery("order_types", 0.3)
        tracker.set_mastery("order_types", 0.75)
        assert tracker.get_mastery("order_types") == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# Tests — is_stage_complete
# ---------------------------------------------------------------------------


class TestIsStageComplete:
    def test_incomplete_stage(self, tracker: CurriculumTracker) -> None:
        assert tracker.is_stage_complete(1) is False

    def test_complete_stage(self, tracker: CurriculumTracker) -> None:
        for topic in tracker._stages[1]:
            tracker.set_mastery(topic.id, 0.8)
        assert tracker.is_stage_complete(1) is True

    def test_nonexistent_stage_is_complete(self, tracker: CurriculumTracker) -> None:
        """A stage with no topics is considered complete."""
        assert tracker.is_stage_complete(999) is True


# ---------------------------------------------------------------------------
# Tests — get_next_learning_tasks
# ---------------------------------------------------------------------------


class TestGetNextLearningTasks:
    def test_returns_lowest_mastery_topics(self, tracker: CurriculumTracker) -> None:
        stage_1 = tracker._stages[1]
        # Give one topic a higher score.
        tracker.set_mastery(stage_1[0].id, 0.5)
        # Leave the rest at 0.0.

        tasks = tracker.get_next_learning_tasks(max_tasks=3)
        assert len(tasks) <= 3
        assert all(isinstance(t, Topic) for t in tasks)
        # The topic with score 0.5 should not be first (it has higher mastery).
        if len(tasks) > 1:
            assert tasks[0].id != stage_1[0].id

    def test_returns_only_unmastered(self, tracker: CurriculumTracker) -> None:
        """Topics at or above the mastery threshold should not appear."""
        for topic in tracker._stages[1]:
            tracker.set_mastery(topic.id, 0.8)
        tasks = tracker.get_next_learning_tasks()
        # All stage-1 topics are mastered; current stage moves to 2.
        # Tasks should come from stage 2.
        if tasks:
            assert all(t.stage_number == 2 for t in tasks)


# ---------------------------------------------------------------------------
# Tests — stage progress
# ---------------------------------------------------------------------------


class TestStageProgress:
    def test_stage_progress(self, tracker: CurriculumTracker) -> None:
        tracker.set_mastery("market_microstructure", 0.4)
        progress = tracker.get_stage_progress(1)
        assert "market_microstructure" in progress
        assert progress["market_microstructure"] == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# Tests — ongoing tasks
# ---------------------------------------------------------------------------


class TestOngoingTasks:
    def test_ongoing_tasks_loaded(self, tracker: CurriculumTracker) -> None:
        ongoing = tracker.get_ongoing_tasks()
        assert len(ongoing) >= 1
        assert any(t["id"] == "daily_news" for t in ongoing)
