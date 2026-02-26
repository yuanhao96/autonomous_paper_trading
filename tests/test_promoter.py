"""Tests for the strategy promotion lifecycle (evolution/promoter.py)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from evolution.promoter import StrategyPromoter


@pytest.fixture()
def promoter(tmp_path: Path) -> StrategyPromoter:
    """Return a StrategyPromoter backed by a temp database."""
    db = tmp_path / "test_evolution.db"
    return StrategyPromoter(db_path=str(db))


def _make_spec_json(name: str = "test_strategy") -> str:
    return json.dumps({"name": name, "version": "1.0", "indicators": []})


class TestSubmitCandidate:
    def test_submit_creates_candidate(self, promoter: StrategyPromoter) -> None:
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"), score=1.5)
        candidates = promoter.get_candidates()
        assert "strat_a" in candidates

    def test_duplicate_submit_is_skipped(self, promoter: StrategyPromoter) -> None:
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"), score=1.0)
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"), score=2.0)
        candidates = promoter.get_candidates()
        assert candidates.count("strat_a") == 1

    def test_retired_strategy_can_be_resubmitted(self, promoter: StrategyPromoter) -> None:
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"))
        promoter.retire("strat_a", reason="outdated")
        # Re-submit after retirement.
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"), score=3.0)
        candidates = promoter.get_candidates()
        assert "strat_a" in candidates


class TestStartTesting:
    def test_start_testing_transitions_status(self, promoter: StrategyPromoter) -> None:
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"))
        assert promoter.start_testing("strat_a") is True
        assert "strat_a" in promoter.get_paper_testing()
        assert "strat_a" not in promoter.get_candidates()

    def test_start_testing_fails_for_non_candidate(self, promoter: StrategyPromoter) -> None:
        assert promoter.start_testing("nonexistent") is False


class TestRecordSignals:
    def test_signal_count_increments(self, promoter: StrategyPromoter) -> None:
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"))
        promoter.start_testing("strat_a")
        promoter.record_signals("strat_a", count=3)
        promoter.record_signals("strat_a", count=2)
        # Verify via direct DB query.
        with sqlite3.connect(str(promoter._db_path)) as conn:
            row = conn.execute(
                "SELECT signals_generated FROM strategy_promotion WHERE spec_name = ?",
                ("strat_a",),
            ).fetchone()
        assert row is not None
        assert row[0] == 5


class TestCheckReadyForPromotion:
    def test_not_ready_too_early(self, promoter: StrategyPromoter) -> None:
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"))
        promoter.start_testing("strat_a")
        promoter.record_signals("strat_a", count=5)
        # Just started testing — not enough days elapsed.
        ready = promoter.check_ready_for_promotion(testing_days=5, min_signals=1)
        assert "strat_a" not in ready

    def test_not_ready_too_few_signals(self, promoter: StrategyPromoter) -> None:
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"))
        promoter.start_testing("strat_a")
        # Backdate testing_started_at to 10 days ago.
        past = (datetime.now(tz=timezone.utc) - timedelta(days=10)).isoformat()
        with sqlite3.connect(str(promoter._db_path)) as conn:
            conn.execute(
                "UPDATE strategy_promotion SET testing_started_at = ? WHERE spec_name = ?",
                (past, "strat_a"),
            )
        # No signals recorded.
        ready = promoter.check_ready_for_promotion(testing_days=5, min_signals=1)
        assert "strat_a" not in ready

    def test_ready_when_criteria_met(self, promoter: StrategyPromoter) -> None:
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"))
        promoter.start_testing("strat_a")
        promoter.record_signals("strat_a", count=3)
        # Backdate testing_started_at.
        past = (datetime.now(tz=timezone.utc) - timedelta(days=6)).isoformat()
        with sqlite3.connect(str(promoter._db_path)) as conn:
            conn.execute(
                "UPDATE strategy_promotion SET testing_started_at = ? WHERE spec_name = ?",
                (past, "strat_a"),
            )
        ready = promoter.check_ready_for_promotion(testing_days=5, min_signals=1)
        assert "strat_a" in ready


class TestPromote:
    def test_promote_succeeds(self, promoter: StrategyPromoter) -> None:
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"))
        promoter.start_testing("strat_a")
        assert promoter.promote("strat_a") is True
        assert "strat_a" not in promoter.get_paper_testing()

    def test_promote_fails_for_non_testing(self, promoter: StrategyPromoter) -> None:
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"))
        # Still a candidate, not in paper_testing.
        assert promoter.promote("strat_a") is False


class TestRetire:
    def test_retire_from_promoted(self, promoter: StrategyPromoter) -> None:
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"))
        promoter.start_testing("strat_a")
        promoter.promote("strat_a")
        assert promoter.retire("strat_a", reason="underperforming") is True
        # No longer in promoted list.
        promoted = promoter.get_promoted()
        assert all(s.get("name") != "strat_a" for s in promoted)

    def test_retire_from_candidate(self, promoter: StrategyPromoter) -> None:
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"))
        assert promoter.retire("strat_a") is True

    def test_retire_already_retired(self, promoter: StrategyPromoter) -> None:
        promoter.submit_candidate("strat_a", _make_spec_json("strat_a"))
        promoter.retire("strat_a")
        # Second retire should fail.
        assert promoter.retire("strat_a") is False


class TestGetPromoted:
    def test_returns_promoted_specs(self, promoter: StrategyPromoter) -> None:
        spec_json = _make_spec_json("strat_a")
        promoter.submit_candidate("strat_a", spec_json, score=2.0)
        promoter.start_testing("strat_a")
        promoter.promote("strat_a")
        promoted = promoter.get_promoted()
        assert len(promoted) == 1
        assert promoted[0]["name"] == "strat_a"

    def test_empty_when_none_promoted(self, promoter: StrategyPromoter) -> None:
        assert promoter.get_promoted() == []


class TestFullLifecycle:
    def test_submit_test_promote_retire(self, promoter: StrategyPromoter) -> None:
        """Full lifecycle: candidate → paper_testing → promoted → retired."""
        spec_json = _make_spec_json("lifecycle")
        promoter.submit_candidate("lifecycle", spec_json, score=1.0)
        assert "lifecycle" in promoter.get_candidates()

        promoter.start_testing("lifecycle")
        assert "lifecycle" in promoter.get_paper_testing()
        assert "lifecycle" not in promoter.get_candidates()

        promoter.record_signals("lifecycle", count=5)
        promoter.promote("lifecycle")
        promoted = promoter.get_promoted()
        assert any(s["name"] == "lifecycle" for s in promoted)
        assert "lifecycle" not in promoter.get_paper_testing()

        promoter.retire("lifecycle", reason="replaced by better strategy")
        promoted = promoter.get_promoted()
        assert not any(s.get("name") == "lifecycle" for s in promoted)

    def test_multiple_strategies_independent(self, promoter: StrategyPromoter) -> None:
        """Multiple strategies progress independently."""
        promoter.submit_candidate("a", _make_spec_json("a"), score=1.0)
        promoter.submit_candidate("b", _make_spec_json("b"), score=2.0)
        promoter.submit_candidate("c", _make_spec_json("c"), score=0.5)

        promoter.start_testing("a")
        promoter.start_testing("b")
        # c stays as candidate.

        promoter.promote("a")

        assert promoter.get_candidates() == ["c"]
        assert promoter.get_paper_testing() == ["b"]
        promoted = promoter.get_promoted()
        assert len(promoted) == 1
        assert promoted[0]["name"] == "a"
