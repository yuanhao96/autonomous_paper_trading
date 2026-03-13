# Screen Mode Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `--screen` mode to `run.py` that selects top-K screens from historical results, refreshes market data, runs them on today's snapshot, and generates a markdown report with company write-ups enriched by Claude.

**Architecture:** New module `screen_report.py` handles screen selection (Sharpe + diversity), live screening, company context gathering (yfinance `.info` + Claude), and markdown report rendering. `run.py` gains a `--screen` CLI flag that delegates to this module. Reports saved to `reports/YYYY-MM-DD/report.md`.

**Tech Stack:** Python, pandas, yfinance, Claude Code CLI (`claude -p`), existing `screen.py` features + `data.py` cache.

---

## Chunk 1: Screen Selection Logic

### Task 1: Select top-K screens with diversity

**Files:**
- Create: `screen_report.py`
- Create: `tests/test_screen_report.py`

The selection algorithm:
1. Load all KEEP screens from `results.jsonl` (Sharpe >= 0.3)
2. For each, load its stock_details archive → extract last period's stock set
3. Greedy pick: best Sharpe first, then for each remaining candidate, score = `sharpe_normalized - 0.5 * max_jaccard_overlap_with_selected`. Pick highest score.
4. Repeat until K screens selected.

- [ ] **Step 1: Write failing test for `load_keep_screens`**

```python
# tests/test_screen_report.py
import json
import tempfile
from pathlib import Path

from screen_report import load_keep_screens


def test_load_keep_screens(tmp_path):
    """Load only KEEP screens (Sharpe >= 0.3) with their index."""
    results = [
        {"name": "good", "sharpe": 0.5, "filters": [], "hypothesis": "x",
         "alpha_monthly_mean": 0.01, "alpha_annual": 0.12, "win_rate": 0.6,
         "n_months": 12, "n_avg_stocks": 15, "holding_days": 21,
         "monthly_details": []},
        {"name": "bad", "sharpe": 0.1, "filters": [], "hypothesis": "y",
         "alpha_monthly_mean": 0.001, "alpha_annual": 0.01, "win_rate": 0.4,
         "n_months": 12, "n_avg_stocks": 10, "holding_days": 21,
         "monthly_details": []},
        {"name": "great", "sharpe": 1.2, "filters": [], "hypothesis": "z",
         "alpha_monthly_mean": 0.03, "alpha_annual": 0.36, "win_rate": 0.7,
         "n_months": 12, "n_avg_stocks": 18, "holding_days": 42,
         "monthly_details": []},
    ]
    jsonl = tmp_path / "results.jsonl"
    with open(jsonl, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    keeps = load_keep_screens(jsonl)
    assert len(keeps) == 2
    # Sorted by sharpe desc
    assert keeps[0]["name"] == "great"
    assert keeps[1]["name"] == "good"
    # Each has an 'idx' field for stock_details lookup
    assert keeps[0]["idx"] == 2
    assert keeps[1]["idx"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n data_science pytest tests/test_screen_report.py::test_load_keep_screens -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'screen_report'`

- [ ] **Step 3: Implement `load_keep_screens`**

```python
# screen_report.py
"""Screen mode: run top screens on today's market and generate reports."""
import json
from pathlib import Path

RESULTS_PATH = Path("results.jsonl")
DETAILS_DIR = Path("data/details")
REPORTS_DIR = Path("reports")
SHARPE_THRESHOLD = 0.3


def load_keep_screens(results_path: Path = RESULTS_PATH) -> list[dict]:
    """Load KEEP screens from results.jsonl, sorted by Sharpe descending.

    Each result gets an 'idx' field (0-based line number) for stock_details lookup.
    """
    keeps = []
    with open(results_path) as f:
        for idx, line in enumerate(f):
            r = json.loads(line.strip())
            if r["sharpe"] >= SHARPE_THRESHOLD:
                r["idx"] = idx
                keeps.append(r)
    keeps.sort(key=lambda r: r["sharpe"], reverse=True)
    return keeps
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n data_science pytest tests/test_screen_report.py::test_load_keep_screens -v`
Expected: PASS

