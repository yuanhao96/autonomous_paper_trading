"""Tests for configuration loading."""

import pytest

from src.core.config import PROJECT_ROOT, Preferences, Settings, load_preferences


class TestProjectRoot:
    def test_project_root_exists(self):
        assert (PROJECT_ROOT / "pyproject.toml").exists()

    def test_config_dir_exists(self):
        assert (PROJECT_ROOT / "config").is_dir()


class TestPreferences:
    def test_load_preferences(self):
        prefs = load_preferences()
        assert isinstance(prefs, Preferences)
        assert prefs.risk_limits.max_position_pct > 0
        assert prefs.risk_limits.max_portfolio_drawdown > 0
        assert len(prefs.allowed_asset_classes) > 0

    def test_preferences_immutable(self):
        prefs = load_preferences()
        with pytest.raises(AttributeError):
            prefs.audit_gate_enabled = False  # type: ignore[misc]

    def test_risk_limits_immutable(self):
        prefs = load_preferences()
        with pytest.raises(AttributeError):
            prefs.risk_limits.max_position_pct = 1.0  # type: ignore[misc]


class TestSettings:
    def test_load_settings(self):
        s = Settings()
        assert s.get("screening.initial_cash") == 100000

    def test_dotted_key_access(self):
        s = Settings()
        assert s.get("screening.pass_criteria.min_sharpe") == 0.5

    def test_missing_key_default(self):
        s = Settings()
        assert s.get("nonexistent.key", 42) == 42

    def test_cache_dir(self):
        s = Settings()
        cache_dir = s.cache_dir
        assert cache_dir.exists()
