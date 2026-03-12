# CLAUDE.md

## Project Purpose

AutoScreen: an autoresearch-style loop that autonomously discovers stock screens predicting 1-month forward returns on S&P 500.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — keep it dead simple. Claude Code CLI proposes a screen, the system backtests it, results get logged, repeat.

### History

- **v1** (`autonomou_evolving_investment`): Unbounded strategy space + custom infrastructure — failed
- **v2** (this repo, prior code): Over-engineered multi-stage pipeline with 133 alpha factors — most factors failed, combining them was meaningless
- **v3** (current): Start from scratch. One question: "which stocks will outperform?" Test screens in a tight loop.

## Key Principles

- **Simple loop**: propose screen → backtest → keep or discard → repeat
- **Free data only**: yfinance for price + quarterly fundamentals, cached as parquet
- **Claude Code CLI for reasoning**: `claude -p` proposes screens with full project context
- **No over-engineering**: 3 Python files + 1 config. No classes, no abstractions.
- **knowledge/ is READ-ONLY**: The 145-doc knowledge base is reference material
- **factors/ is READ-ONLY**: The 133 factor docs are reference material

## Technology Stack

- **Language**: Python 3.10+
- **Data**: yfinance + local Parquet cache
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

# Run tests
conda run -n data_science pytest tests/ -v

# Lint
conda run -n data_science ruff check data.py screen.py run.py
```

## Project Structure

```
data.py          # Download & cache S&P 500 price + fundamental data to parquet
screen.py        # Compute features, apply JSON screen DSL, backtest monthly, measure alpha vs SPY
run.py           # Orchestration loop: Claude Code proposes screen → evaluate → log → repeat
program.md       # LLM instructions + available features + past results log
results.jsonl    # Append-only machine-readable log of all screen evaluations
knowledge/       # 145 curated docs — READ-ONLY reference
factors/         # 133 alpha factor docs — READ-ONLY reference
data/            # Cached parquet files (gitignored)
tests/           # pytest tests
docs/plans/      # Implementation plans
```

## Screen DSL

The LLM proposes screens as JSON:

```json
{
  "name": "Revenue acceleration + uptrend",
  "hypothesis": "Stocks with accelerating revenue in an uptrend outperform",
  "filters": [
    {"feature": "revenue_growth_yoy", "op": ">", "value": 0.10},
    {"feature": "close_vs_sma200", "op": ">", "value": 1.0}
  ],
  "top_n": 20
}
```

Operators: `>`, `<`, `>=`, `<=`, `==`, `!=`, `between` (value = [lo, hi])

## Available Features

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

## The Loop

```
Claude Code analyzes results.jsonl using Python/pandas
(multi-turn: writes & runs scripts freely)
           ↓
Writes analysis.md with computed insights
           ↓
Claude Code reads program.md + analysis.md
           ↓
Proposes ONE screen as structured JSON
           ↓
screen.py backtests: apply monthly over 2020-2025,
equal-weight top_n, per-stock returns tracked
           ↓
Result appended to program.md + results.jsonl
           ↓
Sharpe >= 0.3 → KEEP, else DISCARD
           ↓
Repeat
```

## Conventions

- All code must pass `ruff check` before commit
- Tests in `tests/` with `test_` prefix
- Secrets in `.env` (gitignored)
- Keep it simple — resist the urge to add abstractions
