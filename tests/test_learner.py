"""Unit tests for stratgen.learner module."""

import json
from pathlib import Path

from stratgen.learner import load_previous_runs, log_run


class TestLogRun:
    def test_creates_directory(self, tmp_path: Path):
        run_dir = tmp_path / "test-run"
        summary = {"mean_abs_ic": 0.015, "n_positions": 20}
        result = log_run(summary, run_dir=run_dir)

        assert result == run_dir
        assert run_dir.exists()
        assert (run_dir / "summary.json").exists()

    def test_summary_content(self, tmp_path: Path):
        run_dir = tmp_path / "test-run"
        summary = {"mean_abs_ic": 0.015, "timestamp": "2026-03-11T10:00:00"}
        log_run(summary, run_dir=run_dir)

        with open(run_dir / "summary.json") as f:
            saved = json.load(f)

        assert saved["mean_abs_ic"] == 0.015
        assert saved["timestamp"] == "2026-03-11T10:00:00"

    def test_copies_result_files(self, tmp_path: Path, monkeypatch):
        # Create fake result files
        import stratgen.learner as learner_mod
        fake_screen = tmp_path / "results_screen.json"
        fake_screen.write_text('{"n_passed": 300}')
        monkeypatch.setattr(learner_mod, "RESULTS_SCREEN", fake_screen)

        run_dir = tmp_path / "run-001"
        log_run({"test": True}, run_dir=run_dir)

        assert (run_dir / "results_screen.json").exists()


class TestLoadPreviousRuns:
    def test_empty_when_no_runs(self, tmp_path: Path, monkeypatch):
        import stratgen.learner as learner_mod
        monkeypatch.setattr(learner_mod, "RUNS_DIR", tmp_path / "nonexistent")
        assert load_previous_runs() == []

    def test_loads_sorted(self, tmp_path: Path, monkeypatch):
        import stratgen.learner as learner_mod
        monkeypatch.setattr(learner_mod, "RUNS_DIR", tmp_path)

        # Create two runs
        for name, ic in [("2026-03-11-100000", 0.01), ("2026-03-11-110000", 0.02)]:
            d = tmp_path / name
            d.mkdir()
            with open(d / "summary.json", "w") as f:
                json.dump({"mean_abs_ic": ic}, f)

        runs = load_previous_runs()
        assert len(runs) == 2
        assert runs[0]["mean_abs_ic"] == 0.01  # oldest first
        assert runs[1]["mean_abs_ic"] == 0.02
