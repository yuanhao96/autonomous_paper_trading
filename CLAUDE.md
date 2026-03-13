# CLAUDE.md

## Project Purpose

AutoScreen: an autoresearch-style loop that autonomously discovers stock screens predicting forward returns on S&P 500.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — keep it dead simple. Claude Code CLI proposes a screen, the system backtests it, results get logged, repeat.

### History

- **v1** (`autonomou_evolving_investment`): Unbounded strategy space + custom infrastructure — failed
- **v2** (this repo, prior code): Over-engineered multi-stage pipeline with 133 alpha factors — most factors failed, combining them was meaningless
- **v3** (current): Start from scratch. One question: "which stocks will outperform?" Test screens in a tight loop.

## Key Principles

- **Simple loop**: propose screen → backtest → keep or discard → repeat
- **Free data only**: yfinance for price + quarterly fundamentals, cached as parquet
- **Claude Code CLI for reasoning**: `claude -p` proposes screens with full project context
- **No over-engineering**: functional style, no classes, no abstractions
- **knowledge/ is READ-ONLY**: The 145-doc knowledge base is reference material
- **factors/ is READ-ONLY**: The 133 factor docs are reference material

## Technology Stack

- **Language**: Python 3.10+
- **Data**: yfinance + local Parquet cache
- **Stats**: scipy (Spearman rank IC in feature_stats.py)
- **LLM**: Claude Code CLI (`claude -p`)
- **Conda env**: `data_science`
- **Testing**: pytest
- **Linting**: ruff (line-length 100)

## Commands

```bash
# One-time: download & cache S&P 500 data (~15-20 min)
conda run -n data_science python data.py

# Re-download data (quarterly refresh)
conda run -n data_science python data.py --force

# Run N iterations of autonomous screen research
conda run -n data_science python run.py -n 10

# Run with time limit + patience
conda run -n data_science python run.py --hours 8 --patience 20

# Compute per-feature predictive power stats
conda run -n data_science python feature_stats.py

# Run standalone analysis on past results
conda run -n data_science python analyze.py --section all

# Deep-dive a specific screen
conda run -n data_science python analyze.py --screen "screen name"

# Run tests
conda run -n data_science pytest tests/ -v

# Lint
conda run -n data_science ruff check data.py screen.py run.py analyze.py feature_stats.py
```

## Project Structure

```
data.py            # Download & cache S&P 500 price + fundamental data to parquet
screen.py          # Compute features (price, fundamental, sector, stability, pctrank),
                   #   apply JSON screen DSL, backtest with variable holding periods
analyze.py         # Multi-section analysis of results.jsonl (summary, features, thresholds,
                   #   regime, stocks, overlap, correlation, discards)
feature_stats.py   # Per-feature predictive power: rank IC, quintile long-short Sharpe,
                   #   conditional marginal IC → writes feature_stats.md
run.py             # Orchestration loop: analyze → propose → evaluate → log → repeat
program.md         # LLM instructions + available features (read by Claude Code at proposal time)
feature_stats.md   # Generated per-feature stats (read by Claude Code at proposal time)
analysis.md        # Generated research memo from analyze.py + LLM interpretation
results.jsonl      # Append-only machine-readable log of all screen evaluations
goal.md            # Current milestone requirements
knowledge/         # 145 curated docs — READ-ONLY reference
factors/           # 133 alpha factor docs — READ-ONLY reference
data/              # Cached parquet files (gitignored)
data/details/      # Archived per-stock monthly details (one JSON per screen)
tests/             # pytest tests
docs/plans/        # Implementation plans
```

## Screen DSL

The LLM proposes screens as JSON:

```json
{
  "name": "Momentum + quality quintile",
  "hypothesis": "Top-quintile momentum stocks with above-average quality outperform",
  "filters": [
    {"feature": "return_6m_pctrank", "op": ">", "value": 0.8},
    {"feature": "roe_pctrank", "op": ">", "value": 0.6},
    {"feature": "drawdown", "op": ">", "value": -0.07}
  ],
  "top_n": 20,
  "rank_by": "return_6m",
  "rank_order": "desc",
  "holding_days": 21
}
```

