"""Tests for auditor checks and AuditorAgent."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from agents.auditor.agent import AuditorAgent, AuditReport
from agents.auditor.checks.data_quality import check_data_quality
from agents.auditor.checks.look_ahead_bias import check_look_ahead_bias
from agents.auditor.checks.overfitting import check_overfitting
from evaluation.metrics import PerformanceSummary

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeBacktestResult:
    trades: list[dict] = field(default_factory=list)
    equity_curve: pd.Series = field(
        default_factory=lambda: pd.Series(
            [100000.0 + i * 10 for i in range(100)],
            index=pd.bdate_range("2023-01-01", periods=100),
        )
    )
    windows_used: int = 5


# ---------------------------------------------------------------------------
# Tests — look_ahead_bias
# ---------------------------------------------------------------------------


class TestLookAheadBias:
    def test_detects_shift_minus_1(self) -> None:
        code = """\
import pandas as pd
df['future_close'] = df['Close'].shift(-1)
signal = df['Close'] > df['future_close']
"""
        result = FakeBacktestResult()
        findings = check_look_ahead_bias(result, code)
        assert len(findings) >= 1
        assert any("shift" in f.description.lower() for f in findings)
        assert all(f.severity == "critical" for f in findings if "shift" in f.description.lower())

    def test_detects_shift_minus_n(self) -> None:
        code = "predicted = series.shift(-5)"
        findings = check_look_ahead_bias(FakeBacktestResult(), code)
        assert len(findings) >= 1

    def test_clean_code_no_findings(self) -> None:
        code = """\
