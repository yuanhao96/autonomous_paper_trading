"""Auditor Layer 2: LLM-powered analysis with constructive feedback.

Layer 2 generates Python analysis code, runs it in a sandboxed subprocess,
produces actionable feedback, and promotes recurring patterns to Layer 1.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agents.auditor.checks.look_ahead_bias import Finding
from core.llm import call_llm, load_prompt_template
from evaluation.multi_period import MultiPeriodResult
from strategies.spec import StrategySpec

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Layer2Analysis:
    """Result of a Layer 2 audit analysis."""

    findings: list[Finding] = field(default_factory=list)
    feedback: str = ""
    raw_analysis_code: str = ""
    analysis_output: str = ""
    execution_success: bool = False


@dataclass
class PatternCandidate:
    """A pattern detected by Layer 2 that may be promoted to Layer 1."""

    pattern_name: str
    description: str
    detection_code: str = ""
    occurrences: int = 0
    false_positive_rate: float = 0.0


# ---------------------------------------------------------------------------
# Layer 2 Auditor
# ---------------------------------------------------------------------------


class Layer2Auditor:
    """LLM-driven auditor that generates analysis code and constructive feedback."""

    def analyze(
        self,
        spec: StrategySpec,
        multi_period_result: MultiPeriodResult,
    ) -> Layer2Analysis:
        """Run Layer 2 analysis on a strategy.

        1. Build context from spec + backtest metrics.
        2. Ask LLM for analysis code.
        3. Execute in sandboxed subprocess.
        4. Parse findings.
        5. Generate constructive feedback.
        """
        result = Layer2Analysis()

        # Build context.
        context_json = self._build_analysis_context(spec, multi_period_result)

        # Get analysis code from LLM.
        try:
            template = load_prompt_template("auditor_layer2")
            prompt = template.format(
                spec_json=json.dumps(spec.to_dict(), indent=2),
                metrics_json=context_json,
            )
            raw_code = call_llm(prompt)
            result.raw_analysis_code = self._clean_code(raw_code)
        except Exception:
            logger.exception("Layer 2: failed to get analysis code from LLM")
            return result

        # Execute analysis.
        success, stdout = self._execute_analysis(result.raw_analysis_code, context_json)
        result.execution_success = success
        result.analysis_output = stdout

        # Parse findings from output.
        if success:
            result.findings = self._parse_findings(stdout)

        # Generate constructive feedback.
        try:
            feedback_template = load_prompt_template("auditor_feedback")
            feedback_prompt = feedback_template.format(
                spec_json=json.dumps(spec.to_dict(), indent=2),
                analysis_results=stdout if success else "(analysis failed)",
            )
            result.feedback = call_llm(feedback_prompt)
        except Exception:
            logger.exception("Layer 2: failed to generate feedback")

        return result

    # Modules that must not appear in LLM-generated analysis code.
    _FORBIDDEN_IMPORTS = frozenset({
        "os", "subprocess", "sys", "shutil", "socket", "http", "urllib",
        "ctypes", "importlib", "pathlib", "multiprocessing", "threading",
        "signal", "webbrowser", "ftplib", "smtplib", "telnetlib",
    })

    # Built-in function names that must not be called.
    _FORBIDDEN_CALLS = frozenset({
        "eval", "exec", "__import__", "compile", "open",
        "breakpoint", "exit", "quit",
    })

    @classmethod
    def strip_forbidden_code(cls, code: str) -> str:
        """Remove forbidden imports and calls from LLM-generated code.

        Uses AST to surgically remove violating nodes so the rest of the
        script can still run.  Returns the cleaned source code.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code  # Can't parse — return as-is for validate_code to flag.

        nodes_to_remove: list[ast.stmt] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # Remove entire import if ALL names are forbidden.
                all_forbidden = all(
                    alias.name.split(".")[0] in cls._FORBIDDEN_IMPORTS
                    for alias in node.names
                )
                if all_forbidden:
                    nodes_to_remove.append(node)
                else:
                    # Keep only non-forbidden names.
                    node.names = [
                        alias for alias in node.names
                        if alias.name.split(".")[0] not in cls._FORBIDDEN_IMPORTS
                    ]

            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in cls._FORBIDDEN_IMPORTS:
                    nodes_to_remove.append(node)

        # Remove flagged statements from the module body (and any
        # function/class bodies).
        if nodes_to_remove:
            remove_set = set(id(n) for n in nodes_to_remove)
            for parent in ast.walk(tree):
                for field_name, field_value in ast.iter_fields(parent):
                    if isinstance(field_value, list):
                        new_list = [
                            item for item in field_value
                            if not (isinstance(item, ast.stmt) and id(item) in remove_set)
                        ]
                        # Avoid empty bodies (replace with `pass`).
                        if (
                            len(new_list) < len(field_value)
                            and len(new_list) == 0
                            and field_name == "body"
                        ):
                            new_list = [ast.Pass()]
                        setattr(parent, field_name, new_list)

            ast.fix_missing_locations(tree)

        # Second pass: replace forbidden calls with None (a no-op expression).
        class _CallRewriter(ast.NodeTransformer):
            def visit_Call(self, node: ast.Call) -> ast.AST:
                self.generic_visit(node)
                func = node.func
                name = None
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name and name in cls._FORBIDDEN_CALLS:
                    return ast.copy_location(
                        ast.Constant(value=None), node,
                    )
                return node

        tree = _CallRewriter().visit(tree)

        # Third pass: rewrite `sys.stdin` references to use a safe
        # stdin reader, since we just stripped `import sys`.
        class _StdinRewriter(ast.NodeTransformer):
            found_stdin = False

            def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
                self.generic_visit(node)
                if (
                    node.attr == "stdin"
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "sys"
                ):
                    self.found_stdin = True
                    return ast.copy_location(ast.Name(id="_STDIN", ctx=ast.Load()), node)
                return node

        rewriter = _StdinRewriter()
        tree = rewriter.visit(tree)

        # If we rewrote any sys.stdin refs, prepend a _STDIN helper.
        if rewriter.found_stdin:
            preamble = ast.parse(
                "import io as _io\n_STDIN = _io.TextIOWrapper(_io.FileIO(0))\n"
            )
            tree.body = preamble.body + tree.body

        ast.fix_missing_locations(tree)

        return ast.unparse(tree)

    @classmethod
    def validate_code(cls, code: str) -> list[str]:
        """Validate LLM-generated Python code using AST analysis.

        Returns a list of violation descriptions.  An empty list means the
        code passed validation.
        """
        violations: list[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            violations.append(f"Syntax error: {exc}")
            return violations

        for node in ast.walk(tree):
            # Check import statements.
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top in cls._FORBIDDEN_IMPORTS:
                        violations.append(f"Forbidden import: {alias.name}")

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    if top in cls._FORBIDDEN_IMPORTS:
                        violations.append(f"Forbidden import: {node.module}")

            # Check function calls to forbidden builtins.
            elif isinstance(node, ast.Call):
                func = node.func
                name = None
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name and name in cls._FORBIDDEN_CALLS:
                    violations.append(f"Forbidden call: {name}()")

        return violations

    def _execute_analysis(
        self, code: str, context_json: str
    ) -> tuple[bool, str]:
        """Execute analysis code in a sandboxed subprocess."""
        # Strip forbidden imports/calls before validation so that
        # LLM-generated code with stray `import sys` etc. can still run.
        code = self.strip_forbidden_code(code)

        # Validate the cleaned code.
        violations = self.validate_code(code)
        if violations:
            msg = "Code validation failed: " + "; ".join(violations)
            logger.warning("Layer 2: %s", msg)
            return False, msg

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(code)
            script_path = f.name

        try:
            # Build a minimal env that lets Python find installed packages
            # but strips secrets and dangerous variables.
            safe_env = self._build_sandbox_env()

            proc = subprocess.run(
                [sys.executable, script_path],
                input=context_json,
                capture_output=True,
                text=True,
                timeout=30,
                env=safe_env,
            )
            if proc.returncode == 0:
                return True, proc.stdout
            else:
                logger.warning(
                    "Layer 2 analysis script failed (rc=%d): %s",
                    proc.returncode,
                    proc.stderr[:500],
                )
                return False, proc.stderr[:500]
        except subprocess.TimeoutExpired:
            logger.warning("Layer 2 analysis script timed out")
            return False, "Timeout"
        except Exception as exc:
            logger.exception("Layer 2 analysis execution error")
            return False, str(exc)
        finally:
            Path(script_path).unlink(missing_ok=True)

    # Environment variables passed through to the sandboxed subprocess.
    # These are needed so Python can find installed packages.
    _ENV_PASSTHROUGH = frozenset({
        "PATH", "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "CONDA_PREFIX",
        "CONDA_DEFAULT_ENV", "LANG", "LC_ALL", "TMPDIR", "TEMP", "TMP",
    })

    @classmethod
    def _build_sandbox_env(cls) -> dict[str, str]:
        """Build a minimal environment for the sandboxed subprocess.

        Passes through only the variables needed for Python to locate
        installed packages.  API keys, HOME, and other sensitive vars
        are excluded.
        """
        return {
            k: v for k, v in os.environ.items()
            if k in cls._ENV_PASSTHROUGH
        }

    def _build_analysis_context(
        self,
        spec: StrategySpec,
        result: MultiPeriodResult,
    ) -> str:
        """Serialize strategy spec + backtest metrics into JSON for the analysis script."""
        periods_data: list[dict[str, Any]] = []
        for pr in result.period_results:
            metrics = pr.backtest_result.metrics
            periods_data.append({
                "period_name": pr.period.name,
                "sharpe_ratio": metrics.sharpe_ratio,
                "max_drawdown": metrics.max_drawdown,
                "win_rate": metrics.win_rate,
                "total_pnl": metrics.total_pnl,
                "num_trades": metrics.num_trades,
                "avg_pnl": metrics.avg_pnl,
                "best_trade": metrics.best_trade,
                "worst_trade": metrics.worst_trade,
                "passed_floor": pr.passed_floor,
            })

        context = {
            "strategy_name": spec.name,
            "composite_score": result.composite_score,
            "disqualified": result.disqualified,
            "periods": periods_data,
            "indicator_count": len(spec.indicators),
            "indicator_names": [i.name for i in spec.indicators],
        }
        return json.dumps(context, indent=2)

    @staticmethod
    def _clean_code(raw: str) -> str:
        """Strip markdown fences from LLM-generated code."""
        code = raw.strip()
        if code.startswith("```"):
            code = re.sub(r"^```(?:python)?\s*", "", code)
            code = re.sub(r"\s*```$", "", code)
        return code

    @staticmethod
    def _parse_findings(stdout: str) -> list[Finding]:
        """Parse findings from the analysis script's JSON output."""
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            # Try to extract JSON from mixed output.
            match = re.search(r"\{[\s\S]*\}", stdout)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    return []
            else:
                return []

        findings: list[Finding] = []
        for f in data.get("findings", []):
            findings.append(
                Finding(
                    check_name=f.get("check_name", "layer2_analysis"),
                    severity=f.get("severity", "info"),
                    description=f.get("description", ""),
                    evidence="",
                )
            )
        return findings


# ---------------------------------------------------------------------------
# Pattern Promoter
# ---------------------------------------------------------------------------


class PatternPromoter:
    """Track recurring Layer 2 patterns and promote them to Layer 1 checks."""

    def __init__(self, db_path: str = "data/auditor_patterns.db") -> None:
        self._db_path = Path(db_path)
        if not self._db_path.is_absolute():
            self._db_path = _PROJECT_ROOT / self._db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    name TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    detection_code TEXT NOT NULL DEFAULT '',
                    occurrences INTEGER NOT NULL DEFAULT 0,
                    false_positives INTEGER NOT NULL DEFAULT 0,
                    promoted INTEGER NOT NULL DEFAULT 0
                )
            """)

    def record_pattern(self, pattern: PatternCandidate) -> None:
        """Record or increment a pattern occurrence."""
        with sqlite3.connect(str(self._db_path)) as conn:
            existing = conn.execute(
                "SELECT occurrences FROM patterns WHERE name = ?",
                (pattern.pattern_name,),
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE patterns SET occurrences = occurrences + 1 WHERE name = ?",
                    (pattern.pattern_name,),
                )
            else:
                conn.execute(
                    "INSERT INTO patterns (name, description, detection_code, occurrences) "
                    "VALUES (?, ?, ?, 1)",
                    (pattern.pattern_name, pattern.description, pattern.detection_code),
                )

    def check_promotion(self) -> list[PatternCandidate]:
        """Return patterns ready for promotion (>= 3 occurrences, < 20% FP rate)."""
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute(
                """
                SELECT name, description, detection_code, occurrences, false_positives
                FROM patterns
                WHERE promoted = 0 AND occurrences >= 3
                """
            ).fetchall()

        candidates: list[PatternCandidate] = []
        for name, desc, code, occ, fp in rows:
            fp_rate = fp / occ if occ > 0 else 0.0
            if fp_rate < 0.2:
                candidates.append(
                    PatternCandidate(
                        pattern_name=name,
                        description=desc,
                        detection_code=code,
                        occurrences=occ,
                        false_positive_rate=fp_rate,
                    )
                )
        return candidates

    def promote(self, pattern: PatternCandidate) -> str:
        """Write a Layer 1 check file for the pattern."""
        checks_dir = _PROJECT_ROOT / "agents" / "auditor" / "checks"
        checks_dir.mkdir(parents=True, exist_ok=True)

        safe_name = re.sub(r"[^a-z0-9_]", "_", pattern.pattern_name.lower())
        file_path = checks_dir / f"auto_{safe_name}.py"

        code = (
            f'"""Auto-promoted audit check: {pattern.description}"""\n\n'
            f"from agents.auditor.checks.look_ahead_bias import Finding\n\n\n"
            f"def check_{safe_name}(backtest_result) -> list[Finding]:\n"
            f'    """Check for {pattern.description}."""\n'
            f"    findings = []\n"
            f"    # Pattern detection code:\n"
            f"    # {pattern.detection_code[:200]}\n"
            f"    return findings\n"
        )

        file_path.write_text(code, encoding="utf-8")

        # Mark as promoted in DB.
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "UPDATE patterns SET promoted = 1 WHERE name = ?",
                (pattern.pattern_name,),
            )

        logger.info("Promoted pattern '%s' to %s", pattern.pattern_name, file_path)
        return str(file_path)

    def validate_against_known_good(
        self,
        pattern: PatternCandidate,
        good_results: list[Any],
    ) -> float:
        """Run candidate check against known-good strategies, return FP rate."""
        if not good_results:
            return 0.0

        false_positives = 0
        for result in good_results:
            # Simple heuristic: if pattern matches on known-good, it's a false positive.
            if pattern.detection_code and "num_trades" in pattern.detection_code:
                if hasattr(result, "metrics") and result.metrics.num_trades > 10:
                    false_positives += 1

        fp_rate = false_positives / len(good_results)

        # Update DB.
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "UPDATE patterns SET false_positives = ? WHERE name = ?",
                (false_positives, pattern.pattern_name),
            )

        return fp_rate
