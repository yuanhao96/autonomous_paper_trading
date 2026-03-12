# AutoScreen Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An autoresearch-style loop that autonomously discovers stock screens predicting 1-month forward returns on S&P 500.

**Architecture:** Three files + one config. `data.py` caches S&P 500 price + fundamental data as parquet. `screen.py` evaluates a structured JSON screen definition against cached data via monthly rebalancing and measures alpha vs SPY. `run.py` orchestrates the loop: LLM reads `program.md`, proposes a screen, `screen.py` evaluates it, results get appended. No classes, no abstractions — just functions.

**Tech Stack:** Python 3.10+, yfinance, pandas, Claude Code CLI (`claude -p`), conda env `data_science`

**Conda env:** `data_science` (has yfinance 1.2.0, pandas 2.3.1)

**LLM:** Claude Code CLI in non-interactive mode — no API keys needed in script

---

## File Structure

```
data.py          # Download & cache S&P 500 data to parquet
screen.py        # Evaluate a screen definition, measure alpha vs SPY
run.py           # Orchestration loop: LLM → screen → evaluate → log
program.md       # LLM instructions + available features + results log
results.jsonl    # Append-only log of all screen evaluations (machine-readable)
knowledge/       # Existing — READ-ONLY reference material
factors/         # Existing — READ-ONLY factor docs
CLAUDE.md        # Existing — project instructions (update after build)
```

## Screen DSL

The LLM proposes screens as JSON:

```json
{
  "name": "Revenue acceleration + uptrend",
  "hypothesis": "Stocks with accelerating revenue in an uptrend outperform",
  "filters": [
    {"feature": "revenue_growth_yoy", "op": ">", "value": 0.10},
    {"feature": "close_vs_sma200", "op": ">", "value": 1.0},
    {"feature": "volatility_60d", "op": "<", "value": 0.40}
  ],
  "top_n": 20
}
```

Operators: `>`, `<`, `>=`, `<=`, `==`, `!=`, `between` (value = [lo, hi])

## Available Features

Two categories — all derivable from cached time-series data (backtestable):

### Price-derived (from daily OHLCV)
| Feature | Description |
|---------|-------------|
| `return_1m` | 1-month (21 trading day) return |
| `return_3m` | 3-month return |
| `return_6m` | 6-month return |
| `return_12m` | 12-month return |
| `close_vs_sma50` | Close / SMA(50) ratio |
| `close_vs_sma200` | Close / SMA(200) ratio |
| `sma50_vs_sma200` | SMA(50) / SMA(200) — golden/death cross |
| `high_52w_pct` | Close / 52-week high |
| `low_52w_pct` | Close / 52-week low |
| `volatility_20d` | 20-day annualized volatility |
| `volatility_60d` | 60-day annualized volatility |
| `avg_volume_20d` | 20-day average dollar volume |
| `volume_ratio` | Recent 5d avg volume / 20d avg volume |
| `drawdown` | Current drawdown from rolling 52w high |

### Fundamental (from quarterly financials, forward-filled daily)
| Feature | Description |
|---------|-------------|
| `revenue_growth_yoy` | YoY quarterly revenue growth |
| `revenue_growth_qoq` | QoQ quarterly revenue growth |
| `earnings_growth_yoy` | YoY quarterly net income growth |
| `gross_margin` | Gross profit / revenue |
| `operating_margin` | Operating income / revenue |
| `net_margin` | Net income / revenue |
| `gross_margin_change` | QoQ change in gross margin |
| `operating_margin_change` | QoQ change in operating margin |
| `roa` | Net income / total assets (annualized) |
| `roe` | Net income / stockholders equity (annualized) |
| `debt_to_equity` | Total debt / stockholders equity |
| `current_ratio` | Current assets / current liabilities |
| `revenue_acceleration` | Revenue growth YoY minus prior quarter's YoY growth |

---

## Chunk 1: Data Layer

### Task 1: Project setup

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Create minimal pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "autoscreen"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "pandas",
    "pyarrow",
    "yfinance",
]

[project.optional-dependencies]
dev = ["pytest", "ruff"]

[tool.ruff]
line-length = 100
```

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "feat: init autoscreen project"
```

### Task 2: Data download and caching

**Files:**
- Create: `data.py`
- Test: `tests/test_data.py`

