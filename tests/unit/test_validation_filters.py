"""Tests for validation pass/fail filters."""

import pytest

from src.strategies.spec import RegimeResult, StrategyResult
from src.validation.capacity import CapacityEstimate
from src.validation.filters import ValidationFilters


@pytest.fixture
def filters():
    return ValidationFilters()


class TestValidationFilters:
    def test_passing_result(self, filters):
        result = StrategyResult(
            spec_id="test",
            phase="validate",
            sharpe_ratio=0.8,
            max_drawdown=-0.20,
            regime_results=[
                RegimeResult(
                    regime="bull", period_start="2020-01-01", period_end="2021-01-01",
                    annual_return=0.15, sharpe_ratio=1.0, max_drawdown=-0.10, total_trades=20,
                ),
                RegimeResult(
                    regime="bear", period_start="2022-01-01", period_end="2022-06-01",
                    annual_return=0.02, sharpe_ratio=0.3, max_drawdown=-0.20, total_trades=15,
                ),
                RegimeResult(
                    regime="sideways", period_start="2023-01-01", period_end="2023-06-01",
                    annual_return=-0.01, sharpe_ratio=-0.1, max_drawdown=-0.05, total_trades=10,
                ),
            ],
        )
        capacity = CapacityEstimate(
            max_capital=200_000,
            limiting_factor="volume",
            avg_daily_volume_usd=1_000_000,
            max_participation_rate=0.01,
            details="OK",
        )
        fr = filters.apply(result, capacity=capacity)
        assert fr.passed  # 2 positive regimes, good Sharpe, enough capacity

    def test_low_sharpe_fails(self, filters):
        result = StrategyResult(
            spec_id="test", phase="validate", sharpe_ratio=0.1,
            max_drawdown=-0.10,
            regime_results=[
                RegimeResult("bull", "2020-01-01", "2021-01-01", 0.10, 0.5, -0.05, 10),
                RegimeResult("bear", "2022-01-01", "2022-06-01", 0.05, 0.2, -0.10, 5),
            ],
        )
        fr = filters.apply(result)
        assert not fr.passed
        assert "min_sharpe" in fr.failure_reason

    def test_high_drawdown_fails(self, filters):
        result = StrategyResult(
            spec_id="test", phase="validate", sharpe_ratio=0.5,
            max_drawdown=-0.45,
            regime_results=[
                RegimeResult("bull", "2020-01-01", "2021-01-01", 0.20, 1.0, -0.10, 20),
                RegimeResult("bear", "2022-01-01", "2022-06-01", 0.05, 0.3, -0.40, 10),
            ],
        )
        fr = filters.apply(result)
        assert not fr.passed
        assert "max_drawdown" in fr.failure_reason

    def test_too_few_positive_regimes(self, filters):
        result = StrategyResult(
            spec_id="test", phase="validate", sharpe_ratio=0.5,
            max_drawdown=-0.10,
            regime_results=[
                RegimeResult("bull", "2020-01-01", "2021-01-01", 0.10, 0.5, -0.05, 10),
                RegimeResult("bear", "2022-01-01", "2022-06-01", -0.15, -0.5, -0.20, 5),
                RegimeResult("high_vol", "2020-03-01", "2020-06-01", -0.10, -0.3, -0.15, 8),
                RegimeResult("sideways", "2023-01-01", "2023-06-01", -0.02, -0.1, -0.03, 4),
            ],
        )
        fr = filters.apply(result)
        assert not fr.passed
        assert "min_positive_regimes" in fr.failure_reason

    def test_low_capacity_fails(self, filters):
        result = StrategyResult(
            spec_id="test", phase="validate", sharpe_ratio=1.0,
            max_drawdown=-0.10,
            regime_results=[
                RegimeResult("bull", "2020-01-01", "2021-01-01", 0.20, 1.0, -0.05, 20),
                RegimeResult("bear", "2022-01-01", "2022-06-01", 0.05, 0.3, -0.10, 10),
            ],
        )
        capacity = CapacityEstimate(
            max_capital=10_000,  # Below $50K minimum
            limiting_factor="volume",
            avg_daily_volume_usd=50_000,
            max_participation_rate=0.01,
            details="Low volume",
        )
        fr = filters.apply(result, capacity=capacity)
        assert not fr.passed
        assert "min_capacity" in fr.failure_reason

    def test_no_capacity_check_still_validates(self, filters):
        """When capacity is None, skip that check."""
        result = StrategyResult(
            spec_id="test", phase="validate", sharpe_ratio=0.5,
            max_drawdown=-0.10,
            regime_results=[
                RegimeResult("bull", "2020-01-01", "2021-01-01", 0.10, 0.5, -0.05, 10),
                RegimeResult("bear", "2022-01-01", "2022-06-01", 0.05, 0.3, -0.10, 5),
            ],
        )
        fr = filters.apply(result, capacity=None)
        assert fr.passed
