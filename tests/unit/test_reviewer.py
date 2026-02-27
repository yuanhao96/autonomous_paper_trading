"""Tests for the rich diagnostics reviewer."""

from src.agent.reviewer import (
    format_failure_analysis,
    format_history_for_llm,
    format_result_for_llm,
)
from src.strategies.spec import (
    RegimeResult,
    RiskParams,
    StrategyResult,
    StrategySpec,
)


def _make_spec(**kwargs) -> StrategySpec:
    defaults = dict(
        template="momentum/time-series-momentum",
        parameters={"lookback": 126},
        universe_id="sector_etfs",
        risk=RiskParams(max_position_pct=0.10, max_positions=5),
        created_by="llm_explore",
    )
    defaults.update(kwargs)
    return StrategySpec(**defaults)


def _make_result(**kwargs) -> StrategyResult:
    defaults = dict(
        spec_id="test",
        phase="screen",
        sharpe_ratio=1.0,
        annual_return=0.15,
        total_return=0.50,
        max_drawdown=-0.15,
        win_rate=0.55,
        profit_factor=1.5,
        total_trades=50,
        passed=True,
    )
    defaults.update(kwargs)
    return StrategyResult(**defaults)


class TestFormatResultForLLM:
    def test_basic_format(self):
        spec = _make_spec()
        result = _make_result()
        text = format_result_for_llm(spec, screen_result=result)
        assert "momentum/time-series-momentum" in text
        assert "SCREENING RESULT: PASS" in text
        assert "Sharpe: 1.00" in text

    def test_failed_result_shows_failure(self):
        spec = _make_spec()
        result = _make_result(passed=False, failure_reason="min_sharpe", sharpe_ratio=0.2)
        text = format_result_for_llm(spec, screen_result=result)
        assert "FAIL" in text
        assert "min_sharpe" in text

    def test_validation_with_regimes(self):
        spec = _make_spec()
        val = _make_result(
            phase="validate",
            regime_results=[
                RegimeResult("bull", "2020-01-01", "2021-01-01", 0.20, 1.0, -0.05, 20),
                RegimeResult("bear", "2022-01-01", "2022-06-01", -0.10, -0.5, -0.20, 10),
            ],
        )
        text = format_result_for_llm(spec, validation_result=val)
        assert "Regime Breakdown" in text
        assert "bull" in text
        assert "bear" in text

    def test_sharpe_degradation(self):
        spec = _make_spec()
        screen = _make_result(sharpe_ratio=1.5)
        val = _make_result(phase="validate", sharpe_ratio=0.5)
        text = format_result_for_llm(spec, screen_result=screen, validation_result=val)
        assert "Sharpe Degradation" in text
        assert "1.00" in text  # 1.5 - 0.5

    def test_parent_id_shown(self):
        spec = _make_spec(parent_id="abc123", generation=3)
        text = format_result_for_llm(spec)
        assert "abc123" in text
        assert "gen 3" in text


class TestFormatHistoryForLLM:
    def test_empty_history(self):
        text = format_history_for_llm([])
        assert "No previous" in text

    def test_with_history(self):
        history = [
            (_make_spec(template="momentum/time-series-momentum"), _make_result(sharpe_ratio=1.2)),
            (_make_spec(template="technical/breakout"), _make_result(sharpe_ratio=0.8, passed=False)),
        ]
        text = format_history_for_llm(history)
        assert "EVOLUTION HISTORY" in text
        assert "time-series-momentum" in text
        assert "breakout" in text
        assert "Total strategies tested: 2" in text

    def test_max_entries(self):
        history = [
            (_make_spec(), _make_result()) for _ in range(20)
        ]
        text = format_history_for_llm(history, max_entries=5)
        # Should only show 5 entries (plus header, divider, summary)
        lines = [l for l in text.split("\n") if l.strip()]
        # Header + divider + 5 entries + summary lines
        assert len(lines) <= 12


class TestFormatFailureAnalysis:
    def test_no_failures(self):
        text = format_failure_analysis([])
        assert "No failed" in text

    def test_failure_patterns(self):
        results = [
            (_make_spec(), _make_result(passed=False, failure_reason="min_sharpe")),
            (_make_spec(), _make_result(passed=False, failure_reason="min_sharpe")),
            (_make_spec(), _make_result(passed=False, failure_reason="max_drawdown")),
        ]
        text = format_failure_analysis(results)
        assert "min_sharpe: 2" in text
        assert "max_drawdown: 1" in text
        assert "Suggested actions" in text

    def test_all_passed_no_patterns(self):
        results = [(_make_spec(), _make_result(passed=True))]
        text = format_failure_analysis(results)
        assert "No failure patterns" in text