- [ ] **Step 5: Write failing test for `select_diverse_screens`**

```python
# tests/test_screen_report.py (append)
from screen_report import select_diverse_screens


def test_select_diverse_screens_prefers_diversity(tmp_path):
    """When two screens have similar Sharpe but different stocks, pick diverse."""
    details_dir = tmp_path / "details"
    details_dir.mkdir()

    # Screen 0: stocks A, B, C
    with open(details_dir / "0.json", "w") as f:
        json.dump([{"month": "2025-06-01", "stocks": {"A": 0.01, "B": 0.02, "C": 0.03}}], f)
    # Screen 1: stocks A, B, D — high overlap with 0
    with open(details_dir / "1.json", "w") as f:
        json.dump([{"month": "2025-06-01", "stocks": {"A": 0.01, "B": 0.02, "D": 0.03}}], f)
    # Screen 2: stocks X, Y, Z — zero overlap with 0
    with open(details_dir / "2.json", "w") as f:
        json.dump([{"month": "2025-06-01", "stocks": {"X": 0.01, "Y": 0.02, "Z": 0.03}}], f)

    screens = [
        {"name": "best", "sharpe": 1.0, "idx": 0, "filters": []},
        {"name": "similar", "sharpe": 0.9, "idx": 1, "filters": []},
        {"name": "diverse", "sharpe": 0.85, "idx": 2, "filters": []},
    ]

    selected = select_diverse_screens(screens, k=2, details_dir=details_dir)
    assert len(selected) == 2
    assert selected[0]["name"] == "best"
    # Should prefer "diverse" over "similar" despite lower Sharpe
    assert selected[1]["name"] == "diverse"


def test_select_diverse_screens_k_larger_than_available(tmp_path):
    """If K > available screens, return all."""
    details_dir = tmp_path / "details"
    details_dir.mkdir()
    with open(details_dir / "0.json", "w") as f:
        json.dump([{"month": "2025-06-01", "stocks": {"A": 0.01}}], f)

    screens = [{"name": "only", "sharpe": 0.5, "idx": 0, "filters": []}]
    selected = select_diverse_screens(screens, k=3, details_dir=details_dir)
    assert len(selected) == 1
```

- [ ] **Step 6: Run test to verify it fails**

Run: `conda run -n data_science pytest tests/test_screen_report.py::test_select_diverse_screens_prefers_diversity -v`
Expected: FAIL — `ImportError: cannot import name 'select_diverse_screens'`

- [ ] **Step 7: Implement `select_diverse_screens`**

