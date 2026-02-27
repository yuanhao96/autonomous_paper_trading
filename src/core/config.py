"""Configuration loading — settings.yaml (mutable) and preferences.yaml (immutable)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def _find_project_root() -> Path:
    """Walk up from this file to find the project root (contains pyproject.toml)."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (no pyproject.toml found)")


PROJECT_ROOT = _find_project_root()
CONFIG_DIR = PROJECT_ROOT / "config"


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and return as dict."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if data else {}


@dataclass(frozen=True)
class RiskLimits:
    """Immutable risk limits from preferences.yaml. Cannot be changed at runtime."""

    max_position_pct: float
    max_portfolio_drawdown: float
    max_daily_loss: float
    max_leverage: float
    max_positions: int
    min_cash_reserve_pct: float


@dataclass(frozen=True)
class Preferences:
    """Human-controlled preferences. Frozen — the system cannot modify these."""

    risk_limits: RiskLimits
    allowed_asset_classes: tuple[str, ...]
    audit_gate_enabled: bool
    min_paper_trading_days: int


def load_preferences(path: Path | None = None) -> Preferences:
    """Load preferences.yaml — immutable risk limits and constraints."""
    if path is None:
        path = CONFIG_DIR / "preferences.yaml"
    data = load_yaml(path)
    rl = data["risk_limits"]
    return Preferences(
        risk_limits=RiskLimits(
            max_position_pct=rl["max_position_pct"],
            max_portfolio_drawdown=rl["max_portfolio_drawdown"],
            max_daily_loss=rl["max_daily_loss"],
            max_leverage=rl["max_leverage"],
            max_positions=rl["max_positions"],
            min_cash_reserve_pct=rl["min_cash_reserve_pct"],
        ),
        allowed_asset_classes=tuple(data["allowed_asset_classes"]),
        audit_gate_enabled=data["audit_gate_enabled"],
        min_paper_trading_days=data["min_paper_trading_days"],
    )


class Settings:
    """Runtime settings from settings.yaml. Mutable, reloadable."""

    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = CONFIG_DIR / "settings.yaml"
        self._data = load_yaml(path)

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Get a nested setting by dotted key, e.g., 'screening.pass_criteria.min_sharpe'."""
        keys = dotted_key.split(".")
        current: Any = self._data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    @property
    def cache_dir(self) -> Path:
        raw = self.get("data.cache_dir", "data/cache")
        path = Path(raw)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path.mkdir(parents=True, exist_ok=True)
        return path
