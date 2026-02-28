"""Tests for the scheduler module."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from src.scheduler import (
    ScheduleConfig,
    SimpleScheduler,
    TradingScheduler,
    _parse_days,
)


class TestParseDays:
    def test_mon_fri(self):
        assert _parse_days("mon-fri") == {0, 1, 2, 3, 4}

    def test_daily(self):
        assert _parse_days("daily") == {0, 1, 2, 3, 4, 5, 6}

    def test_specific_days(self):
        assert _parse_days("mon,wed,fri") == {0, 2, 4}

    def test_range(self):
        assert _parse_days("tue-thu") == {1, 2, 3}

    def test_sat(self):
        result = _parse_days("sat")
        assert 5 in result

    def test_invalid_fallback(self):
        result = _parse_days("xyz")
        assert result == {0, 1, 2, 3, 4}  # fallback to mon-fri


class TestScheduleConfig:
    def test_default_schedule(self):
        config = ScheduleConfig(name="test", func=lambda: None)
        assert config.hour == 9
        assert config.minute == 30
        assert config.days_of_week == "mon-fri"
        assert config.enabled is True

    def test_custom_schedule(self):
        config = ScheduleConfig(
            name="custom", func=lambda: None,
            hour=16, minute=0, days_of_week="daily",
        )
        assert config.hour == 16
        assert config.days_of_week == "daily"


class TestSimpleScheduler:
    def test_add_job(self):
        sched = SimpleScheduler()
        sched.add_job(ScheduleConfig(name="j1", func=lambda: None))
        assert sched.job_count == 1

    def test_add_multiple_jobs(self):
        sched = SimpleScheduler()
        sched.add_job(ScheduleConfig(name="j1", func=lambda: None))
        sched.add_job(ScheduleConfig(name="j2", func=lambda: None))
        assert sched.job_count == 2

    def test_get_status(self):
        sched = SimpleScheduler()
        sched.add_job(ScheduleConfig(name="test_job", func=lambda: None, hour=10, minute=0))
        status = sched.get_status()
        assert "test_job" in status
        assert "10:00" in status

    def test_should_run_matching_time(self):
        sched = SimpleScheduler()
        job = ScheduleConfig(name="test", func=lambda: None, hour=9, minute=30)
        sched.add_job(job)
        now = datetime(2024, 1, 15, 9, 30)  # Monday 09:30
        assert sched._should_run(job, now) is True

    def test_should_not_run_wrong_time(self):
        sched = SimpleScheduler()
        job = ScheduleConfig(name="test", func=lambda: None, hour=9, minute=30)
        sched.add_job(job)
        now = datetime(2024, 1, 15, 10, 0)  # Monday 10:00
        assert sched._should_run(job, now) is False

    def test_should_not_run_wrong_day(self):
        sched = SimpleScheduler()
        job = ScheduleConfig(
            name="test", func=lambda: None, hour=9, minute=30, days_of_week="mon-fri",
        )
        sched.add_job(job)
        now = datetime(2024, 1, 13, 9, 30)  # Saturday 09:30
        assert sched._should_run(job, now) is False

    def test_should_not_run_disabled(self):
        sched = SimpleScheduler()
        job = ScheduleConfig(name="test", func=lambda: None, hour=9, minute=30, enabled=False)
        sched.add_job(job)
        now = datetime(2024, 1, 15, 9, 30)
        assert sched._should_run(job, now) is False

    def test_no_double_fire(self):
        sched = SimpleScheduler()
        job = ScheduleConfig(name="test", func=lambda: None, hour=9, minute=30)
        sched.add_job(job)
        now = datetime(2024, 1, 15, 9, 30)
        assert sched._should_run(job, now) is True
        # Simulate the run by recording the last_run key manually
        sched._last_run[job.name] = now.strftime("%Y-%m-%d %H:%M")
        assert sched._should_run(job, now) is False

    def test_run_job_success(self):
        callback = MagicMock()
        sched = SimpleScheduler()
        job = ScheduleConfig(name="test", func=callback, kwargs={"a": 1})
        sched._run_job(job)
        callback.assert_called_once_with(a=1)

    def test_run_job_error_handled(self):
        def bad_func():
            raise RuntimeError("boom")
        sched = SimpleScheduler()
        job = ScheduleConfig(name="test", func=bad_func)
        # Should not raise
        sched._run_job(job)

    def test_start_stop_nonblocking(self):
        sched = SimpleScheduler()
        sched.add_job(ScheduleConfig(name="test", func=lambda: None))
        sched.start(blocking=False)
        assert sched.is_running
        sched.stop()
        assert not sched.is_running


class TestTradingScheduler:
    @patch("src.orchestrator.Orchestrator")
    def test_creates_default_jobs(self, mock_orch_cls):
        sched = TradingScheduler()
        assert sched.scheduler.job_count == 4

    @patch("src.orchestrator.Orchestrator")
    def test_status(self, mock_orch_cls):
        sched = TradingScheduler()
        status = sched.scheduler.get_status()
        assert "daily_pipeline" in status
        assert "daily_monitor" in status
        assert "weekly_evolution" in status
        assert "daily_rebalance" in status

    @patch("src.orchestrator.Orchestrator")
    def test_start_stop(self, mock_orch_cls):
        sched = TradingScheduler()
        sched.start(blocking=False)
        assert sched.scheduler.is_running
        sched.stop()
        assert not sched.scheduler.is_running

    @patch("src.orchestrator.Orchestrator")
    def test_custom_params(self, mock_orch_cls):
        sched = TradingScheduler(
            universe_id="sp500",
            cycles=5,
            computation="momentum_screen",
        )
        mock_orch_cls.assert_called_once_with(universe_id="sp500")
        assert sched._cycles == 5
        assert sched._computation == "momentum_screen"
        assert sched._computation_params is None

    @patch("src.orchestrator.Orchestrator")
    def test_run_pipeline_passes_correct_kwargs(self, mock_orch_cls):
        mock_orch = mock_orch_cls.return_value
        mock_result = MagicMock()
        mock_orch.run_full_cycle.return_value = mock_result

        sched = TradingScheduler(
            universe_id="sector_etfs",
            cycles=3,
            computation="vol_screen",
            computation_params={"min_vol": 0.2},
        )
        sched._run_pipeline()

        mock_orch.run_full_cycle.assert_called_once_with(
            n_evolution_cycles=3,
            computation="vol_screen",
            computation_params={"min_vol": 0.2},
        )

    @patch("src.orchestrator.Orchestrator")
    def test_run_evolution_iterates_results(self, mock_orch_cls):
        """Bug #1: run_evolution returns list[CycleResult], not a single result."""
        mock_orch = mock_orch_cls.return_value
        mock_cycle = MagicMock()
        mock_cycle.summary.return_value = "cycle summary"
        mock_orch.run_evolution.return_value = [mock_cycle]

        sched = TradingScheduler()
        sched._run_evolution()

        mock_orch.run_evolution.assert_called_once_with(n_cycles=5)
        mock_cycle.summary.assert_called_once()

    @patch("src.orchestrator.Orchestrator")
    def test_rebalance_job_present(self, mock_orch_cls):
        """Verify daily_rebalance job appears in scheduler status."""
        sched = TradingScheduler()
        status = sched.scheduler.get_status()
        assert "daily_rebalance" in status
        assert "10:00" in status

    @patch("src.orchestrator.Orchestrator")
    def test_run_rebalance_calls_orchestrator(self, mock_orch_cls):
        mock_orch = mock_orch_cls.return_value
        mock_orch.run_rebalance.return_value = []

        sched = TradingScheduler()
        sched._run_rebalance()

        mock_orch.run_rebalance.assert_called_once()
