# AutoScreen

Autonomous stock screening research loop for S&P 500. Claude Code CLI proposes screens, the system backtests them, results get logged, repeat.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch).

## How it works

1. `analyze.py` computes statistics from past results
2. Claude Code interprets the stats and writes a research memo (`analysis.md`)
3. Claude Code reads available features + research insights and proposes a screen
4. `screen.py` backtests the screen: rebalance every N trading days over 2020-2025, equal-weight portfolio, measure alpha vs SPY
5. Result logged to `results.jsonl` — Sharpe >= 0.3 is a KEEP, else DISCARD
6. Repeat

## Setup

```bash
# Install dependencies (conda)
conda activate data_science
pip install pandas pyarrow yfinance scipy

# Download & cache S&P 500 data (~15-20 min first time)
python data.py

# Re-download data (quarterly refresh)
python data.py --force
```

## Usage

```bash
# Run 10 iterations of autonomous screen research
python run.py -n 10

# Run overnight with time limit
python run.py --hours 8

# Stop after 30 iterations with no new KEEP
python run.py --patience 30

# Combine stopping conditions
python run.py -n 100 --hours 4 --patience 20
```

Ctrl+C for graceful shutdown after the current iteration.

## Analysis tools

```bash
# Full analysis report
python analyze.py

# Specific section (summary, top, feat, thresh, regime, stocks, overlap, corr, discard)
python analyze.py --section feat

# Deep-dive a specific screen by name
python analyze.py --screen "momentum"

# Compute per-feature predictive power (rank IC, quintile Sharpe, conditional IC)
python feature_stats.py
```

## Screen DSL

Screens are JSON objects with filters on computed features:

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

- **filters**: AND logic — stock must pass all filters
- **rank_by** / **rank_order**: rank survivors and pick the best `top_n`
- **holding_days**: rebalance frequency (10 = biweekly, 21 = monthly, 42 = bimonthly)
- **Operators**: `>`, `<`, `>=`, `<=`, `==`, `!=`, `between` (value = [lo, hi])

## Features

~40 raw features + percentile-rank variants for each.

| Category | Features | Coverage |
|----------|----------|----------|
| Price/momentum | return_1m/3m/6m/12m, close_vs_sma50/200, sma50_vs_sma200, high/low_52w_pct, drawdown | Full 2020-2025 |
| Volatility/volume | volatility_20d/60d, avg_volume_20d, volume_ratio | Full 2020-2025 |
| Sector-relative | sector_return_1m/3m, return vs sector, margin/roe vs sector, sector_breadth | Full 2020-2025 |
| Fundamental | gross/operating/net margin, roa, roe, debt_to_equity, current_ratio | Recent ~1.5yr |
| Stability | gross_margin/operating_margin/roe stability | Recent ~1.5yr |
| Percentile ranks | `{feature}_pctrank` for all above (cross-sectional, 0-1) | Same as base |

## Project structure

```
data.py            # Download & cache S&P 500 data to parquet
screen.py          # Feature computation + screen DSL backtesting engine
analyze.py         # Multi-section analysis of backtest results
feature_stats.py   # Per-feature predictive power (rank IC, quintile Sharpe)
run.py             # Orchestration loop: analyze → propose → backtest → log
program.md         # LLM prompt: available features + rules
feature_stats.md   # Generated per-feature stats for LLM context
analysis.md        # Generated research memo from past results
results.jsonl      # Append-only log of all screen evaluations
data/              # Cached parquet files + per-stock detail archives
knowledge/         # 145 curated reference docs (read-only)
factors/           # 133 alpha factor docs (read-only)
tests/             # pytest tests
```

## Development

```bash
# Run tests
pytest tests/ -v

# Lint
ruff check data.py screen.py run.py analyze.py feature_stats.py
```
