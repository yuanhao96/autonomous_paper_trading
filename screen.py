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
        return pivot_quarterly(financials, name1) or pivot_quarterly(financials, name2)

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

    # Growth metrics — computed at quarterly level BEFORE forward-filling
    # shift(4) = 4 quarters ago (YoY), shift(1) = 1 quarter ago (QoQ)
    if revenue_q is not None:
        rev_yoy_q = (revenue_q - revenue_q.shift(4)) / revenue_q.shift(4).abs().clip(lower=1)
        rev_qoq_q = (revenue_q - revenue_q.shift(1)) / revenue_q.shift(1).abs().clip(lower=1)
        rev_accel_q = rev_yoy_q - rev_yoy_q.shift(1)
        features["revenue_growth_yoy"] = ffill_to_daily(rev_yoy_q)
        features["revenue_growth_qoq"] = ffill_to_daily(rev_qoq_q)
        features["revenue_acceleration"] = ffill_to_daily(rev_accel_q)

    if net_income_q is not None:
        ni_yoy_q = (
            (net_income_q - net_income_q.shift(4)) / net_income_q.shift(4).abs().clip(lower=1)
        )
        features["earnings_growth_yoy"] = ffill_to_daily(ni_yoy_q)

    # Margins — computed at quarterly level, then forward-filled
    if gross_profit_q is not None and revenue_q is not None:
        gm_q = gross_profit_q / revenue_q.abs().clip(lower=1)
        features["gross_margin"] = ffill_to_daily(gm_q)
        features["gross_margin_change"] = ffill_to_daily(gm_q - gm_q.shift(1))

    if operating_income_q is not None and revenue_q is not None:
        om_q = operating_income_q / revenue_q.abs().clip(lower=1)
        features["operating_margin"] = ffill_to_daily(om_q)
        features["operating_margin_change"] = ffill_to_daily(om_q - om_q.shift(1))

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


def compute_all_features() -> pd.DataFrame:
    """Load cached data and compute all features. Returns combined DataFrame."""
    prices = pd.read_parquet(DATA_DIR / "prices.parquet")
    financials = pd.read_parquet(DATA_DIR / "financials.parquet")

    price_feat = compute_price_features(prices)
    fund_feat = compute_fundamental_features(financials, prices)

    # Combine: both have MultiIndex columns (feature, ticker)
    combined = pd.concat([price_feat, fund_feat], axis=1)
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


def apply_screen(screen_def: dict, features: pd.DataFrame,
                 start: str = "2020-01-01", end: str = "2025-12-31") -> dict:
    """Backtest a screen: monthly rebalance, equal-weight top_n, measure vs SPY.

    Returns dict with backtest results.
    """
    prices = pd.read_parquet(DATA_DIR / "prices.parquet")
    close = prices["Close"]
    spy = close["SPY"] if "SPY" in close.columns else None

    top_n = screen_def.get("top_n", 20)
    filters = screen_def["filters"]

    # Monthly rebalance dates
    date_range = close.loc[start:end].index
    monthly = date_range.to_series().groupby(pd.Grouper(freq="MS")).first().dropna()

    portfolio_returns = []
    spy_returns = []
    n_stocks_list = []

    for i in range(len(monthly) - 1):
        rebal_date = monthly.iloc[i]
        next_date = monthly.iloc[i + 1]

        # Get tickers passing screen
        passing = _apply_filters(features, filters, rebal_date)
        if len(passing) == 0:
            continue

        # If more pass than top_n, take alphabetically (deterministic).
        tickers = passing[:top_n]

        # Equal-weight 1-month return
        rets = []
        for t in tickers:
            if t in close.columns:
                p0 = close.loc[rebal_date, t] if rebal_date in close.index else np.nan
                p1 = close.loc[next_date, t] if next_date in close.index else np.nan
                if pd.notna(p0) and pd.notna(p1) and p0 > 0:
                    rets.append(p1 / p0 - 1)

        if len(rets) == 0:
            continue

        port_ret = np.mean(rets)
        portfolio_returns.append(port_ret)
        n_stocks_list.append(len(rets))

        # SPY return for same period
        if spy is not None:
            s0 = spy.loc[rebal_date] if rebal_date in spy.index else np.nan
            s1 = spy.loc[next_date] if next_date in spy.index else np.nan
            if pd.notna(s0) and pd.notna(s1) and s0 > 0:
                spy_returns.append(s1 / s0 - 1)
            else:
                spy_returns.append(0.0)

    if len(portfolio_returns) == 0:
        return {
            "name": screen_def.get("name", ""),
            "hypothesis": screen_def.get("hypothesis", ""),
            "filters": filters,
            "alpha_monthly_mean": 0.0,
            "sharpe": 0.0,
            "win_rate": 0.0,
            "n_months": 0,
            "n_avg_stocks": 0,
            "verdict": "NO DATA",
        }

    port = np.array(portfolio_returns)
    spy_r = np.array(spy_returns[:len(port)])
    alpha = port - spy_r

    alpha_mean = float(np.mean(alpha))
    alpha_std = float(np.std(alpha)) if len(alpha) > 1 else 1.0
    sharpe = alpha_mean / alpha_std * np.sqrt(12) if alpha_std > 0 else 0.0

    return {
        "name": screen_def.get("name", ""),
        "hypothesis": screen_def.get("hypothesis", ""),
        "filters": filters,
        "alpha_monthly_mean": round(alpha_mean, 5),
        "alpha_annual": round(alpha_mean * 12, 4),
        "sharpe": round(sharpe, 3),
        "win_rate": round(float(np.mean(alpha > 0)), 3),
        "n_months": len(port),
        "n_avg_stocks": round(float(np.mean(n_stocks_list)), 1),
        "port_total_return": round(float(np.prod(1 + port) - 1), 4),
        "spy_total_return": round(float(np.prod(1 + spy_r) - 1), 4),
        "verdict": "KEEP" if alpha_mean > 0.002 else "DISCARD",
    }