Operators: `>`, `<`, `>=`, `<=`, `==`, `!=`, `between` (value = [lo, hi])

Optional fields:
- **rank_by**: Feature to rank passing stocks by, or `"_score"` for composite ranking (default: none → alphabetical).
- **rank_order**: `"desc"` (highest first, default) or `"asc"` (lowest first).
- **holding_days**: Rebalance every N trading days (default: 21 ≈ monthly). Examples: 10 (biweekly), 21 (monthly), 42 (bimonthly).
- **score**: Weighted multi-factor composite for `rank_by: "_score"`. List of `{"feature": str, "weight": float}`. Negative weights invert (lower = better). Use `_pctrank` features for comparable scales.

## Available Features

### Price-derived (from daily OHLCV, full 2020-2025 coverage)
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

### Sector-relative (adapts to sector rotation — no hardcoded sector bets)
| Feature | Description |
|---------|-------------|
| `sector_return_1m` | Median 1-month return of stocks in same GICS sector |
| `sector_return_3m` | Median 3-month return of stocks in same GICS sector |
| `return_1m_vs_sector` | Stock's 1m return minus sector median |
| `return_6m_vs_sector` | Stock's 6m return minus sector median |
| `gross_margin_vs_sector` | Stock's gross margin / sector median (recent ~1.5yr) |
| `roe_vs_sector` | Stock's ROE / sector median (recent ~1.5yr) |
| `volatility_20d_vs_sector` | Stock's 20d vol / sector median (<1 = calmer than peers) |
| `sector_breadth` | Fraction of sector above SMA200 (0-1) |

### Fundamental (recent ~1.5 years, quarterly forward-filled)
Note: yfinance only provides ~6 quarters of history. These features have limited backtest coverage.

| Feature | Description |
|---------|-------------|
| `gross_margin` | Gross profit / revenue |
| `operating_margin` | Operating income / revenue |
| `net_margin` | Net income / revenue |
| `roa` | Return on assets (annualized) |
| `roe` | Return on equity (annualized) |
| `debt_to_equity` | Total debt / stockholders equity |
| `current_ratio` | Current assets / current liabilities |

### Stability (recent ~1.5 years, moat proxies — lower = more stable)
| Feature | Description |
|---------|-------------|
| `gross_margin_stability` | Std of gross margin over recent quarters |
| `operating_margin_stability` | Std of operating margin over recent quarters |
| `roe_stability` | Std of ROE over recent quarters |

### Percentile Ranks (cross-sectional, 0-1 scale)

Every feature above also has a `{feature}_pctrank` variant (e.g., `roe_pctrank`, `return_6m_pctrank`, `volatility_20d_pctrank`). Percentile ranks are computed cross-sectionally at each date — 0 = lowest among S&P 500, 1 = highest. Use these for relative thresholds that adapt over time instead of hardcoded absolute values.

Example: `{"feature": "roe_pctrank", "op": ">", "value": 0.8}` means "top 20% of ROE."

## The Loop

```
analyze.py computes stats from results.jsonl
(summary, features, thresholds, regime, stocks, overlap, correlation)
           ↓
LLM interprets stats → writes analysis.md
           ↓
Claude Code reads program.md + analysis.md + feature_stats.md
           ↓
Proposes ONE screen as structured JSON
           ↓
screen.py backtests: rebalance every holding_days over 2020-2025,
equal-weight top_n, per-stock returns tracked
           ↓
Result appended to results.jsonl
(stock details archived to data/details/)
           ↓
Sharpe >= 0.3 → KEEP, else DISCARD
           ↓
Repeat
```

### Stopping Conditions

The loop stops on whichever comes first:
- `-n` iterations reached
- `--hours` time limit elapsed
- `--patience` consecutive iterations with no new KEEP (default: 20)
- Ctrl+C (graceful shutdown after current iteration)

## Conventions

- All code must pass `ruff check` before commit
- Tests in `tests/` with `test_` prefix
- Secrets in `.env` (gitignored)
- Keep it simple — resist the urge to add abstractions
