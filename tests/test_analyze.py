import numpy as np
import pytest
from analyze import (
    build_df,
    classify_verdict,
    compute_alpha_slope,
    compute_alpha_stability,
    compute_longest_losing_streak,
    compute_max_alpha_drawdown,
    compute_recency_weighted_sharpe,
    compute_regime_robustness,
    compute_trailing_sharpe,
    tag_regime,
)


def _make_result(name, alphas, sharpe=None):
    """Build a minimal result dict from a list of monthly alphas."""
    arr = np.array(alphas)
    if sharpe is None:
        sharpe = float(arr.mean() / arr.std(ddof=1) * np.sqrt(12)) if arr.std() else 0.0
    return {
        "name": name,
        "hypothesis": "test",
        "filters": [],
        "sharpe": sharpe,
        "alpha_monthly_mean": float(arr.mean()),
        "alpha_annual": float(arr.mean() * 12),
        "win_rate": float((arr > 0).mean()),
        "n_months": len(alphas),
        "n_avg_stocks": 20,
        "monthly_details": [
            {"month": f"2024-{i+1:02d}", "port_return": a + 0.01,
             "spy_return": 0.01, "alpha": a, "n_stocks": 20}
            for i, a in enumerate(alphas)
        ],
    }


class TestTrailingSharpe:
    def test_basic(self):
        alphas = [0.01, 0.02, -0.005, 0.015, 0.01, 0.005]
        result = compute_trailing_sharpe(alphas, 6)
        arr = np.array(alphas)
        expected = float(arr.mean() / arr.std(ddof=1) * np.sqrt(12))
        assert result == pytest.approx(expected)

    def test_trailing_window(self):
        """Last 4 of 8 months used when n_months=4."""
        alphas = [-0.1, -0.1, -0.1, -0.1, 0.02, 0.03, 0.01, 0.04]
        full = compute_trailing_sharpe(alphas, 8)
        tail4 = compute_trailing_sharpe(alphas, 4)
        assert tail4 > full  # last 4 are positive, full includes negatives

    def test_too_few_months(self):
        assert np.isnan(compute_trailing_sharpe([0.01, 0.02], 12))

    def test_zero_std(self):
        assert np.isnan(compute_trailing_sharpe([0.01, 0.01, 0.01], 3))


class TestAlphaSlope:
    def test_positive_trend(self):
        alphas = [0.01, 0.02, 0.03, 0.04]
        slope = compute_alpha_slope(alphas)
        assert slope > 0

    def test_negative_trend(self):
        alphas = [0.04, 0.03, 0.02, 0.01]
        slope = compute_alpha_slope(alphas)
        assert slope < 0

    def test_flat(self):
        alphas = [0.02, 0.02, 0.02, 0.02]
        slope = compute_alpha_slope(alphas)
        assert slope == pytest.approx(0.0)

    def test_too_few(self):
        assert np.isnan(compute_alpha_slope([0.01, 0.02]))

    def test_annualized(self):
        """Slope is monthly polyfit * 12."""
        alphas = [0.0, 0.01, 0.02, 0.03]
        slope = compute_alpha_slope(alphas)
        monthly_slope = np.polyfit(range(4), alphas, 1)[0]
        assert slope == pytest.approx(monthly_slope * 12)


class TestRecencyWeightedSharpe:
    def test_recent_positive_beats_old_negative(self):
        """Recent positive alpha should yield higher rw_sharpe than old positive."""
        # Improving: bad then good
        improving = [-0.02, -0.01, 0.01, 0.02, 0.03, 0.04]
        # Declining: good then bad
        declining = [0.04, 0.03, 0.02, 0.01, -0.01, -0.02]
        rw_imp = compute_recency_weighted_sharpe(improving)
        rw_dec = compute_recency_weighted_sharpe(declining)
        assert rw_imp > rw_dec

    def test_too_few(self):
        assert np.isnan(compute_recency_weighted_sharpe([0.01]))


class TestMaxAlphaDrawdown:
    def test_no_drawdown(self):
        alphas = [0.01, 0.02, 0.03]
        assert compute_max_alpha_drawdown(alphas) == pytest.approx(0.0)

    def test_simple_drawdown(self):
        # cumsum: [0.05, 0.05-0.03, 0.05-0.03+0.01] = [0.05, 0.02, 0.03]
        # running_max: [0.05, 0.05, 0.05]
        # drawdown: [0, -0.03, -0.02]
        alphas = [0.05, -0.03, 0.01]
        assert compute_max_alpha_drawdown(alphas) == pytest.approx(-0.03)

    def test_deep_drawdown(self):
        alphas = [0.1, -0.05, -0.05, -0.05, 0.1]
        dd = compute_max_alpha_drawdown(alphas)
        assert dd < -0.1  # cumulative drawdown of three -0.05 months

    def test_empty(self):
        assert np.isnan(compute_max_alpha_drawdown([]))


