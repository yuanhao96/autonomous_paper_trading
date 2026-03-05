"""Core scoring functions: extract factor values, z-score, rolling IC, composite alpha."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy import stats

from stratgen.core import strip_markdown_fences


# ---------------------------------------------------------------------------
# Factor value extraction via mock Strategy
# ---------------------------------------------------------------------------


class _MockStrategy:
    """Lightweight mock that mimics backtesting.Strategy for alpha extraction.

    Avoids inheriting from Strategy (which has a read-only `data` property).
    """

    data: object = None
    I: object = None


def extract_factor_values(code: str, df: pd.DataFrame, params: dict) -> pd.Series:
    """Run GeneratedStrategy.init() with a mock to extract raw alpha values.

    Executes the cached code string, builds a mock object with .data and .I(),
    then calls init() to capture the alpha array.
    """
    code = strip_markdown_fences(code)

    namespace: dict = {}
    exec(code, namespace)  # noqa: S102

    strategy_cls = namespace.get("GeneratedStrategy")
    if strategy_cls is None:
        raise RuntimeError("Code does not define GeneratedStrategy")

    # Build a mock instance that has class-level params, .data, and .I()
    mock = _MockStrategy()

    # Copy class-level attributes (default params) to mock
    for attr in dir(strategy_cls):
        if not attr.startswith("_") and attr not in ("init", "next", "data"):
            try:
                val = getattr(strategy_cls, attr)
                if not callable(val):
                    setattr(mock, attr, val)
            except Exception:
                pass

    # Override with provided params
    for k, v in params.items():
        setattr(mock, k, v)

    # Mock .data with OHLCV arrays
    mock.data = SimpleNamespace(
        Open=df["Open"].values,
        High=df["High"].values,
        Low=df["Low"].values,
        Close=df["Close"].values,
        Volume=df["Volume"].values,
    )

    # Mock .I() — just calls the function and captures result
    captured: list[np.ndarray] = []

    def mock_indicator(func, *args):  # type: ignore[no-untyped-def]
        result = func(*args)
        if isinstance(result, pd.Series):
            result = result.to_numpy()
        result = np.asarray(result, dtype=float)
        captured.append(result)
        return result

    mock.I = mock_indicator  # type: ignore[attr-defined]

    # Call init() bound to our mock
    strategy_cls.init(mock)

    if not captured:
        raise RuntimeError("init() did not call self.I() — no alpha values captured")

    # Use the first captured indicator as the alpha
    alpha_array = captured[0]
    return pd.Series(alpha_array, index=df.index, name="alpha")


# ---------------------------------------------------------------------------
# Panel construction
# ---------------------------------------------------------------------------


def compute_factor_panel(
    factor: dict,
    universe_data: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Compute one factor's values across all tickers.

    Returns DataFrame(index=dates, columns=tickers).
    Tickers that error are filled with NaN.
    """
    code = factor["code"]
    params = factor.get("optimized_params") or factor.get("original_params") or {}

    series_dict: dict[str, pd.Series] = {}
    for ticker, df in universe_data.items():
        try:
            alpha = extract_factor_values(code, df, params)
            series_dict[ticker] = alpha
        except Exception as e:
            print(f"    {ticker}: factor error ({e})")
            continue

    if not series_dict:
        raise RuntimeError(f"Factor {factor.get('name', '?')} failed on all tickers")

    panel = pd.DataFrame(series_dict)
    return panel


# ---------------------------------------------------------------------------
# Cross-sectional z-scoring
# ---------------------------------------------------------------------------


def zscore_cross_sectional(panel: pd.DataFrame) -> pd.DataFrame:
    """Z-score each row (date) across tickers.

    (value - row_mean) / row_std. Rows with std=0 get NaN.
    """
    row_mean = panel.mean(axis=1)
    row_std = panel.std(axis=1)
    # Avoid division by zero
    row_std = row_std.replace(0, np.nan)
    return panel.sub(row_mean, axis=0).div(row_std, axis=0)


# ---------------------------------------------------------------------------
# Rolling Information Coefficient
# ---------------------------------------------------------------------------