```python
# screen_report.py (append)

def _load_last_stocks(idx: int, details_dir: Path = DETAILS_DIR) -> set[str]:
    """Load the last period's stock set from archived details."""
    archive = details_dir / f"{idx}.json"
    if not archive.exists():
        return set()
    with open(archive) as f:
        periods = json.load(f)
    if not periods:
        return set()
    return set(periods[-1].get("stocks", {}).keys())


def _jaccard(a: set, b: set) -> float:
    """Jaccard similarity: |intersection| / |union|. 0 if both empty."""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def select_diverse_screens(
    screens: list[dict], k: int = 3,
    details_dir: Path = DETAILS_DIR, overlap_penalty: float = 0.5,
) -> list[dict]:
    """Greedy selection: best Sharpe first, then maximize Sharpe - penalty * overlap.

    Args:
        screens: KEEP screens sorted by Sharpe desc (from load_keep_screens).
        k: Number of screens to select.
        details_dir: Path to archived stock details.
        overlap_penalty: Weight for Jaccard overlap penalty (0-1).

    Returns:
        List of k selected screens (or fewer if not enough available).
    """
    if len(screens) <= k:
        return list(screens)

    # Pre-load stock sets
    stock_sets = {s["idx"]: _load_last_stocks(s["idx"], details_dir) for s in screens}

    # Normalize Sharpe to [0, 1] for fair comparison with overlap
    max_sharpe = screens[0]["sharpe"]
    min_sharpe = screens[-1]["sharpe"]
    sharpe_range = max_sharpe - min_sharpe if max_sharpe > min_sharpe else 1.0

    selected = [screens[0]]  # Best Sharpe always first
    remaining = list(screens[1:])

    while len(selected) < k and remaining:
        best_score = -float("inf")
        best_idx = 0
        for i, cand in enumerate(remaining):
            norm_sharpe = (cand["sharpe"] - min_sharpe) / sharpe_range
            max_overlap = max(
                _jaccard(stock_sets[cand["idx"]], stock_sets[s["idx"]])
                for s in selected
            )
            score = norm_sharpe - overlap_penalty * max_overlap
            if score > best_score:
                best_score = score
                best_idx = i
        selected.append(remaining.pop(best_idx))

    return selected
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `conda run -n data_science pytest tests/test_screen_report.py -v`
Expected: All 3 tests PASS

- [ ] **Step 9: Commit**

```bash
git add screen_report.py tests/test_screen_report.py
git commit -m "feat: add screen selection with Sharpe + diversity"
```

---

## Chunk 2: Live Screening on Today's Data

### Task 2: Run a screen definition on current market snapshot

**Files:**
- Modify: `screen_report.py`
- Modify: `tests/test_screen_report.py`

This reuses `screen.py`'s `_apply_filters` and `_rank_and_select` but runs on the last available date instead of backtesting over a range.

- [ ] **Step 1: Write failing test for `run_screen_today`**

```python
# tests/test_screen_report.py (append)
import numpy as np
import pandas as pd
from screen_report import run_screen_today


