"""Tests for auditor sandbox safety and preferences enforcement."""

from __future__ import annotations

from agents.auditor.layer2 import Layer2Auditor
from core.preferences import Preferences
from strategies.generator import validate_spec_against_preferences
from strategies.spec import CompositeCondition, RiskParams, StrategySpec

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_prefs(**overrides) -> Preferences:
    defaults = {
        "risk_tolerance": "moderate",
        "max_drawdown_pct": 15.0,
        "trading_horizon": "swing",
        "target_annual_return_pct": 20.0,
        "allowed_asset_classes": ["us_equities"],
        "max_position_pct": 10.0,
        "max_daily_loss_pct": 3.0,
        "max_sector_concentration_pct": 30.0,
        "evolution_permissions": {"modify_strategies": True},
    }
    defaults.update(overrides)
    return Preferences(**defaults)


def _make_spec(stop_loss: float = 5.0, max_positions: int = 5) -> StrategySpec:
    return StrategySpec(
        name="test",
        version="1.0",
        description="test spec",
        indicators=[],
        entry_conditions=CompositeCondition(logic="ALL_OF", conditions=[]),
        exit_conditions=CompositeCondition(logic="ALL_OF", conditions=[]),
        risk=RiskParams(stop_loss_pct=stop_loss, max_positions=max_positions),
    )


# ---------------------------------------------------------------------------
# Layer2 Code Validation
# ---------------------------------------------------------------------------


class TestLayer2CodeValidation:
    """Test AST-based code validation for Layer2 auditor."""

    def test_safe_code_passes(self) -> None:
        code = """
import json
import math
data = json.loads(input())
print(json.dumps({"findings": []}))
"""
        violations = Layer2Auditor.validate_code(code)
        assert violations == []

    def test_os_import_rejected(self) -> None:
        code = "import os\nos.system('rm -rf /')"
        violations = Layer2Auditor.validate_code(code)
        assert any("os" in v for v in violations)

    def test_subprocess_import_rejected(self) -> None:
        code = "import subprocess\nsubprocess.run(['ls'])"
        violations = Layer2Auditor.validate_code(code)
        assert any("subprocess" in v for v in violations)

    def test_sys_import_rejected(self) -> None:
        code = "import sys\nsys.exit(1)"
        violations = Layer2Auditor.validate_code(code)
        assert any("sys" in v for v in violations)

    def test_from_import_rejected(self) -> None:
        code = "from os.path import join"
        violations = Layer2Auditor.validate_code(code)
        assert any("os" in v for v in violations)

    def test_eval_call_rejected(self) -> None:
        code = "result = eval('2 + 2')"
        violations = Layer2Auditor.validate_code(code)
        assert any("eval" in v for v in violations)

    def test_exec_call_rejected(self) -> None:
        code = "exec('import os')"
        violations = Layer2Auditor.validate_code(code)
        assert any("exec" in v for v in violations)

    def test_open_call_rejected(self) -> None:
        code = "f = open('/etc/passwd', 'r')"
        violations = Layer2Auditor.validate_code(code)
        assert any("open" in v for v in violations)

    def test_dunder_import_rejected(self) -> None:
        code = "mod = __import__('os')"
        violations = Layer2Auditor.validate_code(code)
        assert any("__import__" in v for v in violations)

    def test_socket_import_rejected(self) -> None:
        code = "import socket\ns = socket.socket()"
        violations = Layer2Auditor.validate_code(code)
        assert any("socket" in v for v in violations)

    def test_syntax_error_reported(self) -> None:
        code = "def foo(:"
        violations = Layer2Auditor.validate_code(code)
        assert any("Syntax error" in v for v in violations)

    def test_numpy_pandas_allowed(self) -> None:
        code = """
import numpy as np
import pandas as pd
import json
data = json.loads(input())
arr = np.array([1, 2, 3])
df = pd.DataFrame({"a": arr})
print(json.dumps({"findings": []}))
"""
        violations = Layer2Auditor.validate_code(code)
        assert violations == []

    def test_multiple_violations(self) -> None:
        code = """
import os
import subprocess
eval('bad')
open('/etc/passwd')
"""
        violations = Layer2Auditor.validate_code(code)
        assert len(violations) >= 4


# ---------------------------------------------------------------------------
# Preferences Enforcement
# ---------------------------------------------------------------------------


class TestPreferencesEnforcement:
    """Test that generated specs are validated against human preferences."""

    def test_valid_spec_passes(self) -> None:
        prefs = _make_prefs(max_drawdown_pct=15.0)
        spec = _make_spec(stop_loss=5.0, max_positions=5)
        violations = validate_spec_against_preferences(spec, prefs)
        assert violations == []

    def test_stop_loss_exceeds_max_drawdown(self) -> None:
        prefs = _make_prefs(max_drawdown_pct=10.0)
        spec = _make_spec(stop_loss=15.0)
        violations = validate_spec_against_preferences(spec, prefs)
        assert len(violations) == 1
        assert "stop_loss_pct" in violations[0]

    def test_max_positions_too_few_implies_concentration(self) -> None:
        prefs = _make_prefs(max_position_pct=10.0)
        # 1 position = 100% concentration, far above 10% * 2 = 20%
        spec = _make_spec(max_positions=1)
        violations = validate_spec_against_preferences(spec, prefs)
        assert len(violations) >= 1
        assert "max_positions" in violations[0]

    def test_reasonable_positions_passes(self) -> None:
        prefs = _make_prefs(max_position_pct=10.0)
        # 10 positions = 10% each, within 2x of 10%
        spec = _make_spec(max_positions=10)
        violations = validate_spec_against_preferences(spec, prefs)
        assert violations == []

    def test_edge_case_stop_loss_equals_max_drawdown(self) -> None:
        prefs = _make_prefs(max_drawdown_pct=15.0)
        spec = _make_spec(stop_loss=15.0)
        violations = validate_spec_against_preferences(spec, prefs)
        assert violations == []  # Equal is acceptable