class TestLongestLosingStreak:
    def test_no_losses(self):
        assert compute_longest_losing_streak([0.01, 0.02, 0.03]) == 0

    def test_all_losses(self):
        assert compute_longest_losing_streak([-0.01, -0.02, -0.03]) == 3

    def test_mixed(self):
        alphas = [0.01, -0.01, -0.02, 0.01, -0.01, -0.02, -0.03, 0.01]
        assert compute_longest_losing_streak(alphas) == 3

    def test_empty(self):
        assert compute_longest_losing_streak([]) == 0


class TestAlphaStability:
    def test_all_positive(self):
        alphas = [0.01, 0.02, 0.03, 0.04, 0.05]
        assert compute_alpha_stability(alphas) == pytest.approx(1.0)

    def test_all_negative(self):
        alphas = [-0.01, -0.02, -0.03, -0.04]
        assert compute_alpha_stability(alphas) == pytest.approx(0.0)

    def test_mixed(self):
        alphas = [0.03, 0.02, -0.01, -0.02, 0.03]
        stability = compute_alpha_stability(alphas, window=3)
        # windows: [.03,.02,-.01]=.013>0, [.02,-.01,-.02]=-.003<0,
        #          [-.01,-.02,.03]=0.0=not>0
        assert stability == pytest.approx(1 / 3)

    def test_too_few(self):
        assert np.isnan(compute_alpha_stability([0.01, 0.02], window=3))


class TestClassifyVerdict:
    def test_keep(self):
        assert classify_verdict(0.5, 0.2) == "KEEP"

    def test_stale(self):
        assert classify_verdict(0.5, -0.1) == "STALE"

    def test_discard(self):
        assert classify_verdict(0.1, 0.5) == "DISCARD"

    def test_nan_trailing_keeps(self):
        """If trailing is NaN (too few months), fall back to full-period."""
        assert classify_verdict(0.5, float("nan")) == "KEEP"
        assert classify_verdict(0.1, float("nan")) == "DISCARD"

    def test_boundary(self):
        assert classify_verdict(0.3, 0.0) == "KEEP"
        assert classify_verdict(0.3, -0.001) == "STALE"
        assert classify_verdict(0.299, 0.5) == "DISCARD"


class TestBuildDf:
    def test_stale_verdict_in_df(self):
        """Screen with good full Sharpe but negative trailing gets STALE."""
        # 24 months: first 12 great, last 12 terrible
        good_then_bad = [0.05] * 12 + [-0.03] * 12
        r = _make_result("decay_screen", good_then_bad, sharpe=0.5)
        df = build_df([r])
        assert df.iloc[0]["status"] == "STALE"
        assert df.iloc[0]["trail_12m_sharpe"] < 0

    def test_keep_verdict_in_df(self):
        """Consistently positive screen stays KEEP."""
        steady = [0.02] * 24
        r = _make_result("steady_screen", steady, sharpe=0.8)
        df = build_df([r])
        assert df.iloc[0]["status"] == "KEEP"
        assert df.iloc[0]["trail_12m_sharpe"] > 0

    def test_discard_verdict_in_df(self):
        """Low full-period Sharpe is always DISCARD."""
        bad = [-0.01] * 12
        r = _make_result("bad_screen", bad, sharpe=0.1)
        df = build_df([r])
        assert df.iloc[0]["status"] == "DISCARD"

    def test_trailing_columns_present(self):
        r = _make_result("test", [0.01] * 12, sharpe=0.5)
        df = build_df([r])
        for col in [
            "trail_12m_sharpe", "trail_6m_sharpe", "alpha_slope", "rw_sharpe",
            "max_dd", "lose_streak", "stability",
        ]:
            assert col in df.columns


class TestTagRegime:
    def test_bull(self):
        assert tag_regime(0.05) == "BULL"
        assert tag_regime(0.021) == "BULL"

    def test_bear(self):
        assert tag_regime(-0.05) == "BEAR"
        assert tag_regime(-0.021) == "BEAR"

    def test_flat(self):
        assert tag_regime(0.01) == "FLAT"
        assert tag_regime(-0.01) == "FLAT"
        assert tag_regime(0.0) == "FLAT"

    def test_boundary(self):
        assert tag_regime(0.02) == "FLAT"
        assert tag_regime(-0.02) == "FLAT"


class TestRegimeRobustness:
    def test_all_regimes_positive(self):
        ra = {"BULL": [0.01, 0.02], "BEAR": [0.005], "FLAT": [0.01]}
        assert compute_regime_robustness(ra) == pytest.approx(1.0)

    def test_one_regime_negative(self):
        ra = {"BULL": [0.02], "BEAR": [-0.03], "FLAT": [0.01]}
        assert compute_regime_robustness(ra) == pytest.approx(2 / 3)

    def test_all_negative(self):
        ra = {"BULL": [-0.01], "BEAR": [-0.02], "FLAT": [-0.01]}
        assert compute_regime_robustness(ra) == pytest.approx(0.0)

    def test_missing_regimes(self):
        ra = {"BULL": [0.01]}
        assert compute_regime_robustness(ra) == pytest.approx(1.0)

    def test_empty(self):
        assert np.isnan(compute_regime_robustness({}))