def test_run_screen_today_synthetic():
    """Run a screen on synthetic feature data, get back selected tickers + features."""
    dates = pd.date_range("2025-01-01", periods=5, freq="B")
    tickers = ["AAPL", "GOOG", "MSFT", "AMZN", "META"]
    ret = pd.DataFrame(
        [[0.1, 0.2, -0.05, 0.15, 0.3]] * 5,
        index=dates, columns=tickers,
    )
    vol = pd.DataFrame(
        [[0.2, 0.15, 0.3, 0.25, 0.1]] * 5,
        index=dates, columns=tickers,
    )
    features = pd.concat({"return_6m": ret, "volatility_20d": vol}, axis=1)

    screen_def = {
        "name": "test",
        "hypothesis": "test",
        "filters": [{"feature": "return_6m", "op": ">", "value": 0.05}],
        "top_n": 3,
        "rank_by": "return_6m",
        "rank_order": "desc",
    }

    result = run_screen_today(screen_def, features)
    assert "tickers" in result
    assert "date" in result
    assert "ticker_features" in result
    # META (0.3), GOOG (0.2), AMZN (0.15) — top 3 by return_6m
    assert result["tickers"] == ["META", "GOOG", "AMZN"]
    # Each ticker has feature values
    assert "META" in result["ticker_features"]
    assert "return_6m" in result["ticker_features"]["META"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n data_science pytest tests/test_screen_report.py::test_run_screen_today_synthetic -v`
Expected: FAIL — `ImportError: cannot import name 'run_screen_today'`

- [ ] **Step 3: Implement `run_screen_today`**

```python
# screen_report.py (append)
import pandas as pd
from screen import _apply_filters, _rank_and_select


def run_screen_today(
    screen_def: dict, features: pd.DataFrame,
) -> dict:
    """Run a screen on the most recent date in features.

    Returns dict with:
        date: str — the screening date
        tickers: list[str] — selected tickers in rank order
        ticker_features: dict[str, dict[str, float]] — feature values per ticker
    """
    last_date = features.index[-1]
    passing = _apply_filters(features, screen_def["filters"], last_date)
    selected = _rank_and_select(passing, features, last_date, screen_def)

    # Gather feature values for selected tickers
    feat_names = features.columns.get_level_values(0).unique()
    ticker_features = {}
    for ticker in selected:
        vals = {}
        for feat in feat_names:
            if ticker in features[feat].columns:
                v = features.loc[last_date, (feat, ticker)]
                if pd.notna(v):
                    vals[feat] = round(float(v), 4)
        ticker_features[ticker] = vals

    return {
        "date": str(last_date.date()),
        "tickers": selected,
        "ticker_features": ticker_features,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n data_science pytest tests/test_screen_report.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add screen_report.py tests/test_screen_report.py
git commit -m "feat: add live screening on current market snapshot"
```

### Task 3: Data refresh trigger

**Files:**
- Modify: `screen_report.py`

- [ ] **Step 1: Implement `refresh_data`**

```python
# screen_report.py (append)
import subprocess
import sys


def refresh_data():
    """Re-download market data by running data.py --force."""
    print("Refreshing market data...")
    result = subprocess.run(
        [sys.executable, "data.py", "--force"],
        timeout=1800,  # 30 min for full download
    )
    if result.returncode != 0:
        raise RuntimeError("data.py --force failed")
    print("Data refresh complete.")
```

- [ ] **Step 2: Commit**

```bash
git add screen_report.py
git commit -m "feat: add data refresh trigger for screen mode"
```

---

## Chunk 3: Company Context + Report Generation

### Task 4: Gather company context via yfinance

**Files:**
- Modify: `screen_report.py`
- Modify: `tests/test_screen_report.py`

- [ ] **Step 1: Write failing test for `gather_company_info`**

```python
# tests/test_screen_report.py (append)
from screen_report import gather_company_info


def test_gather_company_info_returns_dict():
    """Should return a dict with basic company fields."""
    info = gather_company_info("AAPL")
    assert isinstance(info, dict)
    assert "name" in info
    assert "sector" in info
    assert "summary" in info
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n data_science pytest tests/test_screen_report.py::test_gather_company_info_returns_dict -v`
Expected: FAIL — `ImportError: cannot import name 'gather_company_info'`

- [ ] **Step 3: Implement `gather_company_info`**

```python
# screen_report.py (append)
import yfinance as yf


def gather_company_info(ticker: str) -> dict:
    """Fetch company info from yfinance. Returns dict with key fields."""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception:
        info = {}

    return {
        "name": info.get("longName") or info.get("shortName") or ticker,
        "sector": info.get("sector", "Unknown"),
        "industry": info.get("industry", "Unknown"),
        "market_cap": info.get("marketCap"),
        "summary": info.get("longBusinessSummary", ""),
        "forward_pe": info.get("forwardPE"),
        "trailing_pe": info.get("trailingPE"),
        "dividend_yield": info.get("dividendYield"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "analyst_target": info.get("targetMeanPrice"),
        "recommendation": info.get("recommendationKey"),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n data_science pytest tests/test_screen_report.py::test_gather_company_info_returns_dict -v`
Expected: PASS (requires network access)

- [ ] **Step 5: Commit**

```bash
git add screen_report.py tests/test_screen_report.py
git commit -m "feat: add yfinance company info gathering"
```

### Task 5: Generate Claude-enriched company write-up

**Files:**
- Modify: `screen_report.py`

- [ ] **Step 1: Implement `generate_company_writeup`**

Uses `_claude_call` from `run.py` to enrich company context with Claude's knowledge.

```python
# screen_report.py (append)
from run import _claude_call


def generate_company_writeup(
    ticker: str, company_info: dict, feature_vals: dict,
    screen_name: str, n_screens_in: int, total_screens: int,
) -> str:
    """Generate a 2-4 sentence company write-up using Claude.

    Provides yfinance info + feature values as grounding, asks Claude
    to add recent context (earnings, news, strategic moves).
    """
    # Format feature highlights (top features by pctrank)
    pctrank_feats = {
        k: v for k, v in feature_vals.items()
        if k.endswith("_pctrank") and v is not None
    }
    top_feats = sorted(pctrank_feats.items(), key=lambda x: x[1], reverse=True)[:5]
    feat_lines = "\n".join(
        f"  - {k}: {v:.0%}" for k, v in top_feats
    )

    market_cap_str = ""
    if company_info.get("market_cap"):
        mc = company_info["market_cap"]
        if mc >= 1e12:
            market_cap_str = f"${mc/1e12:.1f}T"
        elif mc >= 1e9:
            market_cap_str = f"${mc/1e9:.0f}B"
        else:
            market_cap_str = f"${mc/1e6:.0f}M"

    prompt = (
        f"Write a concise investment context paragraph (3-5 sentences) for {ticker} "
        f"({company_info['name']}).\n\n"
        f"Company: {company_info['name']}\n"
        f"Sector: {company_info['sector']} / {company_info['industry']}\n"
        f"Market cap: {market_cap_str}\n"
        f"Forward P/E: {company_info.get('forward_pe', 'N/A')}\n"
        f"Analyst target: ${company_info.get('analyst_target', 'N/A')}\n"
        f"Recommendation: {company_info.get('recommendation', 'N/A')}\n\n"
        f"This stock was selected by screen '{screen_name}' "
        f"(appears in {n_screens_in}/{total_screens} screens).\n"
        f"Top percentile rank features:\n{feat_lines}\n\n"
        f"Include: what the company does, recent developments (earnings, "
        f"product launches, macro headwinds/tailwinds), and why the screen's "
        f"quantitative signals make sense given the fundamental picture. "
        f"Be factual. If you're unsure about very recent events, say so. "
        f"Output ONLY the paragraph, no headers or preamble."
    )

    try:
        return _claude_call(prompt, timeout=60, allowed_tools=[]).strip()
    except Exception as e:
        return f"(Could not generate write-up: {e})"
```

- [ ] **Step 2: Commit**

```bash
git add screen_report.py
git commit -m "feat: add Claude-enriched company write-up generation"
```

### Task 6: Render the full markdown report

**Files:**
- Modify: `screen_report.py`
- Modify: `tests/test_screen_report.py`

- [ ] **Step 1: Write failing test for `render_report`**

```python
# tests/test_screen_report.py (append)
from screen_report import render_report


def test_render_report_structure():
    """Report should contain key sections."""
    screens = [
        {
            "name": "Test Screen",
            "hypothesis": "testing hypothesis",
            "sharpe": 0.8,
            "holding_days": 21,
            "filters": [{"feature": "return_6m", "op": ">", "value": 0.1}],
        }
    ]
    screen_results = [
        {
            "date": "2025-03-13",
            "tickers": ["AAPL", "MSFT"],
            "ticker_features": {
                "AAPL": {"return_6m": 0.15, "return_6m_pctrank": 0.85},
                "MSFT": {"return_6m": 0.12, "return_6m_pctrank": 0.78},
            },
        }
    ]
    company_writeups = {
        "AAPL": "Apple is a tech company...",
        "MSFT": "Microsoft is a software company...",
    }
    company_infos = {
        "AAPL": {"name": "Apple Inc.", "sector": "Technology",
                  "industry": "Consumer Electronics", "market_cap": 3e12},
        "MSFT": {"name": "Microsoft", "sector": "Technology",
                 "industry": "Software", "market_cap": 2.8e12},
    }
    ticker_screen_counts = {"AAPL": 1, "MSFT": 1}

    md = render_report(
        screens, screen_results, company_writeups,
        company_infos, ticker_screen_counts,
    )

    assert "# Screen Report" in md
    assert "Test Screen" in md
    assert "AAPL" in md
    assert "Apple is a tech company" in md
    assert "Consensus Picks" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n data_science pytest tests/test_screen_report.py::test_render_report_structure -v`
Expected: FAIL

- [ ] **Step 3: Implement `render_report`**

```python
# screen_report.py (append)
from datetime import date


def _format_market_cap(mc) -> str:
    if not mc:
        return "N/A"
    if mc >= 1e12:
        return f"${mc/1e12:.1f}T"
    if mc >= 1e9:
        return f"${mc/1e9:.0f}B"
    return f"${mc/1e6:.0f}M"


def render_report(
    screens: list[dict],
    screen_results: list[dict],
    company_writeups: dict[str, str],
    company_infos: dict[str, dict],
    ticker_screen_counts: dict[str, int],
) -> str:
    """Render the full screen report as markdown."""
    today = screen_results[0]["date"] if screen_results else str(date.today())
    lines = [f"# Screen Report — {today}\n"]

    # Screens overview table
    lines.append("## Screens Selected\n")
    lines.append("| # | Screen | Sharpe | Holding | Hypothesis |")
    lines.append("|---|--------|--------|---------|------------|")
    for i, s in enumerate(screens, 1):
        hd = s.get("holding_days", 21)
        lines.append(
            f"| {i} | {s['name']} | {s['sharpe']:.3f} | {hd}d | "
            f"{s.get('hypothesis', '')[:80]} |"
        )
    lines.append("")

    # Per-screen detail
    for i, (screen, result) in enumerate(zip(screens, screen_results), 1):
        lines.append(f"## Screen {i}: {screen['name']}\n")
        lines.append(f"**Hypothesis:** {screen.get('hypothesis', 'N/A')}\n")
        lines.append(f"**Backtest Sharpe:** {screen['sharpe']:.3f} | "
                     f"**Holding:** {screen.get('holding_days', 21)}d\n")

        # Filters
        lines.append("**Filters:**")
        for f in screen.get("filters", []):
            val = f["value"]
            if isinstance(val, list):
                val_str = f"[{val[0]}, {val[1]}]"
            else:
                val_str = str(val)
            lines.append(f"- `{f['feature']}` {f['op']} {val_str}")
        lines.append("")

        # Selected stocks table
        lines.append(f"**Stocks selected ({len(result['tickers'])}):**\n")
        lines.append("| Ticker | Company | Sector | Mkt Cap | In # Screens |")
        lines.append("|--------|---------|--------|---------|-------------|")
        for ticker in result["tickers"]:
            info = company_infos.get(ticker, {})
            mc = _format_market_cap(info.get("market_cap"))
            n_in = ticker_screen_counts.get(ticker, 0)
            lines.append(
                f"| {ticker} | {info.get('name', ticker)} | "
                f"{info.get('sector', '?')} | {mc} | {n_in} |"
            )
        lines.append("")

        # Per-stock write-ups
        for ticker in result["tickers"]:
            info = company_infos.get(ticker, {})
            lines.append(f"### {ticker} — {info.get('name', ticker)}\n")
            writeup = company_writeups.get(ticker, "No write-up available.")
            lines.append(f"{writeup}\n")

            # Key feature values
            feats = result["ticker_features"].get(ticker, {})
            pctranks = {
                k: v for k, v in feats.items()
                if k.endswith("_pctrank")
            }
            if pctranks:
                top = sorted(pctranks.items(), key=lambda x: x[1], reverse=True)[:6]
                feat_str = " | ".join(f"`{k}`: {v:.0%}" for k, v in top)
                lines.append(f"**Top features:** {feat_str}\n")
        lines.append("")

    # Consensus picks
    consensus = {
        t: c for t, c in ticker_screen_counts.items() if c >= 2
    }
    if consensus:
        lines.append("## Consensus Picks\n")
        lines.append(
            "Stocks appearing in 2+ screens deserve extra attention.\n"
        )
        lines.append("| Ticker | Company | Screens |")
        lines.append("|--------|---------|---------|")
        for t, c in sorted(consensus.items(), key=lambda x: -x[1]):
            info = company_infos.get(t, {})
            lines.append(f"| {t} | {info.get('name', t)} | {c} |")
        lines.append("")
    else:
        lines.append("## Consensus Picks\n")
        lines.append("No stocks appeared in 2+ screens.\n")

    lines.append("---\n")
    lines.append("*Generated by AutoScreen*\n")

    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n data_science pytest tests/test_screen_report.py::test_render_report_structure -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add screen_report.py tests/test_screen_report.py
git commit -m "feat: add markdown report renderer"
```

---

## Chunk 4: Orchestration + CLI Integration

### Task 7: Main `run_screen_mode` orchestrator

**Files:**
- Modify: `screen_report.py`

- [ ] **Step 1: Implement `run_screen_mode`**

```python
# screen_report.py (append)
from screen import compute_all_features


def run_screen_mode(k: int = 3, skip_refresh: bool = False):
    """Full screen mode pipeline: select → refresh → screen → report.

    Args:
        k: Number of top screens to run.
        skip_refresh: If True, skip data refresh (use cached data).
    """
    # Step 1: Load and select screens
    print(f"Loading results from {RESULTS_PATH}...")
    keeps = load_keep_screens()
    if not keeps:
        print("No KEEP screens found in results.jsonl. Run research mode first.")
        return

    selected = select_diverse_screens(keeps, k=k)
    print(f"Selected {len(selected)} screens (of {len(keeps)} KEEP):")
    for i, s in enumerate(selected, 1):
        print(f"  {i}. {s['name']} (Sharpe={s['sharpe']:.3f})")

    # Step 2: Refresh data
    if not skip_refresh:
        refresh_data()

    # Step 3: Compute features and run screens
    print("Computing features...")
    features = compute_all_features()
    print(f"Features ready: {features.shape}")

    screen_results = []
    for s in selected:
        print(f"Running screen: {s['name']}...")
        result = run_screen_today(s, features)
        screen_results.append(result)
        print(f"  Selected {len(result['tickers'])} stocks")

    # Step 4: Count consensus
    ticker_screen_counts = {}
    for result in screen_results:
        for ticker in result["tickers"]:
            ticker_screen_counts[ticker] = ticker_screen_counts.get(ticker, 0) + 1

    # Step 5: Gather company info + write-ups
    all_tickers = sorted(set(
        t for result in screen_results for t in result["tickers"]
    ))
    print(f"Gathering info for {len(all_tickers)} unique tickers...")

    company_infos = {}
    company_writeups = {}
    for ticker in all_tickers:
        print(f"  {ticker}...", end=" ", flush=True)
        company_infos[ticker] = gather_company_info(ticker)

        # Find which screen(s) this ticker appears in
        in_screens = [
            s["name"] for s, r in zip(selected, screen_results)
            if ticker in r["tickers"]
        ]
        # Use first screen for the write-up context
        first_result = next(
            r for r in screen_results if ticker in r["tickers"]
        )
        feat_vals = first_result["ticker_features"].get(ticker, {})

        writeup = generate_company_writeup(
            ticker, company_infos[ticker], feat_vals,
            in_screens[0],
            ticker_screen_counts[ticker],
            len(selected),
        )
        company_writeups[ticker] = writeup
        print("done")

    # Step 6: Render and save report
    report = render_report(
        selected, screen_results, company_writeups,
        company_infos, ticker_screen_counts,
    )

    report_date = screen_results[0]["date"] if screen_results else str(date.today())
    report_dir = REPORTS_DIR / report_date
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "report.md"
    report_path.write_text(report)

    # Also save screen definitions for reproducibility
    screens_json = [
        {
            "name": s["name"], "sharpe": s["sharpe"],
            "filters": s["filters"],
            "holding_days": s.get("holding_days", 21),
            "rank_by": s.get("rank_by"),
            "rank_order": s.get("rank_order"),
            "score": s.get("score"),
        }
        for s in selected
    ]
    (report_dir / "screens.json").write_text(
        json.dumps(screens_json, indent=2)
    )

    print(f"\nReport saved to {report_path}")
    print(f"Screens saved to {report_dir / 'screens.json'}")
    return report_path
```

- [ ] **Step 2: Commit**

```bash
git add screen_report.py
git commit -m "feat: add run_screen_mode orchestrator"
```

### Task 8: Add `--screen` flag to `run.py` CLI

**Files:**
- Modify: `run.py`

- [ ] **Step 1: Add `--screen` and `--top-k` arguments to `run.py`**

In `run.py`, modify the `if __name__ == "__main__"` block:

```python
# Replace the existing __main__ block at the bottom of run.py
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AutoScreen research loop")

    # Mode selection
    parser.add_argument("--screen", action="store_true",
                        help="Screen mode: run top screens on today's market")
    parser.add_argument("--top-k", type=int, default=3,
                        help="Number of screens to run in screen mode (default: 3)")
    parser.add_argument("--skip-refresh", action="store_true",
                        help="Skip data refresh in screen mode (use cached data)")

    # Research mode options
    parser.add_argument("-n", type=int, default=None,
                        help="Max number of iterations (default: unlimited)")
    parser.add_argument("--hours", type=float, default=None,
                        help="Time limit in hours (e.g. 8 for overnight)")
    parser.add_argument("--patience", type=int, default=20,
                        help="Stop after N iterations with no new KEEP (default: 20)")
    args = parser.parse_args()

    if args.screen:
        from screen_report import run_screen_mode
        run_screen_mode(k=args.top_k, skip_refresh=args.skip_refresh)
    else:
        # Default to 10 iterations if no stopping condition specified
        if args.n is None and args.hours is None:
            args.n = 10
        run_loop(n_iterations=args.n, hours=args.hours, patience=args.patience)
```

- [ ] **Step 2: Run all tests**

Run: `conda run -n data_science pytest tests/ -v`
Expected: All PASS

- [ ] **Step 3: Run ruff check**

Run: `conda run -n data_science ruff check screen_report.py run.py`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add run.py screen_report.py
git commit -m "feat: add --screen mode to run.py CLI"
```

---

## Chunk 5: Update Project Docs + .gitignore

### Task 9: Update CLAUDE.md and .gitignore

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.gitignore`

- [ ] **Step 1: Add `reports/` to .gitignore**

Append to `.gitignore`:
```
reports/
```

- [ ] **Step 2: Add screen mode command to CLAUDE.md commands section**

In the `## Commands` section, add:

```bash
# Screen mode: run top screens on today's market
conda run -n data_science python run.py --screen

# Screen mode with options
conda run -n data_science python run.py --screen --top-k 5 --skip-refresh
```

- [ ] **Step 3: Add screen_report.py to project structure**

In the `## Project Structure` section, add:
```
screen_report.py   # Screen mode: select top screens, run on today, generate reports
reports/           # Date-organized markdown reports (gitignored)
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md .gitignore
git commit -m "docs: add screen mode to project docs and gitignore reports/"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Screen selection (Sharpe + diversity) | `screen_report.py`, `tests/test_screen_report.py` |
| 2 | Live screening on today's snapshot | `screen_report.py`, `tests/test_screen_report.py` |
| 3 | Data refresh trigger | `screen_report.py` |
| 4 | Company info via yfinance | `screen_report.py`, `tests/test_screen_report.py` |
| 5 | Claude-enriched write-ups | `screen_report.py` |
| 6 | Markdown report renderer | `screen_report.py`, `tests/test_screen_report.py` |
| 7 | Orchestrator (`run_screen_mode`) | `screen_report.py` |
| 8 | CLI integration (`--screen`) | `run.py` |
| 9 | Docs + gitignore | `CLAUDE.md`, `.gitignore` |
