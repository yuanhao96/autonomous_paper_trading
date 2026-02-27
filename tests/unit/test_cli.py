"""Tests for the CLI entry point."""

from __future__ import annotations

import subprocess
import sys

import pytest


class TestCLI:
    def test_help_flag(self):
        """CLI --help should exit successfully."""
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "autonomous-trader" in result.stdout

    def test_info_command(self):
        """CLI info command should show templates and universes."""
        result = subprocess.run(
            [sys.executable, "main.py", "info"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "momentum" in result.stdout
        assert "sector_etfs" in result.stdout
        assert "momentum_screen" in result.stdout

    def test_no_command_shows_help(self):
        """Running without a command should show help."""
        result = subprocess.run(
            [sys.executable, "main.py"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0

    def test_run_help(self):
        """CLI run --help should show run options."""
        result = subprocess.run(
            [sys.executable, "main.py", "run", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "--cycles" in result.stdout
        assert "--universe" in result.stdout
