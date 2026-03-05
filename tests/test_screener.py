"""Tests for stratgen.screener — screen_universe() with synthetic data."""

import pandas as pd
import pytest

from stratgen.screener import screen_universe


def _make_df(n_rows: int, close: float = 100.0, volume: float = 1_000_000) -> pd.DataFrame:
    """Create a synthetic OHLCV DataFrame."""
    dates = pd.bdate_range(end="2025-12-31", periods=n_rows)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": volume,
        },
        index=dates,
    )


class TestScreenUniverse:
    def test_passing_ticker(self) -> None:
        data = {"GOOD": _make_df(600, close=150.0, volume=200_000)}
        passing, results = screen_universe(
            data, min_adv=5_000_000, min_price=10.0,
            min_completeness=0.95, min_history_days=504,
        )
        assert passing == ["GOOD"]
        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].fail_reasons == []
        assert results[0].adv_20d == pytest.approx(150.0 * 200_000)

    def test_failing_adv(self) -> None:
        # close=50, volume=10 -> ADV = 500, below 5M
        data = {"LOW_VOL": _make_df(600, close=50.0, volume=10)}
        passing, results = screen_universe(
            data, min_adv=5_000_000, min_price=10.0,
            min_completeness=0.95, min_history_days=504,
        )
        assert passing == []
        assert results[0].passed is False
        assert any("ADV" in r for r in results[0].fail_reasons)

    def test_failing_price(self) -> None:
        data = {"PENNY": _make_df(600, close=3.0, volume=5_000_000)}
        passing, results = screen_universe(
            data, min_adv=5_000_000, min_price=10.0,
            min_completeness=0.95, min_history_days=504,
        )
        assert passing == []
        assert results[0].passed is False
        assert any("price" in r for r in results[0].fail_reasons)

    def test_failing_completeness(self) -> None:
        # One ticker has 600 rows (max), other has 300 -> 50% completeness
        data = {
            "FULL": _make_df(600, close=100.0, volume=200_000),
            "SHORT": _make_df(300, close=100.0, volume=200_000),
        }
        passing, results = screen_universe(
            data, min_adv=5_000_000, min_price=10.0,
            min_completeness=0.95, min_history_days=250,
        )
        # FULL passes, SHORT fails completeness (300/600 = 0.5)
        assert "FULL" in passing
        assert "SHORT" not in passing
        short_result = [r for r in results if r.ticker == "SHORT"][0]
        assert any("completeness" in r for r in short_result.fail_reasons)

    def test_failing_history_length(self) -> None:
        data = {"NEW": _make_df(100, close=100.0, volume=200_000)}
        passing, results = screen_universe(
            data, min_adv=5_000_000, min_price=10.0,
            min_completeness=0.95, min_history_days=504,
        )
        assert passing == []
        assert results[0].passed is False
        assert any("history" in r for r in results[0].fail_reasons)

    def test_multiple_failures(self) -> None:
        # Fails on price AND history
        data = {"BAD": _make_df(50, close=2.0, volume=1)}
        passing, results = screen_universe(
            data, min_adv=5_000_000, min_price=10.0,
            min_completeness=0.95, min_history_days=504,
        )
        assert passing == []
        assert len(results[0].fail_reasons) >= 2

    def test_empty_universe(self) -> None:
        passing, results = screen_universe({})
        assert passing == []
        assert results == []
