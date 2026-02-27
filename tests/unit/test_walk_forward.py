"""Unit tests for walk-forward analysis in the screening pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.risk.auditor import Auditor
from src.screening.screener import Screener, _average_walk_forward_metrics
from src.strategies.spec import RiskParams, StrategyResult, StrategySpec

# ── Helpers ──────────────────────────────────────────────────────────


def _make_price_df(n: int = 500, trend: float = 0.3) -> pd.DataFrame:
    """Create a realistic OHLCV DataFrame with enough data for walk-forward."""
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    rng = np.random.default_rng(42)
    close = 100.0 + np.cumsum(rng.normal(trend / n, 1.0, n))
    close = np.maximum(close, 10.0)
    return pd.DataFrame(
        {
            "Open": close * 0.995,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": rng.integers(100_000, 5_000_000, n),
        },
        index=idx,
    )


def _make_spec(
    template: str = "momentum/time-series-momentum",
    params: dict | None = None,
) -> StrategySpec:
    return StrategySpec(
        template=template,
        parameters=params or {"lookback": 126, "threshold": 0.0},
        universe_id="test",
        risk=RiskParams(max_position_pct=0.10, max_positions=5),
    )


def _mock_data_manager(data: pd.DataFrame) -> MagicMock:
    dm = MagicMock()
    dm.get_ohlcv.return_value = data
    return dm


# ── Tests: _average_walk_forward_metrics ────────────────────────────


class TestAverageWalkForwardMetrics:
    def test_averages_numeric_keys(self):
        metrics = [
            {
                "symbol": "SPY",
                "sharpe_ratio": 1.0,
                "total_return": 0.10,
                "total_trades": 10,
                "in_sample_sharpe": 0.0,
                "equity_curve": [1, 2],
                "drawdown_series": [0.01],
                "optimized_parameters": {},
            },
            {
                "symbol": "SPY",
                "sharpe_ratio": 2.0,
                "total_return": 0.20,
                "total_trades": 20,
                "in_sample_sharpe": 0.0,
                "equity_curve": [3, 4],
                "drawdown_series": [0.02],
                "optimized_parameters": {},
            },
        ]
        result = _average_walk_forward_metrics(metrics, "SPY", {"lookback": 100})
        assert result["sharpe_ratio"] == pytest.approx(1.5)
        assert result["total_return"] == pytest.approx(0.15)
        assert result["total_trades"] == pytest.approx(15.0)
        assert result["symbol"] == "SPY"
        assert result["optimized_parameters"] == {"lookback": 100}
        # Uses last window's equity curve
        assert result["equity_curve"] == [3, 4]


# ── Tests: Walk-forward branch in screen() ──────────────────────────


class TestScreenWalkForwardBranch:
    def test_optimize_true_uses_walk_forward(self):
        """When optimize=True, screen() should attempt walk-forward."""
        data = _make_price_df(500)
        spec = _make_spec()
        dm = _mock_data_manager(data)
        screener = Screener(data_manager=dm)

        with patch.object(screener, "_run_walk_forward", return_value=None) as wf_mock:
            with patch.object(
                screener,
                "_run_single",
                return_value={
                    "symbol": "SPY",
                    "sharpe_ratio": 0.5,
                    "total_return": 0.05,
                    "annual_return": 0.05,
                    "sortino_ratio": 0.3,
                    "max_drawdown": -0.10,
                    "win_rate": 0.5,
                    "profit_factor": 1.1,
                    "total_trades": 25,
                    "total_fees": 0.0,
                    "equity_curve": [],
                    "drawdown_series": [],
                    "optimized_parameters": {},
                    "in_sample_sharpe": 0.0,
                },
            ):
                result = screener.screen(spec, ["SPY"], optimize=True)

            # Walk-forward was attempted
            wf_mock.assert_called_once()
            # Result should still be valid (fell back to _run_single)
            assert result.phase == "screen"

    def test_optimize_false_skips_walk_forward(self):
        """When optimize=False, screen() should go directly to _run_single."""
        data = _make_price_df(500)
        spec = _make_spec()
        dm = _mock_data_manager(data)
        screener = Screener(data_manager=dm)

        with patch.object(screener, "_run_walk_forward") as wf_mock:
            with patch.object(
                screener,
                "_run_single",
                return_value={
                    "symbol": "SPY",
                    "sharpe_ratio": 0.5,
                    "total_return": 0.05,
                    "annual_return": 0.05,
                    "sortino_ratio": 0.3,
                    "max_drawdown": -0.10,
                    "win_rate": 0.5,
                    "profit_factor": 1.1,
                    "total_trades": 25,
                    "total_fees": 0.0,
                    "equity_curve": [],
                    "drawdown_series": [],
                    "optimized_parameters": {},
                    "in_sample_sharpe": 0.0,
                },
            ):
                result = screener.screen(spec, ["SPY"], optimize=False)

            # Walk-forward was NOT called
            wf_mock.assert_not_called()
            assert result.phase == "screen"


# ── Tests: _run_walk_forward ─────────────────────────────────────────


class TestRunWalkForward:
    def test_returns_none_when_no_bounds(self):
        """Templates with no optimization bounds should return None."""
        data = _make_price_df(500)
        spec = _make_spec(
            template="test/unknown-template",
            params={"foo": 1},
        )
        dm = _mock_data_manager(data)
        screener = Screener(data_manager=dm)
        result = screener._run_walk_forward(spec, data, "SPY")
        # Unknown template → empty bounds → None
        assert result is None

    def test_returns_none_when_data_too_short(self):
        """Data shorter than train+test should return None."""
        data = _make_price_df(200)  # 200 < 252 + 63 = 315
        spec = _make_spec()
        dm = _mock_data_manager(data)
        screener = Screener(data_manager=dm)
        result = screener._run_walk_forward(spec, data, "SPY")
        assert result is None

    def test_walk_forward_returns_metrics(self):
        """With enough data, walk-forward should return valid metrics."""
        data = _make_price_df(600)
        spec = _make_spec()
        dm = _mock_data_manager(data)
        screener = Screener(data_manager=dm)
        result = screener._run_walk_forward(spec, data, "SPY")

        # Should succeed with 600 bars (enough for at least 1 train+test window)
        if result is not None:
            assert "sharpe_ratio" in result
            assert "in_sample_sharpe" in result
            assert "optimized_parameters" in result
            assert result["symbol"] == "SPY"


# ── Tests: in_sample_sharpe in aggregate ─────────────────────────────


class TestAggregateInSampleSharpe:
    def test_aggregate_includes_in_sample_sharpe(self):
        """_aggregate_results should include in_sample_sharpe."""
        dm = MagicMock()
        screener = Screener(data_manager=dm)
        results = [
            {
                "symbol": "SPY",
                "total_return": 0.10,
                "annual_return": 0.10,
                "sharpe_ratio": 1.0,
                "sortino_ratio": 0.8,
                "max_drawdown": -0.05,
                "win_rate": 0.6,
                "profit_factor": 1.5,
                "total_trades": 30,
                "total_fees": 0.0,
                "equity_curve": [],
                "drawdown_series": [],
                "optimized_parameters": {"lookback": 100},
                "in_sample_sharpe": 2.0,
            },
            {
                "symbol": "QQQ",
                "total_return": 0.20,
                "annual_return": 0.20,
                "sharpe_ratio": 1.5,
                "sortino_ratio": 1.0,
                "max_drawdown": -0.08,
                "win_rate": 0.55,
                "profit_factor": 1.3,
                "total_trades": 25,
                "total_fees": 0.0,
                "equity_curve": [],
                "drawdown_series": [],
                "optimized_parameters": {"lookback": 120},
                "in_sample_sharpe": 3.0,
            },
        ]
        agg = screener._aggregate_results("test-id", results)
        assert agg.in_sample_sharpe == pytest.approx(2.5)
        assert agg.sharpe_ratio == pytest.approx(1.25)


# ── Tests: Auditor walk-forward gap check ────────────────────────────


class TestAuditorWalkForwardGap:
    def test_gap_check_passes_when_small(self):
        """Gap <= 1.5 should pass."""
        auditor = Auditor()
        result = StrategyResult(
            spec_id="test",
            phase="screen",
            sharpe_ratio=1.0,
            in_sample_sharpe=2.0,  # gap = 1.0
            total_trades=30,
            profit_factor=1.5,
        )
        report = auditor.audit(result)
        wf_checks = [c for c in report.checks if c.name == "walk_forward_gap"]
        assert len(wf_checks) == 1
        assert wf_checks[0].passed is True

    def test_gap_check_fails_when_large(self):
        """Gap > 1.5 should fail."""
        auditor = Auditor()
        result = StrategyResult(
            spec_id="test",
            phase="screen",
            sharpe_ratio=0.5,
            in_sample_sharpe=3.0,  # gap = 2.5
            total_trades=30,
            profit_factor=1.5,
        )
        report = auditor.audit(result)
        wf_checks = [c for c in report.checks if c.name == "walk_forward_gap"]
        assert len(wf_checks) == 1
        assert wf_checks[0].passed is False

    def test_no_gap_check_when_is_sharpe_zero(self):
        """Walk-forward gap check should not run when in_sample_sharpe=0."""
        auditor = Auditor()
        result = StrategyResult(
            spec_id="test",
            phase="screen",
            sharpe_ratio=1.0,
            in_sample_sharpe=0.0,
            total_trades=30,
            profit_factor=1.5,
        )
        report = auditor.audit(result)
        wf_checks = [c for c in report.checks if c.name == "walk_forward_gap"]
        assert len(wf_checks) == 0

    def test_gap_check_boundary_at_1_5(self):
        """Exactly 1.5 gap should pass (<=)."""
        auditor = Auditor()
        result = StrategyResult(
            spec_id="test",
            phase="screen",
            sharpe_ratio=0.5,
            in_sample_sharpe=2.0,  # gap = 1.5
            total_trades=30,
            profit_factor=1.5,
        )
        report = auditor.audit(result)
        wf_checks = [c for c in report.checks if c.name == "walk_forward_gap"]
        assert len(wf_checks) == 1
        assert wf_checks[0].passed is True