- [ ] **Step 3: Write test for S&P 500 ticker list**

```python
# tests/test_data.py
from data import get_sp500_tickers

def test_sp500_tickers():
    tickers = get_sp500_tickers()
    assert isinstance(tickers, list)
    assert len(tickers) > 400
    assert "AAPL" in tickers
    assert "MSFT" in tickers
```

- [ ] **Step 4: Run test to verify it fails**

Run: `conda run -n data_science pytest tests/test_data.py::test_sp500_tickers -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'data'`

- [ ] **Step 5: Implement get_sp500_tickers**

```python
# data.py
"""Download & cache S&P 500 price + fundamental data."""
from pathlib import Path

import pandas as pd
import yfinance as yf

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def get_sp500_tickers() -> list[str]:
    """Scrape current S&P 500 constituents from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    table = pd.read_html(url)[0]
    tickers = table["Symbol"].str.replace(".", "-", regex=False).tolist()
    return sorted(tickers)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `conda run -n data_science pytest tests/test_data.py::test_sp500_tickers -v`
Expected: PASS

- [ ] **Step 7: Write test for price data download**

```python
# tests/test_data.py  (append)
from data import download_prices

def test_download_prices_small():
    """Test with 3 tickers to keep it fast."""
    df = download_prices(["AAPL", "MSFT", "GOOGL"], start="2024-01-01", end="2024-03-01")
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 30  # ~2 months of trading days
    # MultiIndex columns: (field, ticker)
    assert "AAPL" in df.columns.get_level_values(1)
    assert "Close" in df.columns.get_level_values(0)
```

- [ ] **Step 8: Implement download_prices**

```python
# data.py (append)

def download_prices(tickers: list[str], start: str = "2019-01-01",
                    end: str = "2025-12-31") -> pd.DataFrame:
    """Download daily OHLCV for given tickers. Returns MultiIndex columns (field, ticker)."""
    df = yf.download(tickers, start=start, end=end, group_by="column", threads=True)
    return df
```

- [ ] **Step 9: Run test**

Run: `conda run -n data_science pytest tests/test_data.py::test_download_prices_small -v`
Expected: PASS

- [ ] **Step 10: Write test for quarterly financials**

```python
# tests/test_data.py (append)
from data import download_financials

def test_download_financials_small():
    """Test with 2 tickers."""
    df = download_financials(["AAPL", "MSFT"])
    assert isinstance(df, pd.DataFrame)
    assert "ticker" in df.columns
    assert "Total Revenue" in df.columns or "TotalRevenue" in df.columns
    assert len(df) > 0
```

- [ ] **Step 11: Implement download_financials**

```python
# data.py (append)

def download_financials(tickers: list[str]) -> pd.DataFrame:
    """Download quarterly financials for given tickers.

    Returns a DataFrame with columns: ticker, date, and financial fields.
    Each row = one quarter for one ticker.
    """
    rows = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            # quarterly_income_stmt has columns = dates, rows = line items
            inc = t.quarterly_income_stmt
            bs = t.quarterly_balance_sheet
            cf = t.quarterly_cashflow
            if inc is None or inc.empty:
                continue
            for date in inc.columns:
                row = {"ticker": ticker, "date": date}
                for stmt in [inc, bs, cf]:
                    if stmt is not None and date in stmt.columns:
                        for item in stmt.index:
                            row[item] = stmt.loc[item, date]
                rows.append(row)
        except Exception:
            continue
    return pd.DataFrame(rows)
```

- [ ] **Step 12: Run test**

Run: `conda run -n data_science pytest tests/test_data.py::test_download_financials_small -v`
Expected: PASS

- [ ] **Step 13: Implement cache_all — the main entry point**

```python
# data.py (append)

def cache_all(force: bool = False):
    """Download everything and save to parquet. Skip if cache exists unless force=True."""
    prices_path = DATA_DIR / "prices.parquet"
    financials_path = DATA_DIR / "financials.parquet"

    tickers = get_sp500_tickers()
    # SPY is an ETF, not a constituent — add explicitly for benchmark
    if "SPY" not in tickers:
        tickers.append("SPY")
    print(f"S&P 500 + SPY: {len(tickers)} tickers")

    if force or not prices_path.exists():
        print("Downloading prices...")
        prices = download_prices(tickers)
        prices.to_parquet(prices_path)
        print(f"Saved {prices_path} ({len(prices)} rows)")
    else:
        print(f"Prices cached at {prices_path}")

    if force or not financials_path.exists():
        print("Downloading financials...")
        financials = download_financials(tickers)
        financials.to_parquet(financials_path)
        print(f"Saved {financials_path} ({len(financials)} rows)")
    else:
        print(f"Financials cached at {financials_path}")


