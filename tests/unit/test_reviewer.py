"""Tests for the rich diagnostics reviewer."""

from src.agent.reviewer import (
    format_failure_analysis,
    format_history_for_llm,
    format_overfitting_analysis,
    format_param_optimization_insights,
    format_parameter_insights,
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


class TestParamOptimizationInsights:
    def test_empty_no_optimized_params(self):
        specs = [_make_spec(id="s1")]
        results = [_make_result(spec_id="s1")]
        text = format_param_optimization_insights(specs, results)
        assert text == ""

    def test_with_data_shows_shift_direction(self):
        specs = [
            _make_spec(id="s1", parameters={"lookback": 14, "threshold": 0.5}),
            _make_spec(id="s2", parameters={"lookback": 20}),
        ]
        results = [
            _make_result(
                spec_id="s1",
                sharpe_ratio=1.2,
                optimized_parameters={"lookback": 21, "threshold": 0.7},
            ),
            _make_result(
                spec_id="s2",
                sharpe_ratio=0.8,
                optimized_parameters={"lookback": 30},
            ),
        ]
        text = format_param_optimization_insights(specs, results)
        assert "PARAMETER OPTIMIZATION INSIGHTS" in text
        assert "14→21" in text
        assert "0.5→0.7" in text
        assert "20→30" in text


class TestOverfittingAnalysis:
    def test_empty_cross_phase(self):
        text = format_overfitting_analysis([])
        assert "No cross-phase data" in text

    def test_all_pass_both_phases(self):
        cross_phase = [
            {
                "spec_id": "s1", "template": "momentum/dual-momentum",
                "screen_sharpe": 1.0, "val_sharpe": 0.9,
                "screen_passed": True, "val_passed": True,
                "parameters": {"lookback": 126},
            },
            {
                "spec_id": "s2", "template": "momentum/dual-momentum",
                "screen_sharpe": 0.8, "val_sharpe": 0.7,
                "screen_passed": True, "val_passed": True,
                "parameters": {"lookback": 63},
            },
        ]
        text = format_overfitting_analysis(cross_phase)
        assert "0%" in text  # 0% overfit rate

    def test_with_overfitting(self):
        cross_phase = [
            {
                "spec_id": "s1", "template": "momentum/dual-momentum",
                "screen_sharpe": 1.5, "val_sharpe": 0.2,
                "screen_passed": True, "val_passed": False,
                "parameters": {"lookback": 126},
            },
            {
                "spec_id": "s2", "template": "technical/breakout",
                "screen_sharpe": 1.0, "val_sharpe": 0.8,
                "screen_passed": True, "val_passed": True,
                "parameters": {"lookback": 63},
            },
        ]
        text = format_overfitting_analysis(cross_phase)
        assert "50%" in text  # 1/2 overfit

    def test_sharpe_degradation(self):
        cross_phase = [
            {
                "spec_id": "s1", "template": "momentum/dual-momentum",
                "screen_sharpe": 2.0, "val_sharpe": 1.0,
                "screen_passed": True, "val_passed": True,
                "parameters": {},
            },
            {
                "spec_id": "s2", "template": "momentum/dual-momentum",
                "screen_sharpe": 1.0, "val_sharpe": 0.5,
                "screen_passed": True, "val_passed": True,
                "parameters": {},
            },
        ]
        text = format_overfitting_analysis(cross_phase)
        # avg degradation = (1.0 + 0.5) / 2 = 0.75
        assert "0.75" in text


class TestParameterInsights:
    def test_empty_no_specs(self):
        text = format_parameter_insights([], [])
        assert text == ""

    def test_single_template_insufficient_data(self):
        specs = [
            _make_spec(id="s1", parameters={"lookback": 10}),
            _make_spec(id="s2", parameters={"lookback": 20}),
        ]
        results = [
            _make_result(spec_id="s1", sharpe_ratio=1.0),
            _make_result(spec_id="s2", sharpe_ratio=0.5),
        ]
        text = format_parameter_insights(specs, results)
        assert "insufficient data" in text

    def test_with_correlations(self):
        # 4 results for the same template — enough to compute correlations
        specs = [
            _make_spec(id="s1", parameters={"lookback": 60}),
            _make_spec(id="s2", parameters={"lookback": 80}),
            _make_spec(id="s3", parameters={"lookback": 10}),
            _make_spec(id="s4", parameters={"lookback": 15}),
        ]
        results = [
            _make_result(spec_id="s1", sharpe_ratio=1.5),
            _make_result(spec_id="s2", sharpe_ratio=1.3),
            _make_result(spec_id="s3", sharpe_ratio=0.2),
            _make_result(spec_id="s4", sharpe_ratio=0.1),
        ]
        text = format_parameter_insights(specs, results)
        assert "PARAMETER INSIGHTS" in text
        assert "lookback" in text
        assert "top-half avg" in text

    def test_universe_insights(self):
        specs = [
            _make_spec(id="s1", universe_id="sp500"),
            _make_spec(id="s2", universe_id="sp500"),
            _make_spec(id="s3", universe_id="nasdaq100"),
        ]
        results = [
            _make_result(spec_id="s1", sharpe_ratio=1.0),
            _make_result(spec_id="s2", sharpe_ratio=1.2),
            _make_result(spec_id="s3", sharpe_ratio=0.5),
        ]
        text = format_parameter_insights(specs, results)
        assert "sp500" in text
        assert "nasdaq100" in text
        # sp500 avg 1.1, nasdaq100 avg 0.5 — sp500 should rank first
        sp500_pos = text.index("sp500")
        nasdaq_pos = text.index("nasdaq100")
        assert sp500_pos < nasdaq_pos

    def test_category_insights(self):
        specs = [
            _make_spec(id="s1", template="momentum/time-series-momentum"),
            _make_spec(id="s2", template="momentum/dual-momentum"),
            _make_spec(id="s3", template="technical/breakout"),
        ]
        results = [
            _make_result(spec_id="s1", sharpe_ratio=1.5),
            _make_result(spec_id="s2", sharpe_ratio=1.0),
            _make_result(spec_id="s3", sharpe_ratio=0.3),
        ]
        text = format_parameter_insights(specs, results)
        assert "momentum" in text
        assert "technical" in text
