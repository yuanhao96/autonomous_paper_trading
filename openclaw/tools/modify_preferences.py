"""OpenClaw tool: modify trading preferences (human-only action).

This is the ONLY code path that writes to preferences.yaml. It is
invoked by a human via the OpenClaw helper agent, NOT by the
trading or auditor agents.

Stub — actual OpenClaw integration happens on the target machine.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
_PREFERENCES_PATH: Path = _PROJECT_ROOT / "config" / "preferences.yaml"

TOOL_SCHEMA: dict = {
    "name": "modify_preferences",
    "description": "Modify trading preferences (human-only action)",
    "parameters": {
        "key": {
            "type": "str",
            "description": (
                "The preference key to modify"
                " (e.g. 'risk_tolerance', 'max_drawdown_pct')"
            ),
            "required": True,
        },
        "value": {
            "type": "str",
            "description": "The new value for the preference key (will be parsed as YAML scalar)",
            "required": True,
        },
    },
}


def _parse_yaml_value(value_str: str) -> object:
    """Parse a string as a YAML scalar value.

    This allows the user to pass 'true', '15', '20.5', etc. and get
    the correct Python type (bool, int, float, str).
    """
    parsed = yaml.safe_load(value_str)
    return parsed


async def handle(params: dict) -> str:
    """Modify a single key in preferences.yaml.

    Reads the current file, validates the key exists, updates the value,
    and writes back. Returns a confirmation string.
    """
    key = params.get("key")
    value_str = params.get("value")

    if not key:
        return "Error: 'key' parameter is required."
    if value_str is None:
        return "Error: 'value' parameter is required."

    preferences_path = _PREFERENCES_PATH
    if not preferences_path.exists():
        return f"Error: Preferences file not found at {preferences_path}"

    try:
        with open(preferences_path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)

        if not isinstance(raw, dict):
            return "Error: preferences.yaml does not contain a valid YAML mapping."

        # Support dotted keys for nested values (e.g. "evolution_permissions.modify_strategies")
        key_parts = key.split(".")
        target = raw
        for part in key_parts[:-1]:
            if not isinstance(target, dict) or part not in target:
                return (
                    f"Error: Key path '{key}' is invalid. "
                    f"'{part}' not found in preferences."
                )
            target = target[part]

        final_key = key_parts[-1]
        if not isinstance(target, dict) or final_key not in target:
            available = sorted(target.keys()) if isinstance(target, dict) else []
            return (
                f"Error: Key '{final_key}' not found in preferences. "
                f"Available keys: {available}"
            )

        old_value = target[final_key]
        new_value = _parse_yaml_value(value_str)
        target[final_key] = new_value

        with open(preferences_path, "w", encoding="utf-8") as fh:
            yaml.dump(raw, fh, default_flow_style=False, sort_keys=False)

        return (
            f"Preference updated successfully.\n"
            f"  Key:       {key}\n"
            f"  Old value: {old_value}\n"
            f"  New value: {new_value}"
        )

    except Exception as exc:
        return f"Error modifying preferences: {exc}"