if __name__ == "__main__":
    import sys
    cache_all(force="--force" in sys.argv)
```

- [ ] **Step 14: Commit**

```bash
git add data.py tests/test_data.py
git commit -m "feat: data layer — download & cache S&P 500 prices + financials"
```

---

## Chunk 2: Feature Computation + Screen Evaluation

### Task 3: Feature computation

**Files:**
- Create: `screen.py`
- Test: `tests/test_screen.py`

- [ ] **Step 15: Write test for price features**

```python
# tests/test_screen.py
import pandas as pd
from screen import compute_price_features

def test_price_features_shape():
    """Use cached data if available, otherwise skip."""
    from pathlib import Path
    prices_path = Path("data/prices.parquet")
    if not prices_path.exists():
        import pytest
        pytest.skip("No cached price data")
    prices = pd.read_parquet(prices_path)
    features = compute_price_features(prices)
    assert isinstance(features, pd.DataFrame)
    # Should have MultiIndex columns: (feature_name, ticker)
    assert "return_1m" in features.columns.get_level_values(0)
    assert "close_vs_sma200" in features.columns.get_level_values(0)
    assert len(features) > 100
```

- [ ] **Step 16: Run test to verify it fails**

Run: `conda run -n data_science pytest tests/test_screen.py::test_price_features_shape -v`
Expected: FAIL

- [ ] **Step 17: Implement compute_price_features**

```python
# screen.py
"""Evaluate stock screens against cached S&P 500 data."""
import json
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
    low = prices["Low"]
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
    low_52w = low.rolling(252).min()
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
```

- [ ] **Step 18: Run test**

Run: `conda run -n data_science pytest tests/test_screen.py::test_price_features_shape -v`
Expected: PASS (if data cached) or SKIP

- [ ] **Step 19: Write test for fundamental features**

```python
# tests/test_screen.py (append)
from screen import compute_fundamental_features

def test_fundamental_features_shape():
    from pathlib import Path
    prices_path = Path("data/prices.parquet")
    fin_path = Path("data/financials.parquet")
    if not prices_path.exists() or not fin_path.exists():
        import pytest
        pytest.skip("No cached data")
    prices = pd.read_parquet(prices_path)
    financials = pd.read_parquet(fin_path)
    features = compute_fundamental_features(financials, prices)
    assert isinstance(features, pd.DataFrame)
    assert "revenue_growth_yoy" in features.columns.get_level_values(0)
    assert "gross_margin" in features.columns.get_level_values(0)
```

- [ ] **Step 20: Implement compute_fundamental_features**

This is the trickiest part. Quarterly financials arrive at specific dates and must be forward-filled to daily frequency, then aligned with the price index.

```python
# screen.py (append)

def compute_fundamental_features(financials: pd.DataFrame,
                                  prices: pd.DataFrame) -> pd.DataFrame:
    """Compute fundamental features from quarterly financials.

    Quarterly values are forward-filled to daily frequency and aligned
    to the price DataFrame's date index.
    """
    close = prices["Close"]
    tickers = close.columns.tolist()
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
        ni_yoy_q = (net_income_q - net_income_q.shift(4)) / net_income_q.shift(4).abs().clip(lower=1)
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
        features["roa"] = ffill_to_daily((net_income_q * 4) / total_assets_q.abs().clip(lower=1))

    if net_income_q is not None and equity_q is not None:
        features["roe"] = ffill_to_daily((net_income_q * 4) / equity_q.abs().clip(lower=1))

    # Balance sheet ratios
    if total_debt_q is not None and equity_q is not None:
        features["debt_to_equity"] = ffill_to_daily(total_debt_q / equity_q.abs().clip(lower=1))

    if current_assets_q is not None and current_liab_q is not None:
        features["current_ratio"] = ffill_to_daily(current_assets_q / current_liab_q.abs().clip(lower=1))

    if not features:
        return pd.DataFrame(index=date_index)

    return pd.concat(features, axis=1)
