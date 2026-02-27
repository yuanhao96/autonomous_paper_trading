"""Scheduler — automated daily/periodic pipeline execution.

Uses APScheduler (if installed) or a simple threading-based fallback
to run the trading pipeline on a configurable schedule.

Usage:
    from src.scheduler import TradingScheduler
    scheduler = TradingScheduler()
    scheduler.start()   # Blocks until Ctrl-C
"""

from __future__ import annotations

import logging
import signal
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ScheduleConfig:
    """Configuration for a scheduled job."""

    name: str
    func: Callable[..., Any]
    kwargs: dict[str, Any] = field(default_factory=dict)
    # Cron-like schedule
    hour: int = 9
    minute: int = 30
    days_of_week: str = "mon-fri"  # "mon-fri", "daily", or "mon,wed,fri"
    enabled: bool = True


def _parse_days(days_of_week: str) -> set[int]:
    """Parse days_of_week string to set of weekday ints (0=Monday)."""
    day_map = {
        "mon": 0, "tue": 1, "wed": 2, "thu": 3,
        "fri": 4, "sat": 5, "sun": 6,
    }
    if days_of_week == "daily":
        return {0, 1, 2, 3, 4, 5, 6}
    if days_of_week == "mon-fri":
        return {0, 1, 2, 3, 4}

    result = set()
    for part in days_of_week.split(","):
        part = part.strip().lower()
        if "-" in part:
            start, end = part.split("-", 1)
            s = day_map.get(start[:3], -1)
            e = day_map.get(end[:3], -1)
            if s >= 0 and e >= 0:
                while s != (e + 1) % 7:
                    result.add(s)
                    s = (s + 1) % 7
                result.add(e)
        elif part[:3] in day_map:
            result.add(day_map[part[:3]])
    return result or {0, 1, 2, 3, 4}


class SimpleScheduler:
    """Lightweight scheduler that checks once per minute and fires jobs.

    Does not require APScheduler — uses only stdlib threading.
    """

    def __init__(self) -> None:
        self._jobs: list[ScheduleConfig] = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_run: dict[str, str] = {}  # job_name → "YYYY-MM-DD HH:MM"

    def add_job(self, config: ScheduleConfig) -> None:
        """Register a scheduled job."""
        self._jobs.append(config)
        logger.info(
            "Scheduled job '%s' at %02d:%02d on %s",
            config.name, config.hour, config.minute, config.days_of_week,
        )

    def _should_run(self, job: ScheduleConfig, now: datetime) -> bool:
        """Check if job should fire at the current time."""
        if not job.enabled:
            return False
        allowed_days = _parse_days(job.days_of_week)
        if now.weekday() not in allowed_days:
            return False
        if now.hour != job.hour or now.minute != job.minute:
            return False
        # Prevent double-fire within the same minute
        key = f"{now.strftime('%Y-%m-%d %H:%M')}"
        if self._last_run.get(job.name) == key:
            return False
        return True

    def _run_job(self, job: ScheduleConfig) -> None:
        """Execute a job with error handling."""
        now = datetime.now()
        key = now.strftime("%Y-%m-%d %H:%M")
        self._last_run[job.name] = key
        logger.info("Running scheduled job: %s", job.name)
        try:
            job.func(**job.kwargs)
            logger.info("Job '%s' completed successfully", job.name)
        except Exception as e:
            logger.error("Job '%s' failed: %s", job.name, e, exc_info=True)

    def _loop(self) -> None:
        """Main scheduling loop — checks every 30 seconds."""
        while not self._stop_event.is_set():
            now = datetime.now()
            for job in self._jobs:
                if self._should_run(job, now):
                    self._run_job(job)
            self._stop_event.wait(30)

    def start(self, blocking: bool = True) -> None:
        """Start the scheduler.

        Args:
            blocking: If True, blocks the calling thread. If False, runs
                      in a background daemon thread.
        """
        logger.info("Starting scheduler with %d jobs", len(self._jobs))
        if blocking:
            self._loop()
        else:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        logger.info("Stopping scheduler")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    @property
    def is_running(self) -> bool:
        return not self._stop_event.is_set()

    @property
    def job_count(self) -> int:
        return len(self._jobs)

    def get_status(self) -> str:
        """Return a human-readable status string."""
        lines = [f"Scheduler: {'running' if self.is_running else 'stopped'}"]
        lines.append(f"Jobs: {len(self._jobs)}")
        for job in self._jobs:
            status = "enabled" if job.enabled else "disabled"
            last = self._last_run.get(job.name, "never")
            lines.append(
                f"  {job.name}: {job.hour:02d}:{job.minute:02d} "
                f"{job.days_of_week} [{status}] (last: {last})"
            )
        return "\n".join(lines)


class TradingScheduler:
    """Pre-configured scheduler for the autonomous trading pipeline.

    Default schedule:
      - 09:30 Mon-Fri: Run full pipeline cycle (generate, screen, validate)
      - 16:15 Mon-Fri: Monitor live deployments
      - 08:00 Saturday: Weekly evolution run
    """

    def __init__(
        self,
        universe_id: str = "sector_etfs",
        cycles: int = 3,
        computation: str | None = None,
        computation_params: dict[str, Any] | None = None,
    ) -> None:
        from src.orchestrator import Orchestrator

        self._orch = Orchestrator(
            universe_id=universe_id,
            computation=computation,
            computation_params=computation_params,
        )
        self._cycles = cycles
        self._scheduler = SimpleScheduler()
        self._setup_jobs()

    def _setup_jobs(self) -> None:
        """Configure default trading schedule."""
        # Morning: run pipeline
        self._scheduler.add_job(ScheduleConfig(
            name="daily_pipeline",
            func=self._run_pipeline,
            hour=9, minute=30,
            days_of_week="mon-fri",
        ))

        # Afternoon: monitor deployments
        self._scheduler.add_job(ScheduleConfig(
            name="daily_monitor",
            func=self._run_monitor,
            hour=16, minute=15,
            days_of_week="mon-fri",
        ))

        # Weekly evolution
        self._scheduler.add_job(ScheduleConfig(
            name="weekly_evolution",
            func=self._run_evolution,
            hour=8, minute=0,
            days_of_week="sat",
        ))

    def _run_pipeline(self) -> None:
        """Execute the daily pipeline cycle."""
        logger.info("=== Daily Pipeline Run ===")
        result = self._orch.run_full_cycle(cycles=self._cycles)
        logger.info("Pipeline: %s", result.summary())

    def _run_monitor(self) -> None:
        """Monitor all active deployments."""
        logger.info("=== Daily Monitoring ===")
        status = self._orch.get_pipeline_status()
        logger.info("\n%s", status)

    def _run_evolution(self) -> None:
        """Run weekly evolution."""
        logger.info("=== Weekly Evolution ===")
        result = self._orch.run_evolution(n_cycles=5)
        logger.info("Evolution: %s", result.summary())

    def start(self, blocking: bool = True) -> None:
        """Start the trading scheduler."""
        logger.info("Trading scheduler starting")
        logger.info("\n%s", self._scheduler.get_status())

        if blocking:
            # Handle Ctrl-C gracefully
            def _handler(signum, frame):
                logger.info("Received signal %s, shutting down...", signum)
                self._scheduler.stop()

            signal.signal(signal.SIGINT, _handler)
            signal.signal(signal.SIGTERM, _handler)

        self._scheduler.start(blocking=blocking)

    def stop(self) -> None:
        self._scheduler.stop()

    @property
    def scheduler(self) -> SimpleScheduler:
        return self._scheduler
