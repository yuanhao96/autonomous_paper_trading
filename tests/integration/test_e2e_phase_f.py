"""End-to-end integration tests for Phase F — expanded templates + scheduler.

Verifies:
  1. All 46 templates can be translated and produce strategies
  2. All 46 signal map entries work with realistic data
  3. Generator SUPPORTED_TEMPLATES list is consistent with translator
  4. Scheduler creates and manages jobs correctly
  5. Full pipeline roundtrip with new templates
"""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.agent.generator import SUPPORTED_TEMPLATES
from src.live.signals import compute_signals
from src.screening.translator import translate
from src.strategies.spec import RiskParams, StrategySpec


def _make_price_data(symbols: list[str], n: int = 300) -> dict[str, pd.DataFrame]:
    """Create realistic OHLCV data for multiple symbols."""
    result = {}
    for i, sym in enumerate(symbols):
        rng = np.random.default_rng(42 + i)
        close = 100.0 + np.cumsum(rng.normal(0.05, 1.0, n))
        close = np.maximum(close, 10.0)
        idx = pd.date_range("2020-01-01", periods=n, freq="B")
        result[sym] = pd.DataFrame({
            "Open": close * 0.995,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": rng.integers(100_000, 5_000_000, n),
        }, index=idx)
    return result


class TestE2EAllTemplatesTranslate:
    """Every SUPPORTED_TEMPLATE must translate without error."""

    def test_all_46_templates_translate(self):
        """Iterate all 46 templates and verify translate() succeeds."""
        failures = []
        for template in SUPPORTED_TEMPLATES:
            slug = template.split("/", 1)[1]
            spec = StrategySpec(
                template=f"test/{slug}",
                parameters={},
                universe_id="test",
            )
            try:
                data = _make_price_data(["SPY"], n=300)["SPY"]
                cls = translate(spec, data)
                assert cls is not None
            except Exception as e:
                failures.append(f"{template}: {e}")

        assert not failures, f"Failed templates:\n" + "\n".join(failures)


class TestE2EAllTemplatesSignal:
    """Every SUPPORTED_TEMPLATE must produce a valid signal."""

    def test_all_46_templates_signal(self):
        """Iterate all 46 templates and verify signals are 'long' or 'flat'."""
        prices = _make_price_data(["SPY", "QQQ"], n=300)
        failures = []
        for template in SUPPORTED_TEMPLATES:
            slug = template.split("/", 1)[1]
            spec = StrategySpec(
                template=f"test/{slug}",
                parameters={},
                universe_id="test",
            )
            try:
                signals = compute_signals(spec, prices, lookback_bars=10)
                for sym, sig in signals.items():
                    if sig not in ("long", "flat"):
                        failures.append(f"{template}/{sym}: got '{sig}'")
            except Exception as e:
                failures.append(f"{template}: {e}")

        assert not failures, f"Failed signals:\n" + "\n".join(failures)


class TestE2EGeneratorConsistency:
    """Generator list must match translator+signal registries."""

    def test_template_count_is_46(self):
        assert len(SUPPORTED_TEMPLATES) == 46

    def test_no_duplicates(self):
        assert len(SUPPORTED_TEMPLATES) == len(set(SUPPORTED_TEMPLATES))

    def test_all_categories_present(self):
        categories = {t.split("/")[0] for t in SUPPORTED_TEMPLATES}
        expected = {"momentum", "mean-reversion", "technical", "factor",
                    "value", "calendar", "volatility", "forex", "commodities"}
        assert expected.issubset(categories)


class TestE2EScheduler:
    """Integration test for scheduler module."""

    def test_scheduler_lifecycle(self):
        from src.scheduler import SimpleScheduler, ScheduleConfig

        sched = SimpleScheduler()
        sched.add_job(ScheduleConfig(name="j1", func=lambda: None, hour=9, minute=30))
        sched.add_job(ScheduleConfig(name="j2", func=lambda: None, hour=16, minute=15))
        sched.add_job(ScheduleConfig(name="j3", func=lambda: None, hour=8, minute=0, days_of_week="sat"))

        assert sched.job_count == 3

        sched.start(blocking=False)
        assert sched.is_running

        sched.stop()
        assert not sched.is_running


class TestE2ECLIScheduleCommand:
    """Verify the schedule command is registered in the CLI."""

    def test_schedule_help(self):
        result = subprocess.run(
            [sys.executable, "main.py", "schedule", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "--cycles" in result.stdout
        assert "--universe" in result.stdout

    def test_info_shows_expanded_templates(self):
        """Info command should show new templates like fama-french."""
        result = subprocess.run(
            [sys.executable, "main.py", "info"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "fama-french" in result.stdout
        assert "turn-of-the-month" in result.stdout
        assert "volatility-risk-premium" in result.stdout
        assert "momentum_screen" in result.stdout


class TestE2ENewTemplateBacktest:
    """Spot-check that new templates produce runnable strategies."""

    def test_ichimoku_strategy_runs(self):
        spec = StrategySpec(
            template="technical/ichimoku-clouds-in-energy-sector",
            parameters={"tenkan": 9, "kijun": 26},
            universe_id="test",
        )
        prices = _make_price_data(["XLE"], n=100)
        cls = translate(spec, prices["XLE"])
        assert cls is not None
        signals = compute_signals(spec, prices, lookback_bars=10)
        assert signals["XLE"] in ("long", "flat")

    def test_calendar_turn_of_month_runs(self):
        spec = StrategySpec(
            template="calendar/turn-of-the-month-in-equity-indexes",
            parameters={"entry_day": -2, "exit_day": 3},
            universe_id="test",
        )
        prices = _make_price_data(["SPY"], n=60)
        cls = translate(spec, prices["SPY"])
        assert cls is not None
        signals = compute_signals(spec, prices, lookback_bars=5)
        assert signals["SPY"] in ("long", "flat")

    def test_factor_fama_french_runs(self):
        spec = StrategySpec(
            template="factor/fama-french-five-factors",
            parameters={"lookback": 126},
            universe_id="test",
        )
        prices = _make_price_data(["AAPL", "MSFT"], n=200)
        cls = translate(spec, prices["AAPL"])
        assert cls is not None
        signals = compute_signals(spec, prices, lookback_bars=10)
        assert all(s in ("long", "flat") for s in signals.values())
