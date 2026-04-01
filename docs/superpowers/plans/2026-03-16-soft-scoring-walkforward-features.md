# Soft Scoring + Walk-Forward + Feature Enrichment Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the AutoScreen system from rigid AND-filter screens to soft composite scoring as the primary strategy, replace single-date IS/OOS split with rolling walk-forward evaluation, and add new predictive features.

**Architecture:** Three sequential changes: (B) Update program.md + run.py to make score-only screens the default LLM strategy — no code changes to screen.py since empty `filters: []` already works. (A) Replace `--split-date` with `--walk-forward` in screen.py and run.py — rolling train/test windows produce averaged OOS Sharpe across multiple windows. (C) Add 4 new price-derived features to screen.py and extend data.py start date from 2019 to 2014 for 10+ years of backtest history.

**Tech Stack:** Python 3.10+, pandas, numpy, scipy, yfinance. Conda env: `data_science`.

---

## Chunk 1: Soft Scoring as Default (Direction B)

The existing DSL already supports composite scoring via `rank_by: "_score"` and `score: [...]`, and `_apply_filters` with empty `filters: []` passes all tickers through. The only changes needed are:

1. **program.md** — Rewrite LLM instructions to make score-only screens the default (list only EXISTING features; new features added in Chunk 3 will update this file)
2. **run.py** — Update `propose_screen()` prompt to emphasize scoring over filtering
3. **feature_stats.py** — Update `CORE_FILTERS` to reflect the new score-based approach
4. **results.jsonl** — Delete old results (don't archive to git — it's gitignored)
5. **goal.md** — Update to reflect new milestones

### Task 1: Update program.md for score-first strategy

**Files:**
- Modify: `program.md`

- [ ] **Step 1: Rewrite program.md**

Replace the current program.md with score-first instructions. Key changes:
- Default screen template uses `score` + `rank_by: "_score"` with empty or minimal `filters`
- Reference feature_stats.md for which features to weight (volatility_20d, low_52w_pct, return_1m_vs_sector have the best quintile L/S Sharpe)
- Explain that hard filters are optional guardrails, not the primary mechanism
- Keep holding_days flexibility (10, 21, 42)

