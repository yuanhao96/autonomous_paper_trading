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


def _rank_and_select(passing: list[str], features: pd.DataFrame,
                     date: pd.Timestamp, screen_def: dict) -> list[str]:
    """Rank passing tickers by rank_by feature, return top_n."""
    top_n = screen_def.get("top_n", 20)
    rank_by = screen_def.get("rank_by")

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


def apply_screen(screen_def: dict, features: pd.DataFrame,
                 start: str = "2020-01-01", end: str = "2025-12-31") -> dict:
    """Backtest a screen: rebalance every holding_days, equal-weight top_n, measure vs SPY.

    Returns dict with backtest results.
    """
    prices = pd.read_parquet(DATA_DIR / "prices.parquet")
    close = prices["Close"]
    spy = close["SPY"] if "SPY" in close.columns else None

    filters = screen_def["filters"]
    holding_days = screen_def.get("holding_days", 21)

    # Rebalance dates: every holding_days trading days
    date_range = close.loc[start:end].index
    rebal_indices = list(range(0, len(date_range), holding_days))

    portfolio_returns = []
    spy_returns = []
    n_stocks_list = []
    monthly_details = []  # Per-period granular data

    for i in range(len(rebal_indices) - 1):
        rebal_date = date_range[rebal_indices[i]]
        next_date = date_range[rebal_indices[i + 1]]

        # Get tickers passing screen
        passing = _apply_filters(features, filters, rebal_date)
        if len(passing) == 0:
            continue

        # Rank and select top_n
        tickers = _rank_and_select(passing, features, rebal_date, screen_def)

        # Per-stock 1-month returns
        stock_rets = {}
        for t in tickers:
            if t in close.columns:
                p0 = close.loc[rebal_date, t] if rebal_date in close.index else np.nan
                p1 = close.loc[next_date, t] if next_date in close.index else np.nan
                if pd.notna(p0) and pd.notna(p1) and p0 > 0:
                    stock_rets[t] = round(p1 / p0 - 1, 5)

        if len(stock_rets) == 0:
            continue

        port_ret = np.mean(list(stock_rets.values()))
        portfolio_returns.append(port_ret)
        n_stocks_list.append(len(stock_rets))

        # SPY return for same period
        spy_ret = 0.0
        if spy is not None:
            s0 = spy.loc[rebal_date] if rebal_date in spy.index else np.nan
            s1 = spy.loc[next_date] if next_date in spy.index else np.nan
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
            "monthly_details": [],
            "verdict": "NO DATA",
        }

    port = np.array(portfolio_returns)
    spy_r = np.array(spy_returns[:len(port)])
    alpha = port - spy_r

    alpha_mean = float(np.mean(alpha))
    alpha_std = float(np.std(alpha)) if len(alpha) > 1 else 1.0
    periods_per_year = 252 / holding_days
    sharpe = alpha_mean / alpha_std * np.sqrt(periods_per_year) if alpha_std > 0 else 0.0

    return {
        "name": screen_def.get("name", ""),
        "hypothesis": screen_def.get("hypothesis", ""),
        "filters": filters,
        "holding_days": holding_days,
        "rank_by": screen_def.get("rank_by"),
        "rank_order": screen_def.get("rank_order", "desc") if screen_def.get("rank_by") else None,
        "alpha_monthly_mean": round(alpha_mean, 5),
        "alpha_annual": round(alpha_mean * periods_per_year, 4),
        "sharpe": round(sharpe, 3),
        "win_rate": round(float(np.mean(alpha > 0)), 3),
        "n_months": len(port),
        "n_avg_stocks": round(float(np.mean(n_stocks_list)), 1),
        "port_total_return": round(float(np.prod(1 + port) - 1), 4),
        "spy_total_return": round(float(np.prod(1 + spy_r) - 1), 4),
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
        "verdict": "KEEP" if sharpe >= 0.3 else "DISCARD",
    }