def compute_rolling_ic(
    factor_panel: pd.DataFrame,
    returns_panel: pd.DataFrame,
    window: int = 60,
) -> pd.Series:
    """Rolling Spearman IC of factor values vs next-day returns.

    At each date, compute Spearman rank correlation across tickers.
    Returns Series(index=dates) with trailing-window average IC.
    """
    # Forward returns: shift returns back by 1 to align factor(t) with return(t+1)
    fwd_returns = returns_panel.shift(-1)

    common_idx = factor_panel.index.intersection(fwd_returns.index)
    factor_panel = factor_panel.loc[common_idx]
    fwd_returns = fwd_returns.loc[common_idx]

    daily_ics: list[float] = []
    ic_dates: list = []

    for date in common_idx:
        f = factor_panel.loc[date].dropna()
        r = fwd_returns.loc[date].reindex(f.index).dropna()
        common = f.index.intersection(r.index)
        if len(common) < 10:
            daily_ics.append(np.nan)
            ic_dates.append(date)
            continue
        corr, _ = stats.spearmanr(f[common], r[common])
        daily_ics.append(corr if not np.isnan(corr) else np.nan)
        ic_dates.append(date)

    ic_series = pd.Series(daily_ics, index=ic_dates, name="ic")
    # Rolling mean IC over window
    rolling_ic = ic_series.rolling(window, min_periods=max(20, window // 3)).mean()
    return rolling_ic


# ---------------------------------------------------------------------------
# Composite alpha
# ---------------------------------------------------------------------------


def composite_alpha(
    factor_panels: dict[str, pd.DataFrame],
    returns_panel: pd.DataFrame,
    ic_window: int = 60,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """IC-weighted z-score combination of all factors.

    For each factor:
      1. Z-score cross-sectionally
      2. Compute rolling IC (trailing window)
      3. Weight = rolling_ic (sign-adjusted, so positive IC factors get positive weight)
    Composite = sum(z_score_i * ic_weight_i) across factors.

    Returns (composite DataFrame, dict of factor name -> mean IC).
    """
    weighted_sum: pd.DataFrame | None = None
    weight_sum: pd.DataFrame | None = None
    ic_summary: dict[str, float] = {}

    for name, panel in factor_panels.items():
        # 1. Z-score cross-sectionally
        z = zscore_cross_sectional(panel)

        # 2. Compute rolling IC
        rolling_ic = compute_rolling_ic(panel, returns_panel, window=ic_window)

        # Record mean IC for summary
        mean_ic = float(rolling_ic.dropna().mean()) if rolling_ic.dropna().shape[0] > 0 else 0.0
        ic_summary[name] = mean_ic

        # 3. Weight = lagged rolling IC (avoid look-ahead bias)
        # Shift IC by 1 so weight at date t uses IC computed through t-1
        lagged_ic = rolling_ic.shift(1)

        # Broadcast IC (per-date scalar) across tickers
        common_idx = z.index.intersection(lagged_ic.index)
        z_aligned = z.loc[common_idx]
        ic_aligned = lagged_ic.loc[common_idx]

        # Weighted z-score: z * IC_weight
        weighted_z = z_aligned.mul(ic_aligned, axis=0)

        # Accumulate
        if weighted_sum is None:
            weighted_sum = weighted_z.copy()
            weight_sum = ic_aligned.abs().to_frame()
            weight_sum.columns = [name]
        else:
            # Align and add
            weighted_sum, weighted_z = weighted_sum.align(weighted_z, join="inner")
            weighted_sum = weighted_sum.add(weighted_z, fill_value=0)
            ws_col = ic_aligned.abs().reindex(weighted_sum.index)
            weight_sum = weight_sum.reindex(weighted_sum.index)  # type: ignore[union-attr]
            weight_sum[name] = ws_col  # type: ignore[index]

    if weighted_sum is None:
        raise RuntimeError("No factors produced valid panels")

    # Normalize by sum of absolute weights per date
    total_weight = weight_sum.sum(axis=1)  # type: ignore[union-attr]
    total_weight = total_weight.replace(0, np.nan)
    composite = weighted_sum.div(total_weight, axis=0)

    return composite, ic_summary