```markdown
# AutoScreen

You are an autonomous stock screening researcher. Your job is to propose
screens that identify S&P 500 stocks likely to outperform SPY.

## How it works

1. An analysis agent reads results.jsonl, computes stats with pandas, writes analysis.md
2. You read this file (available features) and analysis.md (research insights)
3. You propose ONE new screen as a JSON object
4. The system backtests it (equal-weight top_n, 2015-2025)
5. Result appended to results.jsonl
6. Repeat

## Rules

- **Score-first design**: Use weighted composite scoring (`rank_by: "_score"`) as the
  primary selection mechanism. Hard filters are optional guardrails (e.g., exclude
  illiquid stocks), NOT the main strategy.
- A screen ranks ALL stocks (or those passing optional guard filters) by composite score,
  then picks the top_n.
- Your goal: find screens with Sharpe >= 0.3 on walk-forward OOS alpha vs SPY (annualized)
- Learn from past results -- don't repeat screens that failed
- Try variations on screens that worked (different weights, holding periods)
- Think about WHY a feature might predict returns, not just what looks good in-sample
- Read analysis.md for research insights from past screen results
- Read feature_stats.md for per-feature predictive power (rank IC, quintile Sharpe)
- IMPORTANT: fundamental features only cover the most recent ~1.5 years (yfinance
  limitation). Prefer price-derived features for full backtest coverage.

### Score-based screen template (PREFERRED)

```json
{
  "name": "Descriptive name",
  "hypothesis": "Why this combination should predict returns",
  "filters": [],
  "score": [
    {"feature": "volatility_20d_pctrank", "weight": 1.0},
    {"feature": "low_52w_pct_pctrank", "weight": 0.5},
    {"feature": "return_1m_vs_sector_pctrank", "weight": 0.3}
  ],
  "top_n": 30,
  "rank_by": "_score",
  "rank_order": "desc",
  "holding_days": 21
}
```

Use `_pctrank` features in scores -- they're all on 0-1 scale, making weights comparable.
Negative weights invert (lower = better, e.g. `volatility_20d_pctrank` with weight -1.0
selects low-vol stocks).

### Features with proven quintile spread (from feature_stats.md)

These features show the strongest long-short quintile spread. Use them as primary
score components:

| Feature | LS Sharpe | Monotonic | Direction |
|---------|-----------|-----------|-----------|
| `volatility_20d_pctrank` | +0.90 | 1.00 | Higher vol = higher return |
| `volatility_60d_pctrank` | +0.84 | 1.00 | Higher vol = higher return |
| `low_52w_pct_pctrank` | +0.66 | 0.75 | Further from 52w low = better |
| `volume_ratio_pctrank` | +0.55 | 0.50 | Higher recent volume = better |
| `return_1m_vs_sector_pctrank` | +0.47 | 0.50 | Sector outperformer |

Features with NEGATIVE quintile spread (avoid or use negative weight):
| `high_52w_pct_pctrank` | -0.72 | Near 52w high = worse |
| `close_vs_sma50_pctrank` | -0.49 | Overbought = worse |
| `return_3m_pctrank` | -0.30 | 3m momentum reverses |

### Filter-based screen (SECONDARY)

Still supported but use sparingly. Hard filters create cliff effects where a stock
just below a threshold is excluded entirely. Prefer scoring.

```json
{
  "name": "Filtered screen",
  "hypothesis": "...",
  "filters": [
    {"feature": "avg_volume_20d_pctrank", "op": ">", "value": 0.2}
  ],
  "score": [...],
  "top_n": 20,
  "rank_by": "_score",
  "rank_order": "desc",
  "holding_days": 21
}
```

### Holding periods

The LLM should experiment with different holding periods:
- 10 trading days (~biweekly): faster signals, more turnover
- 21 trading days (~monthly): standard
- 42 trading days (~bimonthly): slower signals, less turnover noise

### Verdicts

- **KEEP**: Mean OOS Sharpe >= 0.3 across walk-forward windows
- **DISCARD**: Mean OOS Sharpe < 0.3

### Walk-forward evaluation

The system evaluates screens using rolling walk-forward windows:
- Train on trailing N months, test on next M months, roll forward
- Multiple OOS windows produce a more robust Sharpe estimate
- The LLM sees aggregate stats; the verdict uses mean OOS Sharpe

### Market regimes

Each backtest period is tagged with one of 4 market regimes:
- **quiet_bull**: SPY above SMA(200), low volatility
- **volatile_bull**: SPY above SMA(200), high volatility
- **quiet_bear**: SPY below SMA(200), low volatility
- **volatile_bear**: SPY below SMA(200), high volatility

**Prefer regime-robust screens.** A screen with Sharpe 0.4 across all regimes is more
valuable than one with Sharpe 0.8 in only one regime.

## Available features

### Price-derived (full backtest coverage)
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

### Sector-relative (adapts to sector rotation)
- sector_return_1m: median 1-month return of same sector
- sector_return_3m: median 3-month return of same sector
- return_1m_vs_sector: stock 1m return minus sector median
- return_6m_vs_sector: stock 6m return minus sector median
- gross_margin_vs_sector: stock gross margin / sector median
- roe_vs_sector: stock ROE / sector median
- volatility_20d_vs_sector: stock 20d vol / sector median
- sector_breadth: fraction of sector above SMA200

### Fundamental (recent ~1.5 years only)
- gross_margin, operating_margin, net_margin
- roa, roe
- debt_to_equity, current_ratio

### Stability (recent ~1.5 years)
- gross_margin_stability, operating_margin_stability, roe_stability

### Percentile ranks (0-1 scale)
Every feature above also has a `{feature}_pctrank` variant computed cross-sectionally.
```

- [ ] **Step 2: Verify program.md is well-formed**

Read the file back and confirm it renders correctly.

- [ ] **Step 3: Commit**

```bash
git add program.md
git commit -m "feat: rewrite program.md for score-first screen strategy"
```

### Task 2: Update propose_screen() prompt in run.py

**Files:**
- Modify: `run.py:139-170`

- [ ] **Step 1: Update the propose_screen prompt**

Replace the current prompt in `propose_screen()` to emphasize score-based screens:

```python
def propose_screen() -> dict:
    """Use Claude Code CLI to propose a new screen."""
    prompt = (
        "Read program.md to understand the AutoScreen system and available features. "
    )
    if ANALYSIS_PATH.exists():
        prompt += "Read analysis.md for research insights from past screen results. "
    if Path("feature_stats.md").exists():
        prompt += "Read feature_stats.md for per-feature predictive power stats. "
    prompt += (
        "Based on the available features, the analysis insights, "
        "and your knowledge of what predicts stock returns, propose ONE new stock screen.\n"
        "IMPORTANT: Use score-based screens (rank_by='_score' with score weights) as "
        "the default approach. Hard filters are optional guardrails only.\n"
        "Use _pctrank features in scores for comparable 0-1 scales.\n"
        "Experiment with holding_days: 10, 21, or 42 trading days.\n"
        "Focus on features with proven quintile spread from feature_stats.md.\n"
        "Output ONLY the JSON object in a ```json code block. No other text."
    )

    return parse_screen_json(_claude_call(prompt, allowed_tools=["Read", "Glob"]))