import pandas as pd
df['sma'] = df['Close'].rolling(20).mean()
signal = df['Close'] > df['sma']
"""
        findings = check_look_ahead_bias(FakeBacktestResult(), code)
        # Only code-pattern findings should be checked; trade-date and
        # perfect-entry checks need actual trades so they produce nothing.
        code_findings = [
            f for f in findings
            if "code" in f.description.lower()
            or "shift" in f.description.lower()
        ]
        assert code_findings == []

    def test_empty_code(self) -> None:
        findings = check_look_ahead_bias(FakeBacktestResult(), "")
        assert findings == []


# ---------------------------------------------------------------------------
# Tests — overfitting
# ---------------------------------------------------------------------------


class TestOverfitting:
    def test_detects_sharpe_divergence(self) -> None:
        in_sample = PerformanceSummary(
            sharpe_ratio=3.0, max_drawdown=0.05, win_rate=0.7,
            total_pnl=10000, avg_pnl=100, best_trade=500,
            worst_trade=-200, num_trades=100,
        )
        out_sample = PerformanceSummary(
            sharpe_ratio=0.5, max_drawdown=0.20, win_rate=0.45,
            total_pnl=1000, avg_pnl=10, best_trade=200,
            worst_trade=-300, num_trades=100,
        )
        findings = check_overfitting(FakeBacktestResult(), in_sample, out_sample)
        assert len(findings) >= 1
        sharpe_findings = [f for f in findings if "sharpe" in f.description.lower()]
        assert len(sharpe_findings) >= 1

    def test_detects_win_rate_drop(self) -> None:
        in_sample = PerformanceSummary(
            sharpe_ratio=1.5, max_drawdown=0.05, win_rate=0.80,
            total_pnl=5000, avg_pnl=50, best_trade=300,
            worst_trade=-100, num_trades=100,
        )
        out_sample = PerformanceSummary(
            sharpe_ratio=1.0, max_drawdown=0.10, win_rate=0.55,
            total_pnl=2000, avg_pnl=20, best_trade=200,
            worst_trade=-150, num_trades=100,
        )
        findings = check_overfitting(FakeBacktestResult(), in_sample, out_sample)
        wr_findings = [f for f in findings if "win rate" in f.description.lower()]
        assert len(wr_findings) >= 1

    def test_detects_complete_oos_failure(self) -> None:
        in_sample = PerformanceSummary(
            sharpe_ratio=2.0, max_drawdown=0.05, win_rate=0.7,
            total_pnl=10000, avg_pnl=100, best_trade=500,
            worst_trade=-200, num_trades=100,
        )
        out_sample = PerformanceSummary(
            sharpe_ratio=-0.5, max_drawdown=0.30, win_rate=0.40,
            total_pnl=-5000, avg_pnl=-50, best_trade=100,
            worst_trade=-500, num_trades=100,
        )
        findings = check_overfitting(FakeBacktestResult(), in_sample, out_sample)
        critical = [f for f in findings if f.severity == "critical"]
        assert len(critical) >= 1

    def test_no_overfitting_similar_metrics(self) -> None:
        metrics = PerformanceSummary(
            sharpe_ratio=1.2, max_drawdown=0.10, win_rate=0.55,
            total_pnl=5000, avg_pnl=50, best_trade=300,
            worst_trade=-200, num_trades=100,
        )
        findings = check_overfitting(FakeBacktestResult(), metrics, metrics)
        assert findings == []


# ---------------------------------------------------------------------------
# Tests — data_quality
# ---------------------------------------------------------------------------


class TestDataQuality:
    def test_detects_nan_values(self) -> None:
        data = pd.DataFrame(
            {
                "Open": [100, np.nan, 102],
                "High": [105, 106, 107],
                "Low": [95, 94, 96],
                "Close": [100, 101, 102],
                "Volume": [1e6, 1e6, 1e6],
            },
            index=pd.bdate_range("2023-01-02", periods=3),
        )
        findings = check_data_quality(data)
        nan_findings = [f for f in findings if "nan" in f.description.lower()]
        assert len(nan_findings) >= 1

    def test_detects_negative_prices(self) -> None:
        data = pd.DataFrame(
            {
                "Open": [100, -5, 102],
                "High": [105, 106, 107],
                "Low": [95, 94, 96],
                "Close": [100, 101, 102],
                "Volume": [1e6, 1e6, 1e6],
            },
            index=pd.bdate_range("2023-01-02", periods=3),
        )
        findings = check_data_quality(data)
        neg_findings = [f for f in findings if "negative" in f.description.lower()]
        assert len(neg_findings) >= 1
        assert any(f.severity == "critical" for f in neg_findings)

    def test_detects_date_gap(self) -> None:
        """A gap > 3 business days should be flagged."""
        dates = pd.to_datetime(["2023-01-02", "2023-01-03", "2023-01-16"])
        data = pd.DataFrame(
            {
                "Open": [100, 101, 102],
                "High": [105, 106, 107],
                "Low": [95, 96, 97],
                "Close": [100, 101, 102],
                "Volume": [1e6, 1e6, 1e6],
            },
            index=dates,
        )
        findings = check_data_quality(data)
        gap_findings = [f for f in findings if "gap" in f.description.lower()]
        assert len(gap_findings) >= 1

    def test_clean_data_no_critical(self, sample_ohlcv_data: pd.DataFrame) -> None:
        findings = check_data_quality(sample_ohlcv_data)
        critical = [f for f in findings if f.severity == "critical"]
        assert critical == []

    def test_empty_data(self) -> None:
        findings = check_data_quality(pd.DataFrame())
        assert len(findings) >= 1
        assert findings[0].severity == "critical"
        assert "empty" in findings[0].description.lower()


# ---------------------------------------------------------------------------
# Tests — AuditorAgent.audit_backtest aggregation
# ---------------------------------------------------------------------------


class TestAuditorAgent:
    def test_audit_backtest_aggregates_findings(self) -> None:
        agent = AuditorAgent()

        code_with_leak = "df['future'] = df['Close'].shift(-1)"
        bt_result = FakeBacktestResult()

        report = agent.audit_backtest(bt_result, strategy_code=code_with_leak)
        assert isinstance(report, AuditReport)
        # The look-ahead bias check should have flagged the shift(-1).
        assert len(report.findings) >= 1
        assert any(f.check_name == "look_ahead_bias" for f in report.findings)

    def test_audit_backtest_passes_clean_code(self) -> None:
        agent = AuditorAgent()
        clean_code = "signal = df['Close'].rolling(20).mean()"
        bt_result = FakeBacktestResult()

        report = agent.audit_backtest(bt_result, strategy_code=clean_code)
        assert isinstance(report, AuditReport)
        # No critical findings expected.
        critical = [f for f in report.findings if f.severity == "critical"]
        assert critical == []
        assert report.passed is True

    def test_audit_backtest_with_overfitting_metrics(self) -> None:
        agent = AuditorAgent()
        bt_result = FakeBacktestResult()

        is_metrics = PerformanceSummary(
            sharpe_ratio=4.0, max_drawdown=0.02, win_rate=0.9,
            total_pnl=50000, avg_pnl=500, best_trade=2000,
            worst_trade=-100, num_trades=100,
        )
        oos_metrics = PerformanceSummary(
            sharpe_ratio=-1.0, max_drawdown=0.40, win_rate=0.35,
            total_pnl=-20000, avg_pnl=-200, best_trade=500,
            worst_trade=-2000, num_trades=100,
        )

        report = agent.audit_backtest(
            bt_result,
            in_sample_metrics=is_metrics,
            out_of_sample_metrics=oos_metrics,
        )
        assert report.passed is False
        assert any(f.check_name == "overfitting" for f in report.findings)

    def test_audit_data(self, sample_ohlcv_data: pd.DataFrame) -> None:
        agent = AuditorAgent()
        report = agent.audit_data(sample_ohlcv_data)
        assert isinstance(report, AuditReport)
        assert report.timestamp != ""
