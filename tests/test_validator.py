"""Unit tests for stratgen.validator module."""

import numpy as np
import pandas as pd

from stratgen.validator import (
    compute_composite_ic,
    compute_quintile_stats,
    evaluate_composite,
    form_quintile_returns,
    multi_horizon_ic,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_panels(n_dates: int = 200, n_tickers: int = 50, seed: int = 42):
    """Create synthetic alpha and returns panels."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2023-01-01", periods=n_dates)
    tickers = [f"T{i}" for i in range(n_tickers)]

    alpha = pd.DataFrame(
        rng.standard_normal((n_dates, n_tickers)),
        index=dates, columns=tickers,
    )
    returns = pd.DataFrame(
        rng.standard_normal((n_dates, n_tickers)) * 0.02,
        index=dates, columns=tickers,
    )
    return alpha, returns


# ---------------------------------------------------------------------------
# form_quintile_returns
# ---------------------------------------------------------------------------

class TestFormQuintileReturns:
    def test_returns_all_groups(self):
        alpha, returns = _make_panels()
        qr = form_quintile_returns(alpha, returns, n_groups=5, horizon=1)
        assert len(qr) == 5
        for g in range(1, 6):
            assert g in qr
            assert len(qr[g]) > 50  # should have many days

    def test_predictive_alpha_top_beats_bottom(self):
        """When alpha perfectly predicts returns, top quintile should beat bottom."""
        rng = np.random.default_rng(42)
        dates = pd.bdate_range("2023-01-01", periods=200)
        tickers = [f"T{i}" for i in range(50)]

        alpha = pd.DataFrame(
            rng.standard_normal((200, 50)),
            index=dates, columns=tickers,
        )
        # Returns = alpha shifted by 1 day + noise
        ret_data = np.zeros((200, 50))
        ret_data[1:] = alpha.values[:-1] * 0.01 + rng.standard_normal((199, 50)) * 0.001
        returns = pd.DataFrame(ret_data, index=dates, columns=tickers)

        qr = form_quintile_returns(alpha, returns, n_groups=5, horizon=1)
        top_mean = qr[5].mean()
        bottom_mean = qr[1].mean()
        assert top_mean > bottom_mean

    def test_multi_day_horizon(self):
        alpha, returns = _make_panels()
        qr = form_quintile_returns(alpha, returns, n_groups=5, horizon=5)
        assert len(qr) == 5
        for g in range(1, 6):
            assert len(qr[g]) > 0


# ---------------------------------------------------------------------------
# compute_quintile_stats
# ---------------------------------------------------------------------------

class TestComputeQuintileStats:
    def test_stats_keys(self):
        alpha, returns = _make_panels()
        qr = form_quintile_returns(alpha, returns, n_groups=5)
        stats = compute_quintile_stats(qr)
        assert "mean_return_q1" in stats
        assert "mean_return_q5" in stats
        assert "long_short_spread_ann" in stats
        assert "monotonicity" in stats

    def test_monotonic_returns(self):
        """Construct perfectly monotonic group returns."""
        gr = {
            1: pd.Series([0.001] * 100),
            2: pd.Series([0.002] * 100),
            3: pd.Series([0.003] * 100),
        }
        stats = compute_quintile_stats(gr)
        assert stats["monotonicity"] == 1.0
        assert stats["long_short_spread_ann"] > 0


# ---------------------------------------------------------------------------
# compute_composite_ic
# ---------------------------------------------------------------------------

class TestComputeCompositeIC:
    def test_predictive_alpha_positive_ic(self):
        rng = np.random.default_rng(42)
        dates = pd.bdate_range("2023-01-01", periods=200)
        tickers = [f"T{i}" for i in range(50)]

        alpha = pd.DataFrame(
            rng.standard_normal((200, 50)),
            index=dates, columns=tickers,
        )
        ret_data = np.zeros((200, 50))
        ret_data[1:] = alpha.values[:-1] * 0.01 + rng.standard_normal((199, 50)) * 0.001
        returns = pd.DataFrame(ret_data, index=dates, columns=tickers)

        stats = compute_composite_ic(alpha, returns, horizon=1)
        assert stats["mean_ic"] > 0.5
        assert stats["ic_t_stat"] > 3.0
        assert stats["pct_positive"] > 0.7

    def test_random_alpha_near_zero_ic(self):
        alpha, returns = _make_panels()
        stats = compute_composite_ic(alpha, returns, horizon=1)
        assert abs(stats["mean_ic"]) < 0.1

    def test_stats_keys(self):
        alpha, returns = _make_panels()
        stats = compute_composite_ic(alpha, returns, horizon=1)
        for key in ["mean_ic", "ic_std", "ic_t_stat", "ic_ir", "pct_positive", "n_days"]:
            assert key in stats


# ---------------------------------------------------------------------------
# multi_horizon_ic
# ---------------------------------------------------------------------------

class TestMultiHorizonIC:
    def test_returns_all_horizons(self):
        alpha, returns = _make_panels()
        result = multi_horizon_ic(alpha, returns, horizons=[1, 5, 10])
        assert set(result.keys()) == {1, 5, 10}
        for h, stats in result.items():
            assert "mean_ic" in stats


# ---------------------------------------------------------------------------
# evaluate_composite
# ---------------------------------------------------------------------------

class TestEvaluateComposite:
    def test_strong_signal(self):
        ic_stats = {"mean_ic": 0.04, "ic_t_stat": 4.0, "ic_std": 0.01, "ic_ir": 0.5,
                     "pct_positive": 0.6, "n_days": 200}
        q_stats = {"monotonicity": 0.8, "long_short_spread_ann": 0.05,
                    "mean_return_q1": -0.02, "mean_return_q5": 0.03}
        verdict, _ = evaluate_composite(ic_stats, q_stats)
        assert verdict == "STRONG"

    def test_weak_signal(self):
        ic_stats = {"mean_ic": 0.015, "ic_t_stat": 2.0, "ic_std": 0.05, "ic_ir": 0.1,
                     "pct_positive": 0.55, "n_days": 200}
        q_stats = {"monotonicity": 0.6, "long_short_spread_ann": 0.01,
                    "mean_return_q1": -0.01, "mean_return_q5": 0.005}
        verdict, _ = evaluate_composite(ic_stats, q_stats)
        assert verdict == "WEAK"

    def test_no_signal(self):
        ic_stats = {"mean_ic": 0.002, "ic_t_stat": 0.5, "ic_std": 0.05, "ic_ir": 0.01,
                     "pct_positive": 0.51, "n_days": 200}
        q_stats = {"monotonicity": 0.4, "long_short_spread_ann": -0.01,
                    "mean_return_q1": 0.01, "mean_return_q5": -0.005}
        verdict, _ = evaluate_composite(ic_stats, q_stats)
        assert verdict == "NONE"