```

- [ ] **Step 2: Run lint check**

Run: `conda run -n data_science ruff check run.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add run.py
git commit -m "feat: update propose_screen prompt for score-first strategy"
```

### Task 3: Clear old results and update feature_stats core template

**Files:**
- Modify: `feature_stats.py:9-14`
- Archive: `results.jsonl` -> `results_v2_filters.jsonl`

- [ ] **Step 1: Delete old results**

```bash
rm -f results.jsonl data/details/*.json
```

The old filter-based results would pollute the LLM's learning for score-based screens.
results.jsonl is gitignored, so nothing to unstage.

- [ ] **Step 2: Update CORE_FILTERS in feature_stats.py**

The old core template used hard filters. Update to use the features that showed the
strongest quintile spread, in a score-compatible framing:

```python
# Core template for conditional marginal IC analysis.
# These are the features with strongest unconditional quintile spread,
# used as the "base model" to test what additional features help.
CORE_FILTERS = [
    ("volatility_20d_pctrank", ">", 0.5),
    ("low_52w_pct_pctrank", ">", 0.5),
]
```

- [ ] **Step 3: Run lint**

Run: `conda run -n data_science ruff check feature_stats.py`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add feature_stats.py
git commit -m "refactor: update core template for score-first approach"
```

### Task 4: Update goal.md for new milestones

**Files:**
- Modify: `goal.md`

- [ ] **Step 1: Rewrite goal.md**

Replace with the new milestone goals covering walk-forward and feature enrichment.
(Content: brief description of B done, A next, C after.)

- [ ] **Step 2: Commit**

```bash
git add goal.md
git commit -m "docs: update goal.md for score-first + walk-forward milestones"
```

---

## Chunk 2: Walk-Forward Evaluation (Direction A)

Replace the single-date IS/OOS split with rolling walk-forward windows. This produces
multiple OOS observations and a more robust Sharpe estimate.

**Design:**
- `--walk-forward` flag replaces `--split-date`
- Default: 18 months train, 6 months test, roll by 6 months
- Each window: backtest the screen, compute IS and OOS Sharpe
- Final metrics: mean OOS Sharpe across all windows, per-window breakdown
- Verdict: mean OOS Sharpe >= 0.3 -> KEEP

**Window math (with 2015-2025 = ~10 years):**
- 18-month train + 6-month test = 24 months per window
- Rolling by 6 months: ~15 windows (plenty of OOS observations)

### Task 5: Remove split_date and dead code, fix existing tests

**Files:**
- Modify: `screen.py` (remove `_compute_split_metrics`, `split_date` param from `apply_screen`)
- Modify: `tests/test_screen.py` (remove/rewrite split_date tests)

- [ ] **Step 1: Remove `_compute_split_metrics` from screen.py**

Delete the function at lines 500-543 entirely. It's superseded by walk-forward.

- [ ] **Step 2: Remove `split_date` parameter from `apply_screen`**

Remove `split_date` from the signature. Remove the split_date logic inside
(lines 673-677, 690-701, 745-750). Keep `start`, `end` params.
Also remove the import/usage of `_compute_split_metrics`.

- [ ] **Step 3: Update existing tests in test_screen.py**

Remove these tests that reference `split_date`:
- `test_split_metrics_basic` (lines 320-339)
- `test_split_metrics_all_is` (lines 342-352)
- `test_split_fallback_insufficient_months` (lines 354-379)
- `test_apply_screen_with_split_date` (lines 403-443)

Remove the import of `_compute_split_metrics` from the import block (line 7).

Update `test_apply_screen_backward_compatible` to just verify no walk-forward keys
are present (instead of no split keys):

```python
def test_apply_screen_backward_compatible():
    """apply_screen without walk_forward returns basic keys only."""
    if not Path("data/prices.parquet").exists():
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
    assert "sharpe" in result
    assert "wf_oos_sharpe_mean" not in result
    assert result["verdict"] in ("KEEP", "DISCARD")
```

- [ ] **Step 4: Run tests**

Run: `conda run -n data_science pytest tests/test_screen.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run lint**

Run: `conda run -n data_science ruff check screen.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add screen.py tests/test_screen.py
git commit -m "refactor: remove split_date, delete dead _compute_split_metrics code"
```

### Task 6: Write walk-forward test (TDD)

**Files:**
- Create: `tests/test_walk_forward.py`

- [ ] **Step 1: Write failing test for walk-forward window generation**

```python
"""Tests for walk-forward evaluation."""
import numpy as np
import pandas as pd
import pytest
from pathlib import Path


def test_generate_wf_windows_basic():
    """Walk-forward window generation with known date range."""
    from screen import generate_wf_windows

    dates = pd.date_range("2015-01-02", "2025-12-31", freq="B")
    windows = generate_wf_windows(
        dates, train_months=18, test_months=6,
    )
    # Each window is (train_start, train_end, test_start, test_end)
    assert len(windows) >= 10
    for train_start, train_end, test_start, test_end in windows:
        assert train_start < train_end
        assert train_end <= test_start
        assert test_start < test_end
        # Train period ~18 months
        train_days = (train_end - train_start).days
        assert 400 < train_days < 600  # ~18 months of trading days
        # Test period ~6 months
        test_days = (test_end - test_start).days
        assert 100 < test_days < 250  # ~6 months of trading days


def test_generate_wf_windows_no_overlap():
    """Test periods should not overlap."""
    from screen import generate_wf_windows

    dates = pd.date_range("2015-01-02", "2025-12-31", freq="B")
    windows = generate_wf_windows(dates, train_months=18, test_months=6)
    test_ranges = [(ts, te) for _, _, ts, te in windows]
    for i in range(len(test_ranges) - 1):
        assert test_ranges[i][1] <= test_ranges[i + 1][0]


def test_generate_wf_windows_short_data():
    """With very short data, should produce at least 1 window or empty."""
    from screen import generate_wf_windows

    dates = pd.date_range("2024-01-02", "2025-06-30", freq="B")
    windows = generate_wf_windows(dates, train_months=18, test_months=6)
    # 18 months of data is barely enough for 1 window
    assert len(windows) <= 1


def test_generate_wf_windows_too_short():
    """With data shorter than one train window, should produce 0 windows."""
    from screen import generate_wf_windows

    dates = pd.date_range("2024-06-01", "2025-06-30", freq="B")
    windows = generate_wf_windows(dates, train_months=18, test_months=6)
    assert len(windows) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n data_science pytest tests/test_walk_forward.py -v`
Expected: FAIL with ImportError (generate_wf_windows doesn't exist)

- [ ] **Step 3: Implement generate_wf_windows in screen.py**

Add to `screen.py` before `apply_screen`:

```python
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

    start = dates[0]
    end = dates[-1]
    windows = []

    train_start = start
    while True:
        train_end = train_start + relativedelta(months=train_months)
        test_start = train_end
        test_end = test_start + relativedelta(months=test_months)

        # Snap to nearest trading days in our date index
        train_start_idx = dates.searchsorted(train_start)
        train_end_idx = dates.searchsorted(train_end)
        test_start_idx = train_end_idx
        test_end_idx = dates.searchsorted(test_end)

        # Need at least some data in both periods
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

        # Roll forward by test_months
        train_start = train_start + relativedelta(months=test_months)

    return windows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n data_science pytest tests/test_walk_forward.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add screen.py tests/test_walk_forward.py
git commit -m "feat: add generate_wf_windows for rolling walk-forward evaluation"
```

### Task 7: Write walk-forward backtest function (TDD)

**Files:**
- Modify: `screen.py`
- Modify: `tests/test_walk_forward.py`

- [ ] **Step 1: Write failing test for walk-forward apply_screen**

Add to `tests/test_walk_forward.py`:

```python
def test_apply_screen_walk_forward():
    """Walk-forward backtest on real data."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    from screen import apply_screen, compute_all_features

    features = compute_all_features()
    screen_def = {
        "name": "test wf",
        "hypothesis": "testing walk-forward",
        "filters": [],
        "score": [
            {"feature": "volatility_20d_pctrank", "weight": 1.0},
        ],
        "top_n": 30,
        "rank_by": "_score",
        "rank_order": "desc",
        "holding_days": 21,
    }
    result = apply_screen(
        screen_def, features,
        walk_forward=True, train_months=18, test_months=6,
    )
    # Should have walk-forward metrics
    assert "wf_oos_sharpe_mean" in result
    assert "wf_oos_sharpe_std" in result
    assert "wf_n_windows" in result
    assert result["wf_n_windows"] >= 1
    assert isinstance(result["wf_oos_sharpe_mean"], float)
    # Should still have full-period metrics
    assert "sharpe" in result
    assert result["n_months"] > 0
    # Verdict uses mean OOS Sharpe
    if result["wf_oos_sharpe_mean"] >= 0.3:
        assert result["verdict"] == "KEEP"
    else:
        assert result["verdict"] == "DISCARD"


def test_apply_screen_walk_forward_per_window():
    """Walk-forward result includes per-window breakdown."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    from screen import apply_screen, compute_all_features

    features = compute_all_features()
    screen_def = {
        "name": "test wf detail",
        "hypothesis": "testing",
        "filters": [],
        "score": [
            {"feature": "volatility_20d_pctrank", "weight": 1.0},
        ],
        "top_n": 30,
        "rank_by": "_score",
        "rank_order": "desc",
    }
    result = apply_screen(
        screen_def, features,
        walk_forward=True, train_months=18, test_months=6,
    )
    assert "wf_windows" in result
    for w in result["wf_windows"]:
        assert "train_start" in w
        assert "test_start" in w
        assert "sharpe_is" in w
        assert "sharpe_oos" in w


def test_apply_screen_no_walk_forward_backward_compat():
    """Without walk_forward, behavior unchanged."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    from screen import apply_screen, compute_all_features

    features = compute_all_features()
    screen_def = {
        "name": "test compat",
        "hypothesis": "testing",
        "filters": [
            {"feature": "return_3m", "op": ">", "value": 0.05},
        ],
        "top_n": 20,
    }
    result = apply_screen(screen_def, features)
    assert "wf_oos_sharpe_mean" not in result
    assert "sharpe" in result


def test_apply_screen_walk_forward_zero_windows():
    """Walk-forward with insufficient data returns DISCARD gracefully."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    from screen import apply_screen, compute_all_features

    features = compute_all_features()
    screen_def = {
        "name": "test zero wf",
        "hypothesis": "testing",
        "filters": [],
        "score": [
            {"feature": "volatility_20d_pctrank", "weight": 1.0},
        ],
        "top_n": 30,
        "rank_by": "_score",
        "rank_order": "desc",
    }
    # Very short date range -> 0 walk-forward windows
    result = apply_screen(
        screen_def, features,
        start="2025-01-01", end="2025-06-30",
        walk_forward=True, train_months=18, test_months=6,
    )
    assert result["wf_n_windows"] == 0
    assert result["verdict"] == "DISCARD"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n data_science pytest tests/test_walk_forward.py::test_apply_screen_walk_forward -v`
Expected: FAIL (apply_screen doesn't accept walk_forward param)

- [ ] **Step 3: Implement walk-forward in apply_screen**

Modify `apply_screen()` in `screen.py`. Add walk_forward parameters and when enabled,
run the backtest on each window, collect per-window IS/OOS metrics, then aggregate.

The key change to `apply_screen`:
- Add params: `walk_forward: bool = False`, `train_months: int = 18`, `test_months: int = 6`
- When `walk_forward=True`:
  1. Generate windows with `generate_wf_windows`
  2. For each window, run the existing backtest logic (refactored into a helper) on the train and test periods
  3. Collect per-window IS/OOS Sharpe
  4. Return `wf_oos_sharpe_mean`, `wf_oos_sharpe_std`, `wf_n_windows`, `wf_windows` (per-window detail)
  5. Verdict uses `wf_oos_sharpe_mean >= 0.3`
- Also still run full-period backtest for `sharpe`, `monthly_details`, etc.
- Backward compatible: `walk_forward=False` (default) keeps old behavior
- Remove `split_date` parameter (superseded by walk-forward)

Implementation approach: extract the inner loop of `apply_screen` (the rebalance-by-rebalance logic at lines 600-658) into a helper function `_backtest_period(screen_def, features, prices, start, end)` that returns `(portfolio_returns, spy_returns, monthly_details, n_stocks_list)`. Then `apply_screen` calls this helper either once (full period) or per-window.

```python
def _backtest_period(
    screen_def: dict,
    features: pd.DataFrame,
    close: pd.DataFrame,
    spy: pd.Series | None,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
) -> tuple[list, list, list, list]:
    """Run backtest over a single period. Returns (port_rets, spy_rets, details, n_stocks)."""
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
```

Then modify `apply_screen` signature:

```python
def apply_screen(
    screen_def: dict,
    features: pd.DataFrame,
    start: str = "2015-01-01",
    end: str = "2025-12-31",
    walk_forward: bool = False,
    train_months: int = 18,
    test_months: int = 6,
) -> dict:
```

When `walk_forward=True`:

```python
    if walk_forward:
        date_range = close.loc[start:end].index
        windows = generate_wf_windows(
            date_range, train_months, test_months,
        )
        holding_days = screen_def.get("holding_days", 21)
        periods_per_year = 252 / holding_days

        wf_windows = []
        for train_start, train_end, test_start, test_end in windows:
            is_rets, is_spy, is_details, _ = _backtest_period(
                screen_def, features, close, spy,
                train_start, train_end,
            )
            oos_rets, oos_spy, oos_details, _ = _backtest_period(
                screen_def, features, close, spy,
                test_start, test_end,
            )
            is_alpha = np.array(is_rets) - np.array(is_spy[:len(is_rets)])
            oos_alpha = np.array(oos_rets) - np.array(oos_spy[:len(oos_rets)])

            wf_windows.append({
                "train_start": str(train_start.date()),
                "train_end": str(train_end.date()),
                "test_start": str(test_start.date()),
                "test_end": str(test_end.date()),
                "sharpe_is": round(_compute_sharpe(is_alpha, periods_per_year), 3),
                "sharpe_oos": round(_compute_sharpe(oos_alpha, periods_per_year), 3),
                "n_months_is": len(is_alpha),
                "n_months_oos": len(oos_alpha),
            })

        oos_sharpes = [w["sharpe_oos"] for w in wf_windows if w["n_months_oos"] > 0]
        wf_oos_mean = float(np.mean(oos_sharpes)) if oos_sharpes else 0.0
        wf_oos_std = float(np.std(oos_sharpes)) if oos_sharpes else 0.0
```

- [ ] **Step 4: Run tests**

Run: `conda run -n data_science pytest tests/test_walk_forward.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run existing tests to verify backward compat**

Run: `conda run -n data_science pytest tests/test_screen.py -v`
Expected: ALL PASS

- [ ] **Step 6: Run lint**

Run: `conda run -n data_science ruff check screen.py`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add screen.py tests/test_walk_forward.py
git commit -m "feat: add walk-forward evaluation to apply_screen"
```

### Task 8: Update run.py for walk-forward mode

**Files:**
- Modify: `run.py`

- [ ] **Step 1: Replace --split-date with --walk-forward in CLI**

Replace the `--split-date` argument with walk-forward arguments:

```python
    parser.add_argument("--no-walk-forward", dest="walk_forward",
                        action="store_false", default=True,
                        help="Disable walk-forward evaluation (use full-period Sharpe)")
    parser.add_argument("--train-months", type=int, default=18,
                        help="Walk-forward train window in months (default: 18)")
    parser.add_argument("--test-months", type=int, default=6,
                        help="Walk-forward test window in months (default: 6)")
```

- [ ] **Step 2: Update run_loop to pass walk-forward params**

Replace `split_date` usage in `run_loop()` with walk-forward:

```python
def run_loop(
    n_iterations: int = None,
    hours: float = None,
    patience: int = 20,
    walk_forward: bool = False,
    train_months: int = 18,
    test_months: int = 6,
):
```

And update the `apply_screen` call:

```python
        result = apply_screen(
            screen_def, features,
            walk_forward=walk_forward,
            train_months=train_months,
            test_months=test_months,
        )
```

Update the logging to show walk-forward metrics:

```python
        if walk_forward and 'wf_oos_sharpe_mean' in result:
            print(f"WF OOS Sharpe (mean): {result['wf_oos_sharpe_mean']:.3f}")
            print(f"WF OOS Sharpe (std):  {result['wf_oos_sharpe_std']:.3f}")
            print(f"WF windows:           {result['wf_n_windows']}")
```

- [ ] **Step 3: Update the analysis prompt in analyze_results()**

Update the LLM interpretation prompt to reference walk-forward instead of single-split OOS.

- [ ] **Step 4: Run lint**

Run: `conda run -n data_science ruff check run.py`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add run.py
git commit -m "feat: replace --split-date with --walk-forward in run.py"
```

### Task 9: Update analyze.py for walk-forward results

**Files:**
- Modify: `analyze.py`

- [ ] **Step 1: Update section_oos for walk-forward data**

The OOS section should handle both old-style `sharpe_is/sharpe_oos` results and
new walk-forward `wf_oos_sharpe_mean` results. Update `build_df` to read the
walk-forward fields and update `section_oos` accordingly.

In `build_df`, add:
```python
            "wf_oos_sharpe_mean": r.get("wf_oos_sharpe_mean", float("nan")),
            "wf_oos_sharpe_std": r.get("wf_oos_sharpe_std", float("nan")),
            "wf_n_windows": r.get("wf_n_windows", 0),
```

Update `section_oos` to display walk-forward window stats when available.

- [ ] **Step 2: Run lint**

Run: `conda run -n data_science ruff check analyze.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add analyze.py
git commit -m "feat: update analyze.py to handle walk-forward results"
```

---

## Chunk 3: Extended Data + New Features (Direction C)

Add new price-derived features and extend the data history to 2014 for more
walk-forward windows.

### Task 10: Extend data start date

**Files:**
- Modify: `data.py:27`
- Modify: `screen.py` (apply_screen default start)

- [ ] **Step 1: Change data.py default start to 2014-01-01**

In `download_prices`:
```python
def download_prices(tickers: list[str], start: str = "2014-01-01",
                    end: str = "2025-12-31",
                    batch_size: int = 20) -> pd.DataFrame:
```

- [ ] **Step 2: Change apply_screen default start to 2015-01-01**

Start backtest 1 year after data start to allow warmup for 12-month features:
```python
def apply_screen(
    screen_def: dict,
    features: pd.DataFrame,
    start: str = "2015-01-01",
    end: str = "2025-12-31",
    ...
```

- [ ] **Step 3: Update feature_stats.py date range**

Change line 28 from `"2020-01-01"` to `"2015-01-01"`:
```python
    date_range = close.loc["2015-01-01":"2025-12-31"].index
```

- [ ] **Step 4: Update the date range reference in feature_stats write_feature_stats**

Line 257: change "2020-01" to "2015-01".

- [ ] **Step 5: Run lint**

Run: `conda run -n data_science ruff check data.py screen.py feature_stats.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add data.py screen.py feature_stats.py
git commit -m "feat: extend data history to 2014, backtest from 2015"
```

### Task 11: Add new price-derived features (TDD)

**Files:**
- Modify: `screen.py` (compute_price_features)
- Create: `tests/test_new_features.py`

- [ ] **Step 1: Write failing tests for new features**

```python
"""Tests for new price-derived features."""
import numpy as np
import pandas as pd
import pytest
from pathlib import Path


def test_return_1w_synthetic():
    """Test 5-day return feature on synthetic data."""
    from screen import compute_price_features

    dates = pd.date_range("2024-01-01", periods=30, freq="B")
    tickers = ["AAPL", "GOOG"]
    close_data = pd.DataFrame(
        {
            "AAPL": np.linspace(100, 130, 30),
            "GOOG": np.linspace(200, 180, 30),
        },
        index=dates,
    )
    prices = pd.concat({
        "Close": close_data,
        "High": close_data * 1.02,
        "Low": close_data * 0.98,
        "Volume": pd.DataFrame(1e6, index=dates, columns=tickers),
    }, axis=1)

    features = compute_price_features(prices)
    assert "return_1w" in features.columns.get_level_values(0)
    # AAPL going up -> positive 1w return after warmup
    vals = features["return_1w"]["AAPL"].dropna()
    assert len(vals) > 0
    assert vals.iloc[-1] > 0


def test_return_12m_skip_1m_synthetic():
    """Test 12m momentum skipping most recent month."""
    from screen import compute_price_features

    dates = pd.date_range("2023-01-01", periods=300, freq="B")
    tickers = ["AAPL"]
    close_data = pd.DataFrame(
        {"AAPL": np.linspace(100, 200, 300)},
        index=dates,
    )
    prices = pd.concat({
        "Close": close_data,
        "High": close_data * 1.02,
        "Low": close_data * 0.98,
        "Volume": pd.DataFrame(1e6, index=dates, columns=tickers),
    }, axis=1)

    features = compute_price_features(prices)
    assert "return_12m_skip_1m" in features.columns.get_level_values(0)
    vals = features["return_12m_skip_1m"]["AAPL"].dropna()
    assert len(vals) > 0


def test_idio_vol_synthetic():
    """Test idiosyncratic volatility."""
    from screen import compute_price_features

    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    # SPY has smooth returns, AAPL has extra noise (high idio vol)
    spy_rets = np.random.normal(0.0005, 0.01, 100)
    aapl_rets = spy_rets * 1.2 + np.random.normal(0, 0.02, 100)
    goog_rets = spy_rets * 0.8 + np.random.normal(0, 0.005, 100)

    spy_close = pd.Series(100 * np.cumprod(1 + spy_rets), index=dates, name="SPY")
    aapl_close = pd.Series(150 * np.cumprod(1 + aapl_rets), index=dates, name="AAPL")
    goog_close = pd.Series(200 * np.cumprod(1 + goog_rets), index=dates, name="GOOG")

    close_data = pd.concat([spy_close, aapl_close, goog_close], axis=1)
    prices = pd.concat({
        "Close": close_data,
        "High": close_data * 1.01,
        "Low": close_data * 0.99,
        "Volume": pd.DataFrame(1e6, index=dates, columns=["SPY", "AAPL", "GOOG"]),
    }, axis=1)

    features = compute_price_features(prices)
    assert "idio_vol" in features.columns.get_level_values(0)
    # AAPL should have higher idio vol than GOOG (more residual noise)
    aapl_iv = features["idio_vol"]["AAPL"].dropna().iloc[-1]
    goog_iv = features["idio_vol"]["GOOG"].dropna().iloc[-1]
    assert aapl_iv > goog_iv


def test_volume_change_20d_synthetic():
    """Test volume change (20d/60d ratio)."""
    from screen import compute_price_features

    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    tickers = ["AAPL"]
    close_data = pd.DataFrame(
        {"AAPL": np.linspace(100, 120, 100)}, index=dates,
    )
    # Volume doubles in second half
    vol_data = pd.DataFrame(
        {"AAPL": [1e6] * 50 + [2e6] * 50}, index=dates,
    )
    prices = pd.concat({
        "Close": close_data,
        "High": close_data * 1.02,
        "Low": close_data * 0.98,
        "Volume": vol_data,
    }, axis=1)

    features = compute_price_features(prices)
    assert "volume_change_20d" in features.columns.get_level_values(0)
    # At end, 20d avg should be ~2e6, 60d avg ~1.67e6 -> ratio > 1
    val = features["volume_change_20d"]["AAPL"].iloc[-1]
    assert val > 1.0


def test_new_features_on_real_data():
    """New features exist on real cached data."""
    if not Path("data/prices.parquet").exists():
        pytest.skip("No cached data")
    from screen import compute_price_features

    prices = pd.read_parquet(Path("data/prices.parquet"))
    features = compute_price_features(prices)
    for feat in ["return_1w", "return_12m_skip_1m", "idio_vol", "volume_change_20d"]:
        assert feat in features.columns.get_level_values(0), f"Missing: {feat}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n data_science pytest tests/test_new_features.py -v`
Expected: FAIL (features don't exist yet)

- [ ] **Step 3: Implement new features in compute_price_features**

Add to `compute_price_features()` in `screen.py`, after existing features:

```python
    # Short-term reversal (1-week return)
    features["return_1w"] = close.pct_change(5)

    # Classic momentum: 12-month return skipping most recent month
    # (Jegadeesh-Titman formulation avoids short-term reversal contamination)
    ret_12m = close.pct_change(252)
    ret_1m = close.pct_change(21)
    features["return_12m_skip_1m"] = (1 + ret_12m) / (1 + ret_1m) - 1

    # Idiosyncratic volatility: residual vol after removing market beta
    # Uses SPY as market proxy, 60-day rolling beta, 20-day residual vol
    if "SPY" in close.columns:
        spy_ret = daily_ret["SPY"] if "SPY" in daily_ret.columns else close["SPY"].pct_change()
        window = 60
        # Vectorized: rolling covariance of each stock with SPY
        cov_with_spy = daily_ret.rolling(window).cov(spy_ret)
        spy_var = spy_ret.rolling(window).var()
        beta = cov_with_spy.div(spy_var.clip(lower=1e-10), axis=0)
        residual = daily_ret.sub(beta.mul(spy_ret, axis=0))
        features["idio_vol"] = residual.rolling(20).std() * np.sqrt(252)

    # Volume flow proxy: 20d avg dollar volume / 60d avg dollar volume
    features["volume_change_20d"] = (
        dollar_vol.rolling(20).mean() / dollar_vol.rolling(60).mean()
    )
```

- [ ] **Step 4: Run tests**

Run: `conda run -n data_science pytest tests/test_new_features.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `conda run -n data_science pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Run lint**

Run: `conda run -n data_science ruff check screen.py`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add screen.py tests/test_new_features.py
git commit -m "feat: add return_1w, return_12m_skip_1m, idio_vol, volume_change_20d features"
```

### Task 12: Update program.md with new features

**Files:**
- Modify: `program.md`

- [ ] **Step 1: Add new features to the Available features section**

Append to the Price-derived section:
```
- return_1w: 5-day return (short-term reversal signal)
- return_12m_skip_1m: 12-month return skipping most recent month (classic momentum)
- idio_vol: idiosyncratic volatility (residual vol after removing market beta)
- volume_change_20d: 20d avg dollar volume / 60d avg (flow proxy)
```

- [ ] **Step 2: Commit**

```bash
git add program.md
git commit -m "docs: add new features to program.md"
```

### Task 13: Re-download extended data

**Files:** None (runtime task)

- [ ] **Step 1: Re-download with extended date range**

Run: `conda run -n data_science python data.py --force`

This will download price data from 2014-01-01 (takes ~15-20 min).

- [ ] **Step 2: Verify data**

```bash
conda run -n data_science python -c "
import pandas as pd
prices = pd.read_parquet('data/prices.parquet')
print(f'Date range: {prices.index[0]} to {prices.index[-1]}')
print(f'Shape: {prices.shape}')
print(f'Tickers: {len(prices.columns.get_level_values(1).unique())}')
"
```

Expected: Date range starts around 2014-01-02.

- [ ] **Step 3: Regenerate feature_stats.md**

Run: `conda run -n data_science python feature_stats.py`

This now uses 2015-2025 data, producing more robust IC estimates.

- [ ] **Step 4: Commit updated feature_stats**

```bash
git add feature_stats.md
git commit -m "data: regenerate feature_stats.md with 2015-2025 data and new features"
```

### Task 14: Smoke test the full pipeline

- [ ] **Step 1: Run a single walk-forward iteration**

```bash
conda run -n data_science python run.py -n 1
```

Walk-forward is now the default. Use `--no-walk-forward` to disable.

Verify:
- LLM proposes a score-based screen (check stdout)
- Walk-forward metrics are printed (WF OOS Sharpe mean, std, windows)
- Result appended to results.jsonl with walk-forward fields

- [ ] **Step 2: Run full test suite one more time**

Run: `conda run -n data_science pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 3: Run lint on all modified files**

Run: `conda run -n data_science ruff check data.py screen.py run.py analyze.py feature_stats.py`
Expected: No errors

- [ ] **Step 4: Update CLAUDE.md commands section**

Replace `--split-date` references with walk-forward. Update the example commands:
```bash
# Run N iterations (walk-forward evaluation is default)
conda run -n data_science python run.py -n 10

# Run without walk-forward (full-period Sharpe only)
conda run -n data_science python run.py -n 10 --no-walk-forward
```

- [ ] **Step 5: Final commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md commands for walk-forward default"
```