```

- [ ] **Step 21: Run test**

Run: `conda run -n data_science pytest tests/test_screen.py::test_fundamental_features_shape -v`
Expected: PASS (if data cached) or SKIP

- [ ] **Step 22: Commit**

```bash
git add screen.py tests/test_screen.py
git commit -m "feat: feature computation — price + fundamental features from cached data"
```

### Task 4: Screen evaluation (the core)

**Files:**
- Modify: `screen.py`
- Test: `tests/test_screen.py` (append)

- [ ] **Step 23: Write test for apply_screen**

```python
# tests/test_screen.py (append)
from screen import apply_screen, compute_all_features

def test_apply_screen():
    from pathlib import Path
    if not Path("data/prices.parquet").exists():
        import pytest
        pytest.skip("No cached data")
    features = compute_all_features()
    screen_def = {
        "name": "test momentum",
        "hypothesis": "testing",
        "filters": [
            {"feature": "return_3m", "op": ">", "value": 0.05},
            {"feature": "close_vs_sma200", "op": ">", "value": 1.0},
        ],
        "top_n": 20,
    }
    result = apply_screen(screen_def, features)
    assert "alpha_monthly_mean" in result
    assert "sharpe" in result
    assert "n_avg_stocks" in result
    assert isinstance(result["alpha_monthly_mean"], float)
```

- [ ] **Step 24: Run test to verify it fails**

Run: `conda run -n data_science pytest tests/test_screen.py::test_apply_screen -v`
Expected: FAIL

- [ ] **Step 25: Implement compute_all_features and apply_screen**

```python
# screen.py (append)

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
    """Apply filter list at a single date. Returns list of tickers passing all filters."""
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
        # All passing stocks meet the criteria, so selection within is equal.
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
```

- [ ] **Step 26: Run test**

Run: `conda run -n data_science pytest tests/test_screen.py::test_apply_screen -v`
Expected: PASS (if data cached) or SKIP

- [ ] **Step 27: Commit**

```bash
git add screen.py tests/test_screen.py
git commit -m "feat: screen evaluation — apply filters, monthly rebalance, measure alpha vs SPY"
```

---

## Chunk 3: LLM Loop + Program

### Task 5: program.md — LLM instructions

**Files:**
- Create: `program.md`

- [ ] **Step 28: Write program.md**

```markdown
# AutoScreen

You are an autonomous stock screening researcher. Your job is to propose
screens that identify S&P 500 stocks likely to outperform SPY over the
next month.

## How it works

1. You read this file (past results + available features)
2. You propose ONE new screen as a JSON object
3. The system backtests it (monthly rebalance, 2020-2025, equal-weight)
4. Results get appended below
5. Repeat

## Rules

- Each screen is a set of filters on the features listed below
- A screen PASSES a stock if ALL filters are satisfied (AND logic)
- The system buys equal-weight top_n stocks passing the screen, holds 1 month
- Your goal: find screens with positive alpha (excess return vs SPY)
- Learn from past results — don't repeat screens that failed
- Try variations on screens that worked
- Think about WHY a screen might predict returns, not just what looks good in-sample

## Available features

### Price-derived
- return_1m: 1-month return
- return_3m: 3-month return
- return_6m: 6-month return
- return_12m: 12-month return
- close_vs_sma50: close / 50-day SMA
- close_vs_sma200: close / 200-day SMA
- sma50_vs_sma200: 50-day SMA / 200-day SMA (golden/death cross)
- high_52w_pct: close / 52-week high (1.0 = at high)
- low_52w_pct: close / 52-week low
- volatility_20d: 20-day annualized volatility
- volatility_60d: 60-day annualized volatility
- avg_volume_20d: 20-day avg dollar volume
- volume_ratio: 5d avg volume / 20d avg volume
- drawdown: current drawdown from 52-week high (0 = at high, -0.2 = 20% down)

### Fundamental (quarterly, forward-filled)
- revenue_growth_yoy: year-over-year quarterly revenue growth
- revenue_growth_qoq: quarter-over-quarter revenue growth
- earnings_growth_yoy: YoY net income growth
- gross_margin: gross profit / revenue
- operating_margin: operating income / revenue
- net_margin: net income / revenue
- gross_margin_change: QoQ change in gross margin
- operating_margin_change: QoQ change in operating margin
- roa: return on assets (annualized)
- roe: return on equity (annualized)
- debt_to_equity: total debt / equity
- current_ratio: current assets / current liabilities
- revenue_acceleration: revenue growth YoY minus prior quarter's YoY growth

