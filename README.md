# AutoScreen

An autonomous stock screening research system that uses Claude Code CLI to discover factor-based screens predicting forward returns on S&P 500. Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch).

The system proposes a screen, backtests it, logs the result, and repeats — learning from past successes and failures to propose better screens over time.

## How it works

```
                    ┌──────────────────────┐
                    │  compute_all_features │
                    │  price, fundamental,  │
                    │  sector, stability,   │
                    │  pctrank, regime      │
                    └──────────┬───────────┘
                               │ (computed once, cached in memory)
                               ▼
              ┌──────── ITERATION LOOP ────────┐
              │                                │
              │  1. analyze.py                 │
              │     compute stats from         │
              │     results.jsonl              │
              │              │                 │
              │              ▼                 │
              │  2. claude -p (LLM #1)         │
              │     interpret stats            │
              │     → write analysis.md        │
              │              │                 │
              │              ▼                 │
              │  3. claude -p (LLM #2)         │
              │     read program.md            │
              │     read analysis.md           │
              │     read feature_stats.md      │
              │     → propose ONE screen JSON  │
              │              │                 │
              │              ▼                 │
              │  4. apply_screen()             │
              │     backtest 2020-2025         │
              │     split IS / OOS metrics     │
              │     tag per-regime stats       │
              │              │                 │
              │              ▼                 │
              │  5. append to results.jsonl    │
              │     OOS Sharpe >= 0.3 → KEEP   │
              │     else → DISCARD             │
              │              │                 │
              │              ▼                 │
              │  6. stopping condition met?    │
              │     no → back to step 1        │
              └────────────────────────────────┘
```

Each iteration makes two LLM calls:
1. **Analysis agent** reads computed stats and writes a research memo (`analysis.md`)
2. **Proposal agent** reads the memo, feature docs, and past results, then proposes one new screen as structured JSON

The backtest engine rebalances every N trading days, builds an equal-weight portfolio of the top-ranked stocks passing all filters, and measures alpha vs SPY.

## Quick start

```bash
# Prerequisites: conda environment with pandas, numpy, scipy, yfinance
conda activate data_science

# 1. Download S&P 500 data (~15-20 min first time)
python data.py

# 2. Run 10 iterations of autonomous research
python run.py -n 10

# 3. Run with out-of-sample discipline (recommended)
python run.py -n 10 --split-date 2023-07-01

# 4. Analyze results
python analyze.py --section all

# 5. Run top screens on today's market
python run.py --screen
```

## Screen DSL

The LLM proposes screens as JSON objects:

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

Filters use AND logic. Operators: `>`, `<`, `>=`, `<=`, `==`, `!=`, `between`.

Multi-factor composite ranking via `score` + `rank_by: "_score"`:

```json
{
  "score": [
    {"feature": "return_6m_pctrank", "weight": 0.4},
    {"feature": "roe_pctrank", "weight": 0.3},
    {"feature": "volatility_20d_pctrank", "weight": -0.3}
  ],
  "rank_by": "_score",
  "rank_order": "desc"
}
```

## Features

32 features computed from price and fundamental data, plus cross-sectional percentile rank variants for each.

| Category | Features | Coverage |
|----------|----------|----------|
| Price-derived | returns (1/3/6/12m), MA ratios, volatility, drawdown, volume | Full 2020-2025 |
| Sector-relative | sector momentum, relative margins/ROE, sector breadth | Full 2020-2025 |
| Fundamental | margins, ROA, ROE, debt/equity, current ratio | Recent ~1.5 years |
| Stability | margin and ROE consistency (std over quarters) | Recent ~1.5 years |
| Percentile ranks | `{feature}_pctrank` (0-1 scale) for all above | Matches underlying |
| Market regime | `market_regime` (quiet_bull, volatile_bull, quiet_bear, volatile_bear) | Full 2020-2025 |

## Out-of-sample discipline

Running with `--split-date` splits the backtest into in-sample and out-of-sample periods:

```bash
python run.py -n 10 --split-date 2023-07-01
```

- The LLM sees only IS-period statistics
- The keep/discard verdict uses OOS Sharpe
- IS/OOS Sharpe ratio > 3 is flagged as likely overfit
- Prevents the optimization loop from overfitting to the full backtest window

## Market regime awareness

Each trading day is classified into one of 4 regimes based on SPY:

| | Low Volatility | High Volatility |
|---|---|---|
| **Uptrend** (close > SMA200) | quiet_bull | volatile_bull |
| **Downtrend** (close < SMA200) | quiet_bear | volatile_bear |

Per-regime alpha stats and robustness scores are computed for each screen. A robustness score of 1.0 means the screen generates positive alpha in all observed regimes.

## Verdict system

Screens receive a three-way verdict:

| Verdict | Condition |
|---------|-----------|
| **KEEP** | OOS Sharpe >= 0.3 and trailing-12m Sharpe >= 0 |
| **STALE** | Full Sharpe >= 0.3 but trailing-12m Sharpe < 0 (edge decayed) |
| **DISCARD** | Sharpe < 0.3 |

## Analysis

`analyze.py` produces 12 sections of analysis:

```bash
python analyze.py --section summary    # KEEP/STALE/DISCARD counts
python analyze.py --section top        # best/worst screens by Sharpe
python analyze.py --section recent     # trailing metrics, decay detection
python analyze.py --section risk       # drawdown, losing streaks, stability
python analyze.py --section feat       # feature usage, recent hit rate, trend
python analyze.py --section thresh     # threshold values used in KEEP screens
python analyze.py --section regime     # per-regime performance breakdown
python analyze.py --section oos        # IS vs OOS comparison, overfit warnings
python analyze.py --section stocks     # stock-level alpha contributors
python analyze.py --section overlap    # portfolio overlap between screens
python analyze.py --section corr       # alpha correlation between screens
python analyze.py --section discard    # why recent screens failed
python analyze.py --section all        # everything
python analyze.py --screen "name"      # deep-dive a single screen
```

## Stopping conditions

The loop stops on whichever comes first:

- `-n` iterations reached
- `--hours` time limit elapsed
- `--patience` consecutive iterations with no new KEEP (default: 20)
- Ctrl+C (graceful shutdown after current iteration)

## Project structure

```
data.py            # Download & cache S&P 500 data to parquet
screen.py          # Feature computation, screen DSL, backtesting
analyze.py         # Multi-section analysis of results.jsonl
feature_stats.py   # Per-feature predictive power (rank IC, quintile Sharpe)
run.py             # Orchestration loop + screen mode
screen_report.py   # Run top screens on today's market, generate reports
program.md         # LLM context: features, rules, examples
results.jsonl      # Append-only log of all screen evaluations
data/              # Cached parquet files (gitignored)
data/details/      # Per-stock monthly returns (one JSON per screen)
reports/           # Screen mode reports (gitignored)
knowledge/         # 145 curated reference docs (read-only)
factors/           # 133 alpha factor docs (read-only)
tests/             # pytest tests
```

## Development

```bash
# Run tests
pytest tests/ -v

# Lint
ruff check data.py screen.py run.py analyze.py feature_stats.py screen_report.py
```

## Technology

- Python 3.10+, pandas, numpy, scipy
- yfinance for free price and fundamental data
- Claude Code CLI (`claude -p`) for LLM reasoning
- No external APIs, no paid data sources
