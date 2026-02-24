"""Preferences reader module.

Loads and validates the human-controlled preferences from config/preferences.yaml.
This file is read-only for all agents; only humans may modify the YAML source.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

import yaml

_VALID_RISK_TOLERANCES = frozenset({"conservative", "moderate", "aggressive"})
_VALID_TRADING_HORIZONS = frozenset({"intraday", "swing", "position"})
_KNOWN_EVOLUTION_PERMISSIONS = frozenset(
    {
        "modify_strategies",
        "modify_backtester",
        "modify_indicators",
        "modify_risk_engine",
        "modify_ui",
        "modify_core_agent",
    }
)

_DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "preferences.yaml",
)


@dataclass(frozen=True)
class Preferences:
    """Immutable snapshot of human-controlled trading preferences."""

    risk_tolerance: str
    max_drawdown_pct: float
    trading_horizon: str
    target_annual_return_pct: float
    allowed_asset_classes: list[str]
    max_position_pct: float
    max_daily_loss_pct: float
    max_sector_concentration_pct: float
    evolution_permissions: dict[str, bool]


def _validate_pct(name: str, value: Any) -> float:
    """Validate that a value is a number in [0, 100]."""
    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {type(value).__name__}")
    val = float(value)
    if not 0 <= val <= 100:
        raise ValueError(f"{name} must be between 0 and 100, got {val}")
    return val


def _validate(raw: dict[str, Any]) -> Preferences:
    """Validate raw YAML dict and return a Preferences instance."""
    # Check for unknown top-level keys.
    known_fields = {f.name for f in fields(Preferences)}
    unknown = set(raw.keys()) - known_fields
    if unknown:
        raise ValueError(f"Unknown preference fields: {sorted(unknown)}")

    # Check for missing keys.
    missing = known_fields - set(raw.keys())
    if missing:
        raise ValueError(f"Missing preference fields: {sorted(missing)}")

    # --- risk_tolerance ---
    risk_tolerance = raw["risk_tolerance"]
    if not isinstance(risk_tolerance, str):
        raise ValueError(
            f"risk_tolerance must be a string, got {type(risk_tolerance).__name__}"
        )
    risk_tolerance = risk_tolerance.strip().lower()
    if risk_tolerance not in _VALID_RISK_TOLERANCES:
        raise ValueError(
            f"risk_tolerance must be one of {sorted(_VALID_RISK_TOLERANCES)}, "
            f"got '{risk_tolerance}'"
        )

    # --- trading_horizon ---
    trading_horizon = raw["trading_horizon"]
    if not isinstance(trading_horizon, str):
        raise ValueError(
            f"trading_horizon must be a string, got {type(trading_horizon).__name__}"
        )
    trading_horizon = trading_horizon.strip().lower()
    if trading_horizon not in _VALID_TRADING_HORIZONS:
        raise ValueError(
            f"trading_horizon must be one of {sorted(_VALID_TRADING_HORIZONS)}, "
            f"got '{trading_horizon}'"
        )

    # --- percentage fields ---
    max_drawdown_pct = _validate_pct("max_drawdown_pct", raw["max_drawdown_pct"])
    target_annual_return_pct = _validate_pct(
        "target_annual_return_pct", raw["target_annual_return_pct"]
    )
    max_position_pct = _validate_pct("max_position_pct", raw["max_position_pct"])
    max_daily_loss_pct = _validate_pct("max_daily_loss_pct", raw["max_daily_loss_pct"])
    max_sector_concentration_pct = _validate_pct(
        "max_sector_concentration_pct", raw["max_sector_concentration_pct"]
    )

    # --- allowed_asset_classes ---
    allowed_asset_classes = raw["allowed_asset_classes"]
    if not isinstance(allowed_asset_classes, list):
        raise ValueError(
            f"allowed_asset_classes must be a list, "
            f"got {type(allowed_asset_classes).__name__}"
        )
    if len(allowed_asset_classes) == 0:
        raise ValueError("allowed_asset_classes must not be empty")
    for item in allowed_asset_classes:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"Each entry in allowed_asset_classes must be a non-empty string, "
                f"got {item!r}"
            )
    allowed_asset_classes = [s.strip().lower() for s in allowed_asset_classes]

    # --- evolution_permissions ---
    evolution_permissions = raw["evolution_permissions"]
    if not isinstance(evolution_permissions, dict):
        raise ValueError(
            f"evolution_permissions must be a dict, "
            f"got {type(evolution_permissions).__name__}"
        )
    unknown_perms = set(evolution_permissions.keys()) - _KNOWN_EVOLUTION_PERMISSIONS
    if unknown_perms:
        raise ValueError(
            f"Unknown evolution_permissions keys: {sorted(unknown_perms)}"
        )
    for key, val in evolution_permissions.items():
        if not isinstance(val, bool):
            raise ValueError(
                f"evolution_permissions['{key}'] must be a bool, "
                f"got {type(val).__name__}"
            )

    return Preferences(
        risk_tolerance=risk_tolerance,
        max_drawdown_pct=max_drawdown_pct,
        trading_horizon=trading_horizon,
        target_annual_return_pct=target_annual_return_pct,
        allowed_asset_classes=allowed_asset_classes,
        max_position_pct=max_position_pct,
        max_daily_loss_pct=max_daily_loss_pct,
        max_sector_concentration_pct=max_sector_concentration_pct,
        evolution_permissions=dict(evolution_permissions),
    )


def load_preferences(path: str | Path | None = None) -> Preferences:
    """Load and validate preferences from a YAML file.

    Parameters
    ----------
    path:
        Path to the preferences YAML file.  Defaults to
        ``<project_root>/config/preferences.yaml``.

    Returns
    -------
    Preferences
        A frozen dataclass with all validated preference values.

    Raises
    ------
    FileNotFoundError
        If the YAML file does not exist.
    ValueError
        If the YAML content is invalid or fails validation.
    """
    if path is None:
        path = _DEFAULT_PATH
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Preferences file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, dict):
        raise ValueError(
            f"preferences.yaml must contain a YAML mapping, got {type(raw).__name__}"
        )

    return _validate(raw)