## Filter operators
- `>`, `<`, `>=`, `<=`, `==`, `!=`
- `between` — value is [lo, hi]

## JSON format

```json
{
  "name": "descriptive short name",
  "hypothesis": "why this should predict returns (1-2 sentences)",
  "filters": [
    {"feature": "feature_name", "op": ">", "value": 0.1}
  ],
  "top_n": 20
}
```

## Past results

(Results will be appended here by the system)
```

- [ ] **Step 29: Commit**

```bash
git add program.md
git commit -m "feat: program.md — LLM instructions and feature reference"
```

### Task 6: run.py — the orchestration loop

**Files:**
- Create: `run.py`
- Test: `tests/test_run.py`

- [ ] **Step 30: Write test for LLM screen proposal parsing**

```python
# tests/test_run.py
from run import parse_screen_json

def test_parse_screen_json():
    raw = '''Here's my proposal:
```json
{
  "name": "test",
  "hypothesis": "testing",
  "filters": [{"feature": "return_3m", "op": ">", "value": 0.05}],
  "top_n": 20
}
```
'''
    screen = parse_screen_json(raw)
    assert screen["name"] == "test"
    assert len(screen["filters"]) == 1
    assert screen["top_n"] == 20


def test_parse_screen_json_no_codeblock():
    raw = '{"name": "test", "hypothesis": "x", "filters": [], "top_n": 10}'
    screen = parse_screen_json(raw)
    assert screen["name"] == "test"
```

- [ ] **Step 31: Run test to verify it fails**

Run: `conda run -n data_science pytest tests/test_run.py -v`
Expected: FAIL

- [ ] **Step 32: Implement run.py**

```python
# run.py
"""AutoScreen: autonomous stock screening research loop.

Uses Claude Code CLI (`claude -p`) to propose screens. Claude Code has full
access to project files (CLAUDE.md, program.md, knowledge/, factors/) and
can reason about what screens to try based on the full project context.
"""
import json
import re
import subprocess
from pathlib import Path

PROGRAM_PATH = Path("program.md")
RESULTS_PATH = Path("results.jsonl")


def parse_screen_json(text: str) -> dict:
    """Extract screen JSON from LLM response. Handles markdown code blocks."""
    # Try to find JSON in code block first
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # Fallback: try to parse the entire text as JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    raise ValueError(f"Could not parse screen JSON from LLM response:\n{text[:500]}")


def propose_screen() -> dict:
    """Use Claude Code CLI to propose a new screen.

    Claude Code automatically sees CLAUDE.md, can read program.md and
    results.jsonl, and has access to the knowledge base and factor docs.
    """
    prompt = (
        "Read program.md to understand the AutoScreen system. "
        "Read results.jsonl if it exists to see past screen results. "
        "Based on the available features, past results (learn from what worked/failed), "
        "and your knowledge of what predicts stock returns, propose ONE new stock screen. "
        "Output ONLY the JSON object in a ```json code block. No other text."
    )

    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude Code failed: {result.stderr[:500]}")

    return parse_screen_json(result.stdout)


def append_result(result: dict):
    """Append result to results.jsonl and to program.md."""
    # Append to JSONL
    with open(RESULTS_PATH, "a") as f:
        f.write(json.dumps(result) + "\n")

    # Append human-readable summary to program.md
    summary = (
        f"\n### Screen #{count_results()}: {result['name']}\n"
        f"- **Hypothesis**: {result['hypothesis']}\n"
        f"- **Filters**: {json.dumps(result['filters'])}\n"
        f"- **Alpha (monthly)**: {result['alpha_monthly_mean']:.4f} "
        f"({result.get('alpha_annual', 0):.2%} annualized)\n"
        f"- **Sharpe**: {result['sharpe']:.2f}\n"
        f"- **Win rate**: {result['win_rate']:.1%}\n"
        f"- **Avg stocks**: {result['n_avg_stocks']}\n"
        f"- **Months**: {result['n_months']}\n"
        f"- **Verdict**: {result['verdict']}\n"
    )
    with open(PROGRAM_PATH, "a") as f:
        f.write(summary)


