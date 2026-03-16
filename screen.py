"""Evaluate stock screens against cached S&P 500 data."""
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path("data")


def compute_price_features(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute price-derived features from OHLCV data.

    Input: MultiIndex columns (field, ticker) with fields: Open, High, Low, Close, Volume
    Output: MultiIndex columns (feature, ticker) — one row per trading day.
    """
    close = prices["Close"]
    high = prices["High"]
    volume = prices["Volume"]

    features = {}

    # Returns
    features["return_1m"] = close.pct_change(21)
    features["return_3m"] = close.pct_change(63)
    features["return_6m"] = close.pct_change(126)
    features["return_12m"] = close.pct_change(252)

    # Moving average ratios
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    features["close_vs_sma50"] = close / sma50
    features["close_vs_sma200"] = close / sma200
    features["sma50_vs_sma200"] = sma50 / sma200

    # 52-week high/low
    high_52w = high.rolling(252).max()
    low_52w = close.rolling(252).min()
    features["high_52w_pct"] = close / high_52w
    features["low_52w_pct"] = close / low_52w

    # Volatility
    daily_ret = close.pct_change()
    features["volatility_20d"] = daily_ret.rolling(20).std() * np.sqrt(252)
    features["volatility_60d"] = daily_ret.rolling(60).std() * np.sqrt(252)

    # Volume
    dollar_vol = close * volume
    features["avg_volume_20d"] = dollar_vol.rolling(20).mean()
    features["volume_ratio"] = dollar_vol.rolling(5).mean() / dollar_vol.rolling(20).mean()

    # Drawdown
    rolling_max = close.rolling(252, min_periods=1).max()
    features["drawdown"] = close / rolling_max - 1

    return pd.concat(features, axis=1)


def compute_fundamental_features(financials: pd.DataFrame,
                                  prices: pd.DataFrame) -> pd.DataFrame:
    """Compute fundamental features from quarterly financials.

    Growth metrics are computed at the quarterly level (using shift(4) for YoY,
    shift(1) for QoQ) BEFORE forward-filling to daily frequency.
    """
    close = prices["Close"]
    date_index = close.index

    # Pivot financials: for each field, create (date x ticker) quarterly DataFrame
    def pivot_quarterly(df, field):
        """Pivot to (quarterly_date x ticker), no forward-fill yet."""
        if field not in df.columns:
            return None
        sub = df[df[field].notna()][["ticker", "date", field]].copy()
        sub = sub.drop_duplicates(subset=["ticker", "date"], keep="last")
        piv = sub.pivot(index="date", columns="ticker", values=field)
        return piv.sort_index()

    def ffill_to_daily(quarterly_df):
        """Forward-fill quarterly data to daily price index."""
        if quarterly_df is None:
            return None
        return quarterly_df.reindex(date_index, method="ffill")

    # Try both naming conventions (yfinance varies)
    def get_field(name1, name2):
        result = pivot_quarterly(financials, name1)
        if result is not None:
            return result
        return pivot_quarterly(financials, name2)

    # Raw quarterly data (NOT forward-filled yet)
    revenue_q = get_field("Total Revenue", "TotalRevenue")
    gross_profit_q = get_field("Gross Profit", "GrossProfit")
    operating_income_q = get_field("Operating Income", "OperatingIncome")
    net_income_q = get_field("Net Income", "NetIncome")
    total_assets_q = get_field("Total Assets", "TotalAssets")
    equity_q = get_field("Stockholders Equity", "StockholdersEquity")
    total_debt_q = get_field("Total Debt", "TotalDebt")
    current_assets_q = get_field("Current Assets", "CurrentAssets")
    current_liab_q = get_field("Current Liabilities", "CurrentLiabilities")

    features = {}

    # NOTE: yfinance only gives ~6 quarters. Growth metrics (shift(1) for QoQ,
    # shift(4) for YoY) produce almost all NaN. Only level features work.

    # Margins — computed at quarterly level, then forward-filled
    if gross_profit_q is not None and revenue_q is not None:
        gm_q = gross_profit_q / revenue_q.abs().clip(lower=1)
        features["gross_margin"] = ffill_to_daily(gm_q)

    if operating_income_q is not None and revenue_q is not None:
        om_q = operating_income_q / revenue_q.abs().clip(lower=1)
        features["operating_margin"] = ffill_to_daily(om_q)

    if net_income_q is not None and revenue_q is not None:
        features["net_margin"] = ffill_to_daily(net_income_q / revenue_q.abs().clip(lower=1))

    # Returns on capital (annualized: multiply quarterly by 4)
    if net_income_q is not None and total_assets_q is not None:
        features["roa"] = ffill_to_daily(
            (net_income_q * 4) / total_assets_q.abs().clip(lower=1)
        )

    if net_income_q is not None and equity_q is not None:
        features["roe"] = ffill_to_daily(
            (net_income_q * 4) / equity_q.abs().clip(lower=1)
        )

    # Balance sheet ratios
    if total_debt_q is not None and equity_q is not None:
        features["debt_to_equity"] = ffill_to_daily(
            total_debt_q / equity_q.abs().clip(lower=1)
        )

    if current_assets_q is not None and current_liab_q is not None:
        features["current_ratio"] = ffill_to_daily(
            current_assets_q / current_liab_q.abs().clip(lower=1)
        )

    if not features:
        return pd.DataFrame(index=date_index)

    return pd.concat(features, axis=1)


def compute_sector_features(features: pd.DataFrame,
                             sector_map: dict[str, str]) -> pd.DataFrame:
    """Compute sector-level and sector-relative features.

    sector_map: {ticker: sector_name}
    features: existing MultiIndex (feature, ticker) DataFrame

    Returns new features with same MultiIndex structure.
    """
    tickers = features.columns.get_level_values(1).unique()
    # Only include tickers that have a sector mapping
    mapped = {t: sector_map[t] for t in tickers if t in sector_map}
    sectors_series = pd.Series(mapped)  # ticker -> sector

    result = {}

    # --- Sector momentum: median return of the sector ---
    for ret_feat in ["return_1m", "return_3m"]:
        if ret_feat not in features.columns.get_level_values(0):
            continue
        ret_data = features[ret_feat]  # (dates x tickers)
        sector_med = pd.DataFrame(index=ret_data.index, columns=ret_data.columns)
        for sector, sector_tickers in sectors_series.groupby(sectors_series):
            st = [t for t in sector_tickers.index if t in ret_data.columns]
            if st:
                med = ret_data[st].median(axis=1)
                for t in st:
                    sector_med[t] = med
        result[f"sector_{ret_feat}"] = sector_med

    # --- Relative strength vs sector (subtraction for returns) ---
    for ret_feat in ["return_1m", "return_6m"]:
        if ret_feat not in features.columns.get_level_values(0):
            continue
        ret_data = features[ret_feat]
        vs_sector = pd.DataFrame(index=ret_data.index, columns=ret_data.columns, dtype=float)
        for sector, sector_tickers in sectors_series.groupby(sectors_series):
            st = [t for t in sector_tickers.index if t in ret_data.columns]
            if st:
                med = ret_data[st].median(axis=1)
                for t in st:
                    vs_sector[t] = ret_data[t] - med
        result[f"{ret_feat}_vs_sector"] = vs_sector

    # --- Relative quality vs sector (ratio for margins/ratios) ---
    for qual_feat in ["gross_margin", "roe", "volatility_20d"]:
        if qual_feat not in features.columns.get_level_values(0):
            continue
        feat_data = features[qual_feat]
        vs_sector = pd.DataFrame(index=feat_data.index, columns=feat_data.columns, dtype=float)
        for sector, sector_tickers in sectors_series.groupby(sectors_series):
            st = [t for t in sector_tickers.index if t in feat_data.columns]
            if st:
                med = feat_data[st].median(axis=1)
                # Avoid division by zero
                safe_med = med.replace(0, np.nan)
                for t in st:
                    vs_sector[t] = feat_data[t] / safe_med
        result[f"{qual_feat}_vs_sector"] = vs_sector

    # --- Sector breadth: fraction of sector above SMA200 ---
    if "close_vs_sma200" in features.columns.get_level_values(0):
        sma_data = features["close_vs_sma200"]
        breadth = pd.DataFrame(index=sma_data.index, columns=sma_data.columns, dtype=float)
        for sector, sector_tickers in sectors_series.groupby(sectors_series):
            st = [t for t in sector_tickers.index if t in sma_data.columns]
            if st:
                above = (sma_data[st] > 1.0).sum(axis=1) / len(st)
                for t in st:
                    breadth[t] = above
        result["sector_breadth"] = breadth

    if not result:
        return pd.DataFrame(index=features.index)

    return pd.concat(result, axis=1)


def compute_stability_features(financials: pd.DataFrame,
                                prices: pd.DataFrame) -> pd.DataFrame:
    """Compute margin/return stability from quarterly data.

    Lower values = more stable = potential moat signal.
    """
    close = prices["Close"]
    date_index = close.index

    def pivot_quarterly(df, field):
        if field not in df.columns:
            return None
        sub = df[df[field].notna()][["ticker", "date", field]].copy()
        sub = sub.drop_duplicates(subset=["ticker", "date"], keep="last")
        piv = sub.pivot(index="date", columns="ticker", values=field)
        return piv.sort_index()

    def get_field(name1, name2):
        result = pivot_quarterly(financials, name1)
        if result is not None:
            return result
        return pivot_quarterly(financials, name2)

    revenue_q = get_field("Total Revenue", "TotalRevenue")
    gross_profit_q = get_field("Gross Profit", "GrossProfit")
    operating_income_q = get_field("Operating Income", "OperatingIncome")
    net_income_q = get_field("Net Income", "NetIncome")
    equity_q = get_field("Stockholders Equity", "StockholdersEquity")

    def per_ticker_expanding_std(quarterly_df):
        """Compute expanding std per ticker over their own quarterly values.

        Handles tickers reporting on different fiscal dates by computing
        per-column (ticker) expanding std, ignoring NaN rows for each ticker.
        """
        result = pd.DataFrame(index=quarterly_df.index, columns=quarterly_df.columns,
                              dtype=float)
        for ticker in quarterly_df.columns:
            vals = quarterly_df[ticker].dropna()
            if len(vals) >= 3:
                # Expanding std over this ticker's actual quarterly values
                exp_std = vals.expanding(min_periods=3).std()
                result[ticker] = exp_std.reindex(quarterly_df.index)
        return result

    features = {}

    # Stability = expanding std over available quarters (lower = more stable)
    if gross_profit_q is not None and revenue_q is not None:
        gm_q = gross_profit_q / revenue_q.abs().clip(lower=1)
        gm_std = per_ticker_expanding_std(gm_q)
        features["gross_margin_stability"] = gm_std.reindex(date_index, method="ffill")

    if operating_income_q is not None and revenue_q is not None:
        om_q = operating_income_q / revenue_q.abs().clip(lower=1)
        om_std = per_ticker_expanding_std(om_q)
        features["operating_margin_stability"] = om_std.reindex(date_index, method="ffill")

    if net_income_q is not None and equity_q is not None:
        roe_q = (net_income_q * 4) / equity_q.abs().clip(lower=1)
        roe_std = per_ticker_expanding_std(roe_q)
        features["roe_stability"] = roe_std.reindex(date_index, method="ffill")

    if not features:
        return pd.DataFrame(index=date_index)

    return pd.concat(features, axis=1)


def compute_regime(prices: pd.DataFrame) -> pd.Series:
    """Classify each trading day into one of 4 market regimes.

    Uses SPY price data on two axes:
    - Trend: SPY close vs SMA(200). Above = uptrend, below = downtrend.
    - Volatility: SPY 20d realized vol vs its expanding median.
      Above median = high vol, below = low vol.

    Returns Series of regime labels indexed by date:
    quiet_bull, volatile_bull, quiet_bear, volatile_bear.
    """
    spy_close = prices["Close"]["SPY"]

    # Trend axis: close vs SMA(200)
    sma200 = spy_close.rolling(200).mean()
    is_uptrend = spy_close >= sma200

    # Volatility axis: 20d realized vol vs expanding median
    daily_ret = spy_close.pct_change()
    vol_20d = daily_ret.rolling(20).std() * np.sqrt(252)
    vol_median = vol_20d.expanding().median()
    is_high_vol = vol_20d >= vol_median

    regime = pd.Series(index=spy_close.index, dtype="object")
    regime[is_uptrend & ~is_high_vol] = "quiet_bull"
    regime[is_uptrend & is_high_vol] = "volatile_bull"
    regime[~is_uptrend & ~is_high_vol] = "quiet_bear"
    regime[~is_uptrend & is_high_vol] = "volatile_bear"

    return regime


def compute_pctrank_features(features: pd.DataFrame) -> pd.DataFrame:
    """Compute cross-sectional percentile ranks for all numeric features.

    For each feature, ranks stocks from 0 (lowest) to 1 (highest) at each
    date independently. NaN values remain NaN.

    Returns MultiIndex (feature_pctrank, ticker) DataFrame.
    """
    feature_names = features.columns.get_level_values(0).unique()
    result = {}
    for feat in feature_names:
        feat_data = features[feat]
        # rank across tickers (axis=1) at each date — cross-sectional
        ranked = feat_data.rank(axis=1, pct=True, na_option="keep")
        result[f"{feat}_pctrank"] = ranked
    return pd.concat(result, axis=1)


def compute_all_features() -> pd.DataFrame:
    """Load cached data and compute all features. Returns combined DataFrame."""
    prices = pd.read_parquet(DATA_DIR / "prices.parquet")
    financials = pd.read_parquet(DATA_DIR / "financials.parquet")

    price_feat = compute_price_features(prices)
    fund_feat = compute_fundamental_features(financials, prices)

    # Combine price + fundamental
    combined = pd.concat([price_feat, fund_feat], axis=1)

    # Sector-relative features
    sectors_path = DATA_DIR / "sectors.parquet"
    if sectors_path.exists():
        sectors_df = pd.read_parquet(sectors_path)
        sector_map = dict(zip(sectors_df["ticker"], sectors_df["sector"]))
        sector_feat = compute_sector_features(combined, sector_map)
        combined = pd.concat([combined, sector_feat], axis=1)

    # Stability features
    stability_feat = compute_stability_features(financials, prices)
    combined = pd.concat([combined, stability_feat], axis=1)

    # Percentile rank features (cross-sectional per date)
    pctrank_feat = compute_pctrank_features(combined)
    combined = pd.concat([combined, pctrank_feat], axis=1)

    # Market regime (broadcast to all tickers)
    regime = compute_regime(prices)
    tickers = combined.columns.get_level_values(1).unique()
    regime_df = pd.DataFrame(
        {("market_regime", t): regime for t in tickers},
        index=combined.index,
    )
    regime_df.columns = pd.MultiIndex.from_tuples(regime_df.columns)
    combined = pd.concat([combined, regime_df], axis=1)

    return combined


def _apply_filters(features: pd.DataFrame, filters: list[dict],
                   date: pd.Timestamp) -> list[str]:
    """Apply filter list at a single date. Returns sorted list of tickers passing all filters."""
    # Get all tickers
    all_tickers = features.columns.get_level_values(1).unique().tolist()
    passing = set(all_tickers)

    for f in filters:
        feat_name = f["feature"]
        op = f["op"]
        val = f["value"]

        if feat_name not in features.columns.get_level_values(0):
            continue  # Unknown feature — skip filter

        series = features.loc[date, feat_name] if date in features.index else pd.Series()
        if series.empty:
            return []

        if op == ">":
            mask = series > val
        elif op == ">=":
            mask = series >= val
        elif op == "<":
            mask = series < val
        elif op == "<=":
            mask = series <= val
        elif op == "==":
            mask = series == val
        elif op == "!=":
            mask = series != val
        elif op == "between":
            if not isinstance(val, list) or len(val) != 2:
                continue
            mask = (series >= val[0]) & (series <= val[1])
        else:
            continue

        passing &= set(mask[mask].index.tolist())

    return sorted(passing)


def _compute_composite_score(
    score_def: list[dict], features: pd.DataFrame,
    date: pd.Timestamp, tickers: list[str],
) -> pd.Series:
    """Compute weighted composite score for tickers at a date.

    Args:
        score_def: List of {"feature": str, "weight": float} dicts.
        features: Full feature matrix (MultiIndex columns).
        date: Rebalance date.
        tickers: List of tickers to score.

    Returns:
        Series indexed by ticker with composite scores. Features not
        in the matrix are skipped (contribute 0). NaN propagates from
        individual feature values.
    """
    scores = pd.Series(0.0, index=tickers)
    feat_names = features.columns.get_level_values(0).unique()
    for term in score_def:
        feat = term["feature"]
        weight = term["weight"]
        if feat not in feat_names:
            continue
        vals = features.loc[date, feat] if date in features.index else pd.Series()
        vals = vals.reindex(tickers)
        scores = scores + weight * vals
    return scores


def _rank_and_select(passing: list[str], features: pd.DataFrame,
                     date: pd.Timestamp, screen_def: dict) -> list[str]:
    """Rank passing tickers by rank_by feature or composite score."""
    top_n = screen_def.get("top_n", 20)
    rank_by = screen_def.get("rank_by")
    score_def = screen_def.get("score")

    # Composite score ranking
    if rank_by == "_score" and score_def:
        scores = _compute_composite_score(score_def, features, date, passing)
        scores = scores.dropna()
        if scores.empty:
            return passing[:top_n]
        rank_order = screen_def.get("rank_order", "desc")
        ascending = rank_order != "desc"
        ranked = scores.sort_values(ascending=ascending).index.tolist()
        return ranked[:top_n]

    # Standard feature ranking
    if not rank_by or rank_by not in features.columns.get_level_values(0):
        return passing[:top_n]  # Alphabetical fallback

    rank_order = screen_def.get("rank_order", "desc")
    vals = features.loc[date, rank_by] if date in features.index else pd.Series()
    vals = vals.reindex(passing).dropna()
    if vals.empty:
        return passing[:top_n]

    ascending = rank_order != "desc"
    ranked = vals.sort_values(ascending=ascending).index.tolist()
    return ranked[:top_n]


def _compute_sharpe(alpha: np.ndarray, periods_per_year: float) -> float:
    """Compute annualized Sharpe ratio from an array of alpha values."""
    if len(alpha) < 2:
        return 0.0
    alpha_std = float(np.std(alpha))
    if alpha_std == 0:
        return 0.0
    return float(np.mean(alpha)) / alpha_std * np.sqrt(periods_per_year)


def _compute_regime_stats(
    monthly_details: list[dict],
    regime_series: pd.Series,
) -> dict:
    """Compute per-regime alpha stats from monthly_details."""
    regime_alphas = {}
    for md in monthly_details:
        date = pd.Timestamp(md["month"])
        # Find closest date in regime_series (rebal date may not align exactly)
        idx = regime_series.index.get_indexer([date], method="ffill")
        if idx[0] >= 0:
            label = regime_series.iloc[idx[0]]
        else:
            label = "unknown"
        regime_alphas.setdefault(label, []).append(md["alpha"])

    stats = {}
    for label, alphas in regime_alphas.items():
        arr = np.array(alphas)
        stats[label] = {
            "alpha_mean": round(float(np.mean(arr)), 5),
            "win_rate": round(float(np.mean(arr > 0)), 3),
            "n_months": len(arr),
        }
    return stats


def generate_wf_windows(
    dates: pd.DatetimeIndex,
    train_months: int = 18,
    test_months: int = 6,
) -> list[tuple]:
    """Generate rolling walk-forward windows from a date index.

    Returns list of (train_start, train_end, test_start, test_end) tuples.
    Windows roll forward by test_months. Test periods do not overlap.
    """
    from dateutil.relativedelta import relativedelta

    windows = []
    train_start = dates[0]

    while True:
        train_end_cal = train_start + relativedelta(months=train_months)
        test_start_cal = train_end_cal
        test_end_cal = test_start_cal + relativedelta(months=test_months)

        train_start_idx = dates.searchsorted(train_start)
        train_end_idx = dates.searchsorted(train_end_cal)
        test_start_idx = train_end_idx
        test_end_idx = dates.searchsorted(test_end_cal)

        if test_end_idx >= len(dates):
            test_end_idx = len(dates) - 1
        if train_end_idx >= len(dates) or test_start_idx >= test_end_idx:
            break

        windows.append((
            dates[train_start_idx],
            dates[train_end_idx - 1],
            dates[test_start_idx],
            dates[test_end_idx],
        ))

        train_start = train_start + relativedelta(months=test_months)

    return windows


def _backtest_period(
    screen_def: dict,
    features: pd.DataFrame,
    close: pd.DataFrame,
    spy: pd.Series | None,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
) -> tuple[list, list, list, list]:
    """Run backtest over a single period.

    Returns (port_returns, spy_returns, monthly_details, n_stocks_list).
    """
    filters = screen_def.get("filters", [])
    holding_days = screen_def.get("holding_days", 21)

    date_range = close.loc[start:end].index
    rebal_indices = list(range(0, len(date_range), holding_days))

    portfolio_returns = []
    spy_returns = []
    n_stocks_list = []
    monthly_details = []

    for i in range(len(rebal_indices) - 1):
        rebal_date = date_range[rebal_indices[i]]
        next_date = date_range[rebal_indices[i + 1]]

        passing = _apply_filters(features, filters, rebal_date)
        if len(passing) == 0:
            continue

        tickers = _rank_and_select(
            passing, features, rebal_date, screen_def,
        )

        stock_rets = {}
        for t in tickers:
            if t in close.columns:
                p0 = (
                    close.loc[rebal_date, t]
                    if rebal_date in close.index else np.nan
                )
                p1 = (
                    close.loc[next_date, t]
                    if next_date in close.index else np.nan
                )
                if pd.notna(p0) and pd.notna(p1) and p0 > 0:
                    stock_rets[t] = round(p1 / p0 - 1, 5)

        if len(stock_rets) == 0:
            continue

        port_ret = np.mean(list(stock_rets.values()))
        portfolio_returns.append(port_ret)
        n_stocks_list.append(len(stock_rets))

        spy_ret = 0.0
        if spy is not None:
            s0 = (
                spy.loc[rebal_date]
                if rebal_date in spy.index else np.nan
            )
            s1 = (
                spy.loc[next_date]
                if next_date in spy.index else np.nan
            )
            if pd.notna(s0) and pd.notna(s1) and s0 > 0:
                spy_ret = s1 / s0 - 1
        spy_returns.append(spy_ret)

        monthly_details.append({
            "month": str(rebal_date.date()),
            "stocks": stock_rets,
            "port_return": round(float(port_ret), 5),
            "spy_return": round(float(spy_ret), 5),
            "alpha": round(float(port_ret - spy_ret), 5),
        })

    return portfolio_returns, spy_returns, monthly_details, n_stocks_list


def apply_screen(
    screen_def: dict,
    features: pd.DataFrame,
    start: str = "2015-01-01",
    end: str = "2025-12-31",
    walk_forward: bool = False,
    train_months: int = 18,
    test_months: int = 6,
) -> dict:
    """Backtest a screen: rebalance every holding_days, equal-weight top_n.

    Args:
        walk_forward: If True, use rolling walk-forward evaluation.
            Verdict uses mean OOS Sharpe across windows.
        train_months: Walk-forward train window in months.
        test_months: Walk-forward test window in months.
    """
    prices = pd.read_parquet(DATA_DIR / "prices.parquet")
    close = prices["Close"]
    spy = close["SPY"] if "SPY" in close.columns else None

    filters = screen_def.get("filters", [])
    holding_days = screen_def.get("holding_days", 21)
    periods_per_year = 252 / holding_days

    # Full-period backtest (always run for overall metrics)
    port_rets, spy_rets, monthly_details, n_stocks_list = (
        _backtest_period(screen_def, features, close, spy, start, end)
    )

    if len(port_rets) == 0:
        result = {
            "name": screen_def.get("name", ""),
            "hypothesis": screen_def.get("hypothesis", ""),
            "filters": filters,
            "alpha_monthly_mean": 0.0,
            "sharpe": 0.0,
            "win_rate": 0.0,
            "n_months": 0,
            "n_avg_stocks": 0,
            "monthly_details": [],
            "verdict": "NO DATA",
        }
        if walk_forward:
            result.update({
                "wf_oos_sharpe_mean": 0.0,
                "wf_oos_sharpe_std": 0.0,
                "wf_n_windows": 0,
                "wf_windows": [],
            })
        return result

    port = np.array(port_rets)
    spy_r = np.array(spy_rets[:len(port)])
    alpha = port - spy_r

    alpha_mean = float(np.mean(alpha))
    sharpe = _compute_sharpe(alpha, periods_per_year)

    # Walk-forward evaluation
    wf_result = {}
    if walk_forward:
        date_range = close.loc[start:end].index
        windows = generate_wf_windows(
            date_range, train_months, test_months,
        )

        wf_windows = []
        for tr_start, tr_end, te_start, te_end in windows:
            is_rets, is_spy, _, _ = _backtest_period(
                screen_def, features, close, spy,
                tr_start, tr_end,
            )
            oos_rets, oos_spy, _, _ = _backtest_period(
                screen_def, features, close, spy,
                te_start, te_end,
            )
            is_alpha = (
                np.array(is_rets) - np.array(is_spy[:len(is_rets)])
                if is_rets else np.array([])
            )
            oos_alpha = (
                np.array(oos_rets) - np.array(oos_spy[:len(oos_rets)])
                if oos_rets else np.array([])
            )

            wf_windows.append({
                "train_start": str(tr_start.date()),
                "train_end": str(tr_end.date()),
                "test_start": str(te_start.date()),
                "test_end": str(te_end.date()),
                "sharpe_is": round(
                    _compute_sharpe(is_alpha, periods_per_year), 3,
                ),
                "sharpe_oos": round(
                    _compute_sharpe(oos_alpha, periods_per_year), 3,
                ),
                "n_months_is": len(is_alpha),
                "n_months_oos": len(oos_alpha),
            })

        oos_sharpes = [
            w["sharpe_oos"] for w in wf_windows
            if w["n_months_oos"] > 0
        ]
        wf_oos_mean = (
            float(np.mean(oos_sharpes)) if oos_sharpes else 0.0
        )
        wf_oos_std = (
            float(np.std(oos_sharpes)) if oos_sharpes else 0.0
        )

        wf_result = {
            "wf_oos_sharpe_mean": round(wf_oos_mean, 3),
            "wf_oos_sharpe_std": round(wf_oos_std, 3),
            "wf_n_windows": len(wf_windows),
            "wf_windows": wf_windows,
        }

    # Verdict
    if walk_forward:
        verdict_sharpe = wf_result.get("wf_oos_sharpe_mean", 0.0)
    else:
        verdict_sharpe = sharpe

    result = {
        "name": screen_def.get("name", ""),
        "hypothesis": screen_def.get("hypothesis", ""),
        "filters": filters,
        "holding_days": holding_days,
        "rank_by": screen_def.get("rank_by"),
        "rank_order": (
            screen_def.get("rank_order", "desc")
            if screen_def.get("rank_by") else None
        ),
        "score": screen_def.get("score"),
        "alpha_monthly_mean": round(alpha_mean, 5),
        "alpha_annual": round(alpha_mean * periods_per_year, 4),
        "sharpe": round(sharpe, 3),
        "win_rate": round(float(np.mean(alpha > 0)), 3),
        "n_months": len(port),
        "n_avg_stocks": round(float(np.mean(n_stocks_list)), 1),
        "port_total_return": round(
            float(np.prod(1 + port) - 1), 4,
        ),
        "spy_total_return": round(
            float(np.prod(1 + spy_r) - 1), 4,
        ),
        "monthly_details": [
            {
                "month": md["month"],
                "port_return": md["port_return"],
                "spy_return": md["spy_return"],
                "alpha": md["alpha"],
                "n_stocks": len(md["stocks"]),
            }
            for md in monthly_details
        ],
        "stock_details": [
            {"month": md["month"], "stocks": md["stocks"]}
            for md in monthly_details
        ],
        "verdict": "KEEP" if verdict_sharpe >= 0.3 else "DISCARD",
    }
    result.update(wf_result)

    return result
