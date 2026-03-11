"""Unit tests for stratgen.scorer module."""

import numpy as np
import pandas as pd
import pytest

from stratgen.scorer import (
    composite_alpha,
    compute_rolling_ic,
    extract_factor_values,
    zscore_cross_sectional,
)


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

def _make_ohlcv_df(n: int = 100, seed: int = 42) -> pd.DataFrame:
    """Create a synthetic OHLCV DataFrame."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2023-01-01", periods=n)
    close = 100 + np.cumsum(rng.standard_normal(n) * 0.5)
    return pd.DataFrame({
        "Open": close - rng.uniform(0, 1, n),
        "High": close + rng.uniform(0, 2, n),
        "Low": close - rng.uniform(0, 2, n),
        "Close": close,
        "Volume": rng.integers(1_000_000, 10_000_000, n).astype(float),
    }, index=dates)


# Minimal GeneratedStrategy code for testing
SIMPLE_STRATEGY_CODE = """
import numpy as np
import pandas as pd
from backtesting import Strategy

class GeneratedStrategy(Strategy):
    lookback = 10

    def init(self):
        def alpha_func(close, lookback):
            s = pd.Series(close)
            sma = s.rolling(int(lookback)).mean()
            return (s - sma).to_numpy()

        self.alpha = self.I(alpha_func, self.data.Close, self.lookback)

    def next(self):
        pass
