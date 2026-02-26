"""Tests for Auditor Layer 2 (LLM analysis + pattern promotion)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from agents.auditor.layer2 import (
    Layer2Analysis,
    Layer2Auditor,
    PatternCandidate,
    PatternPromoter,
)
from evaluation.backtester import BacktestResult
from evaluation.metrics import PerformanceSummary
from evaluation.multi_period import MultiPeriodResult, PeriodConfig, PeriodResult
from strategies.spec import (
    CompositeCondition,
    ConditionSpec,
    IndicatorSpec,
    StrategySpec,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_spec() -> StrategySpec:
    return StrategySpec(
        name="test_strategy",
        version="0.1.0",
        description="Test",
        indicators=[
            IndicatorSpec(name="sma", params={"period": 20}, output_key="sma_val"),
        ],
        entry_conditions=CompositeCondition(
            logic="ALL_OF",
            conditions=[
                ConditionSpec(operator="greater_than", left="sma_val", right="100.0"),
            ],
        ),
        exit_conditions=CompositeCondition(
            logic="ALL_OF",
            conditions=[
                ConditionSpec(operator="less_than", left="sma_val", right="90.0"),
            ],
        ),
    )


@pytest.fixture
def sample_multi_period_result() -> MultiPeriodResult:
    metrics = PerformanceSummary(
        sharpe_ratio=0.5,
        max_drawdown=0.1,
        win_rate=0.6,
        total_pnl=5000.0,
        avg_pnl=100.0,
        best_trade=500.0,
        worst_trade=-200.0,
        num_trades=50,
    )
    bt_result = BacktestResult(metrics=metrics, windows_used=5)
    period = PeriodConfig(name="Test Period", start="2020-01-01", end="2021-01-01")
    pr = PeriodResult(period=period, backtest_result=bt_result, passed_floor=True)
    return MultiPeriodResult(
        strategy_name="test_strategy",
        period_results=[pr],
        composite_score=0.5,
    )


@pytest.fixture
def pattern_db(tmp_path: Path) -> str:
    return str(tmp_path / "test_patterns.db")


# ---------------------------------------------------------------------------
# Layer 2 Auditor tests
# ---------------------------------------------------------------------------


class TestStripForbiddenCode:
    """Tests for Layer2Auditor.strip_forbidden_code()."""

    def test_strips_import_sys(self) -> None:
        code = "import sys\nimport json\ndata = json.load(sys.stdin)\nprint(data)\n"
        cleaned = Layer2Auditor.strip_forbidden_code(code)
        assert "import sys" not in cleaned
        assert "import json" in cleaned

    def test_strips_from_os_import(self) -> None:
        code = "from os import path\nimport json\nprint('ok')\n"
        cleaned = Layer2Auditor.strip_forbidden_code(code)
        assert "os" not in cleaned
        assert "import json" in cleaned

    def test_strips_combined_forbidden_import(self) -> None:
        code = "import sys, os\nimport json\nprint('hi')\n"
        cleaned = Layer2Auditor.strip_forbidden_code(code)
        assert "import sys" not in cleaned
        assert "import os" not in cleaned
        assert "import json" in cleaned

    def test_keeps_mixed_import_nonforbidden(self) -> None:
        code = "import json, sys\nprint('hi')\n"
        cleaned = Layer2Auditor.strip_forbidden_code(code)
        # json should survive, sys should be removed.
        assert "json" in cleaned
        assert "sys" not in cleaned

    def test_strips_open_call(self) -> None:
        code = "f = open('test.txt')\nprint('ok')\n"
        cleaned = Layer2Auditor.strip_forbidden_code(code)
        assert "open(" not in cleaned
        # The call should be replaced with None.
        assert "None" in cleaned

    def test_strips_eval_call(self) -> None:
        code = "result = eval('1+1')\nprint(result)\n"
        cleaned = Layer2Auditor.strip_forbidden_code(code)
        assert "eval(" not in cleaned

    def test_clean_code_passes_validation(self) -> None:
        """Code with forbidden imports should pass validation after stripping."""
        code = (
            "import sys, json\n"
            "data = json.loads('{}')\n"
            "print(json.dumps({'findings': [], 'patterns': []}))\n"
        )
        cleaned = Layer2Auditor.strip_forbidden_code(code)
        violations = Layer2Auditor.validate_code(cleaned)
        assert violations == []

    def test_rewrites_sys_stdin(self) -> None:
        """sys.stdin references should be replaced with a safe _STDIN reader."""
        code = (
            "import sys, json\n"
            "data = json.load(sys.stdin)\n"
            "print(json.dumps(data))\n"
        )
        cleaned = Layer2Auditor.strip_forbidden_code(code)
        assert "sys" not in cleaned
        assert "_STDIN" in cleaned
        assert "import io as _io" in cleaned
        # Should still pass validation.
        violations = Layer2Auditor.validate_code(cleaned)
        assert violations == []

    def test_no_stdin_preamble_when_not_needed(self) -> None:
        """Don't inject _STDIN preamble if sys.stdin wasn't used."""
        code = "import sys\nprint('hello')\n"
        cleaned = Layer2Auditor.strip_forbidden_code(code)
        assert "_STDIN" not in cleaned
        assert "_io" not in cleaned

    def test_syntax_error_returned_as_is(self) -> None:
        code = "import sys\ndef foo(:\n"
        cleaned = Layer2Auditor.strip_forbidden_code(code)
        # Can't parse, returned unchanged.
        assert cleaned == code


class TestLayer2Auditor:
    def test_build_analysis_context(
        self, sample_spec: StrategySpec, sample_multi_period_result: MultiPeriodResult
    ) -> None:
        auditor = Layer2Auditor()
        context = auditor._build_analysis_context(sample_spec, sample_multi_period_result)
        data = json.loads(context)
        assert data["strategy_name"] == "test_strategy"
        assert len(data["periods"]) == 1
        assert data["periods"][0]["sharpe_ratio"] == 0.5

    def test_clean_code(self) -> None:
        raw = "```python\nprint('hello')\n```"
        cleaned = Layer2Auditor._clean_code(raw)
        assert "```" not in cleaned
        assert "print('hello')" in cleaned

    def test_parse_findings_valid(self) -> None:
        output = json.dumps({
            "findings": [
                {
                    "check_name": "low_trades",
                    "severity": "warning",
                    "description": "Too few trades",
                },
            ],
            "patterns": [],
        })
        findings = Layer2Auditor._parse_findings(output)
        assert len(findings) == 1
        assert findings[0].check_name == "low_trades"
        assert findings[0].severity == "warning"

    def test_parse_findings_invalid(self) -> None:
        findings = Layer2Auditor._parse_findings("not json")
        assert findings == []

    @patch("agents.auditor.layer2.call_llm")
    @patch("agents.auditor.layer2.load_prompt_template")
    def test_analyze_with_mock_llm(
        self,
        mock_template,
        mock_llm,
        sample_spec,
        sample_multi_period_result,
    ) -> None:
        # The auditor calls load_prompt_template twice: once for layer2, once for feedback.
        mock_template.side_effect = [
            "{spec_json} {metrics_json}",      # auditor_layer2 template
            "{spec_json} {analysis_results}",  # auditor_feedback template
        ]

        # First LLM call: analysis code (with stray `import sys` that
        # strip_forbidden_code should handle).  Second: feedback.
        analysis_code = (
            "import sys, json\n"
            "data = json.loads('{}')\n"
            "result = {'findings': ["
            "{'check_name': 'mock', 'severity': 'info', "
            "'description': 'test'}], 'patterns': []}\n"
            "print(json.dumps(result))\n"
        )
        mock_llm.side_effect = [analysis_code, "Try shorter periods."]

        auditor = Layer2Auditor()
        result = auditor.analyze(sample_spec, sample_multi_period_result)

        assert isinstance(result, Layer2Analysis)
        assert result.feedback == "Try shorter periods."


# ---------------------------------------------------------------------------
# Pattern Promoter tests
# ---------------------------------------------------------------------------


class TestPatternPromoter:
    def test_record_and_query(self, pattern_db: str) -> None:
        promoter = PatternPromoter(db_path=pattern_db)
        pattern = PatternCandidate(
            pattern_name="low_trade_count",
            description="Strategy has fewer than 10 trades",
        )

        promoter.record_pattern(pattern)
        promoter.record_pattern(pattern)
        promoter.record_pattern(pattern)

        candidates = promoter.check_promotion()
        assert len(candidates) == 1
        assert candidates[0].pattern_name == "low_trade_count"
        assert candidates[0].occurrences == 3

    def test_promotion_requires_three(self, pattern_db: str) -> None:
        promoter = PatternPromoter(db_path=pattern_db)
        pattern = PatternCandidate(
            pattern_name="rare_pattern",
            description="Seen twice only",
        )

        promoter.record_pattern(pattern)
        promoter.record_pattern(pattern)

        candidates = promoter.check_promotion()
        assert len(candidates) == 0

    def test_promote_writes_file(self, pattern_db: str, tmp_path: Path) -> None:
        promoter = PatternPromoter(db_path=pattern_db)
        pattern = PatternCandidate(
            pattern_name="test_check",
            description="Test check pattern",
            detection_code="check num_trades < 10",
            occurrences=5,
        )

        # Record to DB first.
        for _ in range(5):
            promoter.record_pattern(pattern)

        path_str = promoter.promote(pattern)
        promoted_path = Path(path_str)
        assert promoted_path.exists()

        content = promoted_path.read_text()
        assert "check_test_check" in content

        # Verify marked as promoted in DB.
        with sqlite3.connect(pattern_db) as conn:
            row = conn.execute(
                "SELECT promoted FROM patterns WHERE name = ?",
                ("test_check",),
            ).fetchone()
            assert row[0] == 1

        # Cleanup auto-generated file.
        promoted_path.unlink(missing_ok=True)

    def test_high_fp_rate_excluded(self, pattern_db: str) -> None:
        promoter = PatternPromoter(db_path=pattern_db)

        # Manually insert a pattern with high false positives.
        with sqlite3.connect(pattern_db) as conn:
            conn.execute(
                "INSERT INTO patterns (name, description, "
                "detection_code, occurrences, false_positives, "
                "promoted) VALUES (?, ?, ?, ?, ?, ?)",
                ("noisy_pattern", "Too many false positives", "", 10, 5, 0),
            )

        candidates = promoter.check_promotion()
        # FP rate = 5/10 = 0.5, which exceeds 0.2 threshold.
        names = [c.pattern_name for c in candidates]
        assert "noisy_pattern" not in names