def count_results() -> int:
    """Count existing results."""
    if not RESULTS_PATH.exists():
        return 0
    with open(RESULTS_PATH) as f:
        return sum(1 for _ in f)


def run_loop(n_iterations: int = 10):
    """Main loop: propose → evaluate → log, repeated n times."""
    from screen import apply_screen, compute_all_features

    print("Computing features from cached data...")
    features = compute_all_features()
    print(f"Features ready: {features.shape}")

    for i in range(n_iterations):
        iteration = count_results() + 1
        print(f"\n{'='*60}")
        print(f"Iteration {iteration}")
        print(f"{'='*60}")

        # Claude Code proposes screen
        print("Asking Claude Code for screen proposal...")
        try:
            screen_def = propose_screen()
        except Exception as e:
            print(f"Error: {e}")
            continue

        print(f"Screen: {screen_def.get('name', '?')}")
        print(f"Hypothesis: {screen_def.get('hypothesis', '?')}")
        print(f"Filters: {json.dumps(screen_def.get('filters', []), indent=2)}")

        # Evaluate
        print("Backtesting...")
        result = apply_screen(screen_def, features)

        # Log
        print(f"Alpha (monthly): {result['alpha_monthly_mean']:.4f}")
        print(f"Alpha (annual):  {result.get('alpha_annual', 0):.2%}")
        print(f"Sharpe:          {result['sharpe']:.2f}")
        print(f"Win rate:        {result['win_rate']:.1%}")
        print(f"Avg stocks:      {result['n_avg_stocks']}")
        print(f"Verdict:         {result['verdict']}")

        append_result(result)

    # Summary
    print(f"\n{'='*60}")
    print(f"Done. {count_results()} total screens evaluated.")
    if RESULTS_PATH.exists():
        import pandas as pd
        df = pd.read_json(RESULTS_PATH, lines=True)
        kept = df[df["verdict"] == "KEEP"]
        print(f"Keepers: {len(kept)} / {len(df)}")
        if len(kept) > 0:
            print("\nBest screens:")
            print(kept.sort_values("alpha_annual", ascending=False)[
                ["name", "alpha_annual", "sharpe", "win_rate"]
            ].head(5).to_string(index=False))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AutoScreen research loop")
    parser.add_argument("-n", type=int, default=10, help="Number of iterations")
    args = parser.parse_args()
    run_loop(n_iterations=args.n)
```

- [ ] **Step 33: Run test**

Run: `conda run -n data_science pytest tests/test_run.py -v`
Expected: PASS

- [ ] **Step 34: Commit**

```bash
git add run.py tests/test_run.py
git commit -m "feat: run.py — LLM-driven screen research loop"
```

---

## Chunk 4: Integration + CLAUDE.md update

### Task 7: End-to-end smoke test

- [ ] **Step 35: Cache data (run once, ~15-20 min)**

```bash
conda run -n data_science python data.py
```

Expected: Downloads ~500 tickers of price data + quarterly financials, saves to `data/`

- [ ] **Step 36: Run one iteration to verify loop works**

```bash
conda run -n data_science python run.py -n 1
```

Expected: Claude Code proposes a screen, system evaluates it, result appended to program.md and results.jsonl

- [ ] **Step 37: Run lint**

```bash
conda run -n data_science ruff check data.py screen.py run.py
```

Fix any issues found.

### Task 8: Update CLAUDE.md

- [ ] **Step 38: Replace CLAUDE.md to reflect new project**

Update CLAUDE.md to document the new autoscreen system: 3 files, how to run, the loop, available features, DSL format. Remove all references to the old stratgen pipeline.

- [ ] **Step 39: Final commit**

```bash
git add CLAUDE.md data.py screen.py run.py program.md tests/
git commit -m "feat: autoscreen v0.1 — autonomous stock screening research loop"
```

---

## Usage

```bash
# One-time: download & cache S&P 500 data
conda run -n data_science python data.py

# Run 10 iterations of autonomous screen research (uses Claude Code CLI)
conda run -n data_science python run.py -n 10

# Run 1 iteration (good for testing)
conda run -n data_science python run.py -n 1

# Re-download data (quarterly refresh)
conda run -n data_science python data.py --force
```

**Prerequisite:** Claude Code CLI must be installed and authenticated (`claude` available on PATH).