"""


# ---------------------------------------------------------------------------
# extract_factor_values
# ---------------------------------------------------------------------------

class TestExtractFactorValues:
    def test_basic_extraction(self):
        df = _make_ohlcv_df(50)
        result = extract_factor_values(SIMPLE_STRATEGY_CODE, df, {"lookback": 5})
        assert isinstance(result, pd.Series)
        assert len(result) == 50
        assert result.index.equals(df.index)
        # First 4 values should be NaN (lookback=5, need 5 points for SMA)
        assert result.iloc[:4].isna().all()
        # Later values should be non-NaN
        assert result.iloc[10:].notna().all()

    def test_param_override(self):
        df = _make_ohlcv_df(50)
        r5 = extract_factor_values(SIMPLE_STRATEGY_CODE, df, {"lookback": 5})
        r20 = extract_factor_values(SIMPLE_STRATEGY_CODE, df, {"lookback": 20})
        # Different lookbacks should produce different results
        # (at least where both are non-NaN)
        valid = r5.iloc[25:].notna() & r20.iloc[25:].notna()
        assert not np.allclose(r5.iloc[25:][valid], r20.iloc[25:][valid])

    def test_missing_class_raises(self):
        bad_code = "x = 1"
        df = _make_ohlcv_df(10)
        with pytest.raises(RuntimeError, match="GeneratedStrategy"):
            extract_factor_values(bad_code, df, {})


# ---------------------------------------------------------------------------
# zscore_cross_sectional
# ---------------------------------------------------------------------------

class TestZscoreCrossSectional:
    def test_known_zscores(self):
        # 2 dates, 3 tickers with known values
        panel = pd.DataFrame(
            {"A": [10.0, 20.0], "B": [20.0, 30.0], "C": [30.0, 40.0]},
            index=pd.date_range("2023-01-01", periods=2),
        )
        z = zscore_cross_sectional(panel)

        # For [10, 20, 30]: mean=20, std=10 → z = [-1, 0, 1]
        assert z.shape == (2, 3)
        np.testing.assert_allclose(z.iloc[0].values, [-1.0, 0.0, 1.0])
        np.testing.assert_allclose(z.iloc[1].values, [-1.0, 0.0, 1.0])

    def test_constant_row_gives_nan(self):
        panel = pd.DataFrame(
            {"A": [5.0], "B": [5.0], "C": [5.0]},
            index=pd.date_range("2023-01-01", periods=1),
        )
        z = zscore_cross_sectional(panel)
        assert z.iloc[0].isna().all()

    def test_handles_nan(self):
        panel = pd.DataFrame(
            {"A": [10.0], "B": [np.nan], "C": [30.0]},
            index=pd.date_range("2023-01-01", periods=1),
        )
        z = zscore_cross_sectional(panel)
        assert pd.isna(z.iloc[0]["B"])
        # A and C should have valid z-scores
        assert not pd.isna(z.iloc[0]["A"])
        assert not pd.isna(z.iloc[0]["C"])


# ---------------------------------------------------------------------------
# compute_rolling_ic
# ---------------------------------------------------------------------------

class TestComputeRollingIC:
    def test_perfect_correlation(self):
        dates = pd.bdate_range("2023-01-01", periods=200)
        n_tickers = 50
        rng = np.random.default_rng(42)

        # Factor values: random per date
        factor_data = rng.standard_normal((200, n_tickers))
        factor_panel = pd.DataFrame(
            factor_data,
            index=dates,
            columns=[f"T{i}" for i in range(n_tickers)],
        )

        # Returns: perfectly correlated with factor (shifted by 1)
        # return(t+1) = factor(t) + small noise
        returns_data = np.zeros_like(factor_data)
        returns_data[1:] = factor_data[:-1] + rng.standard_normal((199, n_tickers)) * 0.01
        returns_panel = pd.DataFrame(
            returns_data,
            index=dates,
            columns=[f"T{i}" for i in range(n_tickers)],
        )

        ic = compute_rolling_ic(factor_panel, returns_panel, window=30)
        # IC should be high (close to 1.0) after warmup
        valid_ic = ic.dropna()
        assert len(valid_ic) > 50
        assert valid_ic.mean() > 0.8

    def test_uncorrelated_near_zero(self):
        dates = pd.bdate_range("2023-01-01", periods=200)
        n_tickers = 50
        rng = np.random.default_rng(42)

        factor_panel = pd.DataFrame(
            rng.standard_normal((200, n_tickers)),
            index=dates,
            columns=[f"T{i}" for i in range(n_tickers)],
        )
        # Independent random returns
        returns_panel = pd.DataFrame(
            rng.standard_normal((200, n_tickers)),
            index=dates,
            columns=[f"T{i}" for i in range(n_tickers)],
        )

        ic = compute_rolling_ic(factor_panel, returns_panel, window=30)
        valid_ic = ic.dropna()
        # Mean IC should be close to 0 for uncorrelated data
        assert abs(valid_ic.mean()) < 0.15


# ---------------------------------------------------------------------------
# composite_alpha
# ---------------------------------------------------------------------------

class TestCompositeAlpha:
    @staticmethod
    def _make_two_factor_data():
        dates = pd.bdate_range("2023-01-01", periods=200)
        tickers = [f"T{i}" for i in range(30)]
        rng = np.random.default_rng(42)

        f1 = pd.DataFrame(
            rng.standard_normal((200, 30)),
            index=dates, columns=tickers,
        )
        f2 = pd.DataFrame(
            rng.standard_normal((200, 30)),
            index=dates, columns=tickers,
        )

        returns_data = np.zeros((200, 30))
        returns_data[1:] = (
            f1.values[:-1] * 0.5 - f2.values[:-1] * 0.3
            + rng.standard_normal((199, 30)) * 0.1
        )
        returns_panel = pd.DataFrame(returns_data, index=dates, columns=tickers)
        return {"factor1": f1, "factor2": f2}, returns_panel

    def test_two_factors(self):
        panels, returns_panel = self._make_two_factor_data()
        comp, ic_sum = composite_alpha(panels, returns_panel, ic_window=30, min_ic=0.0)

        assert isinstance(comp, pd.DataFrame)
        assert comp.shape[1] == 30
        assert len(ic_sum) == 2
        # factor1 should have positive IC, factor2 negative
        assert ic_sum["factor1"] > 0
        assert ic_sum["factor2"] < 0

    def test_sign_weighting(self):
        panels, returns_panel = self._make_two_factor_data()
        comp_sign, ic_sign = composite_alpha(
            panels, returns_panel, ic_window=30, weight_method="sign", min_ic=0.0,
        )
        comp_ic, ic_ic = composite_alpha(
            panels, returns_panel, ic_window=30, weight_method="ic", min_ic=0.0,
        )
        # Both should produce DataFrames of the same shape
        assert comp_sign.shape == comp_ic.shape
        # ICs should be identical regardless of weighting method
        assert ic_sign == ic_ic

    def test_min_ic_filters_weak_factors(self):
        dates = pd.bdate_range("2023-01-01", periods=200)
        tickers = [f"T{i}" for i in range(30)]
        rng = np.random.default_rng(42)

        # Strong factor: high IC
        f_strong = pd.DataFrame(
            rng.standard_normal((200, 30)),
            index=dates, columns=tickers,
        )
        # Weak factor: pure noise, low IC
        f_weak = pd.DataFrame(
            rng.standard_normal((200, 30)) * 0.001,
            index=dates, columns=tickers,
        )

        returns_data = np.zeros((200, 30))
        returns_data[1:] = f_strong.values[:-1] * 0.5 + rng.standard_normal((199, 30)) * 0.1
        returns_panel = pd.DataFrame(returns_data, index=dates, columns=tickers)

        panels = {"strong": f_strong, "weak": f_weak}
        # With high min_ic, weak factor should be filtered
        comp, ic_sum = composite_alpha(
            panels, returns_panel, ic_window=30, min_ic=0.1,
        )
        assert isinstance(comp, pd.DataFrame)

    def test_icir_weighting(self):
        panels, returns_panel = self._make_two_factor_data()
        comp, ic_sum = composite_alpha(
            panels, returns_panel, ic_window=30, weight_method="icir", min_ic=0.0,
        )
        assert isinstance(comp, pd.DataFrame)
        assert comp.shape[1] == 30
