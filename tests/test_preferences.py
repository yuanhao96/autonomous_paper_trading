"""Tests for core.preferences — loading and validating preferences YAML."""

from __future__ import annotations

import textwrap
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from core.preferences import Preferences, load_preferences

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "prefs.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


_VALID_YAML = """\
risk_tolerance: moderate
max_drawdown_pct: 15
trading_horizon: swing
target_annual_return_pct: 20
allowed_asset_classes:
  - us_equities
max_position_pct: 10
max_daily_loss_pct: 3
max_sector_concentration_pct: 30
evolution_permissions:
  modify_strategies: true
  modify_backtester: true
  modify_indicators: true
  modify_risk_engine: false
  modify_ui: true
  modify_core_agent: false
"""


# ---------------------------------------------------------------------------
# Tests — happy path
# ---------------------------------------------------------------------------


class TestLoadPreferences:
    def test_load_valid_yaml(self, sample_preferences_yaml: Path) -> None:
        prefs = load_preferences(sample_preferences_yaml)

        assert isinstance(prefs, Preferences)
        assert prefs.risk_tolerance == "moderate"
        assert prefs.max_drawdown_pct == 15.0
        assert prefs.trading_horizon == "swing"
        assert prefs.target_annual_return_pct == 20.0
        assert prefs.allowed_asset_classes == ["us_equities"]
        assert prefs.max_position_pct == 10.0
        assert prefs.max_daily_loss_pct == 3.0
        assert prefs.max_sector_concentration_pct == 30.0
        assert prefs.evolution_permissions["modify_strategies"] is True
        assert prefs.evolution_permissions["modify_risk_engine"] is False

    def test_all_risk_tolerances(self, tmp_path: Path) -> None:
        for tolerance in ("conservative", "moderate", "aggressive"):
            yaml_str = _VALID_YAML.replace(
                "risk_tolerance: moderate",
                f"risk_tolerance: {tolerance}",
            )
            d = tmp_path / tolerance
            d.mkdir(exist_ok=True)
            p = d / "prefs.yaml"
            p.write_text(textwrap.dedent(yaml_str), encoding="utf-8")
            prefs = load_preferences(p)
            assert prefs.risk_tolerance == tolerance

    def test_all_trading_horizons(self, tmp_path: Path) -> None:
        for horizon in ("intraday", "swing", "position"):
            yaml_str = _VALID_YAML.replace("trading_horizon: swing", f"trading_horizon: {horizon}")
            d = tmp_path / horizon
            d.mkdir(exist_ok=True)
            p = d / "prefs.yaml"
            p.write_text(textwrap.dedent(yaml_str), encoding="utf-8")
            prefs = load_preferences(p)
            assert prefs.trading_horizon == horizon


# ---------------------------------------------------------------------------
# Tests — validation errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_invalid_risk_tolerance(self, tmp_path: Path) -> None:
        yaml_str = _VALID_YAML.replace("risk_tolerance: moderate", "risk_tolerance: reckless")
        p = _write_yaml(tmp_path, yaml_str)
        with pytest.raises(ValueError, match="risk_tolerance"):
            load_preferences(p)

    def test_max_drawdown_out_of_range(self, tmp_path: Path) -> None:
        yaml_str = _VALID_YAML.replace("max_drawdown_pct: 15", "max_drawdown_pct: 150")
        p = _write_yaml(tmp_path, yaml_str)
        with pytest.raises(ValueError, match="max_drawdown_pct"):
            load_preferences(p)

    def test_negative_percentage(self, tmp_path: Path) -> None:
        yaml_str = _VALID_YAML.replace("max_position_pct: 10", "max_position_pct: -5")
        p = _write_yaml(tmp_path, yaml_str)
        with pytest.raises(ValueError, match="max_position_pct"):
            load_preferences(p)

    def test_missing_field(self, tmp_path: Path) -> None:
        # Remove max_daily_loss_pct line entirely.
        lines = [
            line for line in _VALID_YAML.splitlines(True)
            if "max_daily_loss_pct" not in line
        ]
        p = _write_yaml(tmp_path, "".join(lines))
        with pytest.raises(ValueError, match="Missing preference fields"):
            load_preferences(p)

    def test_unknown_field(self, tmp_path: Path) -> None:
        yaml_str = _VALID_YAML + "some_unknown_field: 42\n"
        p = _write_yaml(tmp_path, yaml_str)
        with pytest.raises(ValueError, match="Unknown preference fields"):
            load_preferences(p)

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_preferences(tmp_path / "nonexistent.yaml")


# ---------------------------------------------------------------------------
# Tests — immutability
# ---------------------------------------------------------------------------


class TestImmutability:
    def test_preferences_is_frozen(self, sample_preferences_yaml: Path) -> None:
        prefs = load_preferences(sample_preferences_yaml)
        with pytest.raises(FrozenInstanceError):
            prefs.risk_tolerance = "aggressive"  # type: ignore[misc]

    def test_cannot_set_new_attribute(self, sample_preferences_yaml: Path) -> None:
        prefs = load_preferences(sample_preferences_yaml)
        with pytest.raises(FrozenInstanceError):
            prefs.new_attr = "value"  # type: ignore[attr-defined]
