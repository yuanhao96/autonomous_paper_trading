"""Tests for screening pass/fail filters."""

import pytest

from src.screening.filters import ScreeningFilters
from src.strategies.spec import StrategyResult


class TestScreeningFilters:
    @pytest.fixture
    def filters(self):
        return ScreeningFilters()

    def test_passing_result(self, filters):
        result = StrategyResult(
            spec_id="test",
            phase="screen",
            sharpe_ratio=1.5,
            max_drawdown=-0.15,
            total_trades=50,
            profit_factor=1.8,
        )
        fr = filters.apply(result)
        assert fr.passed
        assert fr.failure_reason is None

    def test_low_sharpe_fails(self, filters):
        result = StrategyResult(
            spec_id="test",
            phase="screen",
            sharpe_ratio=0.2,
            max_drawdown=-0.15,
            total_trades=50,
            profit_factor=1.8,
        )
        fr = filters.apply(result)
        assert not fr.passed
        assert "min_sharpe" in fr.failure_reason

    def test_high_drawdown_fails(self, filters):
        result = StrategyResult(
            spec_id="test",
            phase="screen",
            sharpe_ratio=1.5,
            max_drawdown=-0.40,
            total_trades=50,
            profit_factor=1.8,
        )
        fr = filters.apply(result)
        assert not fr.passed
        assert "max_drawdown" in fr.failure_reason

    def test_low_trades_fails(self, filters):
        result = StrategyResult(
            spec_id="test",
            phase="screen",
            sharpe_ratio=1.5,
            max_drawdown=-0.15,
            total_trades=5,
            profit_factor=1.8,
        )
        fr = filters.apply(result)
        assert not fr.passed
        assert "min_trades" in fr.failure_reason

    def test_low_profit_factor_fails(self, filters):
        result = StrategyResult(
            spec_id="test",
            phase="screen",
            sharpe_ratio=1.5,
            max_drawdown=-0.15,
            total_trades=50,
            profit_factor=0.8,
        )
        fr = filters.apply(result)
        assert not fr.passed
        assert "min_profit_factor" in fr.failure_reason

    def test_multiple_failures(self, filters):
        result = StrategyResult(
            spec_id="test",
            phase="screen",
            sharpe_ratio=0.1,
            max_drawdown=-0.50,
            total_trades=3,
            profit_factor=0.5,
        )
        fr = filters.apply(result)
        assert not fr.passed
        assert len([c for c in fr.checks.values() if not c]) == 4
