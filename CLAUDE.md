# CLAUDE.md

## Project Purpose

An autonomous trading agent that discovers, scores, and trades alpha factors on a screened S&P 500 universe. It uses 133 curated factor formulas (124 WorldQuant + 9 traditional) as a structured knowledge base, generates executable code via LLM, scores individual stocks using IC-weighted factor combination, and deploys portfolio allocations to an Alpaca paper trading account.

This is the third attempt. Previous iterations failed due to:
1. **v1** (`autonomou_evolving_investment`): Unbounded strategy space + custom infrastructure
2. **v2** (this repo, prior code): Over-engineered multi-stage pipeline, too many abstractions before anything worked end-to-end

**v1.x** built the factor discovery and evaluation infrastructure: deterministic parsing, LLM codegen, time-series backtesting, cross-sectional analysis, and parameter optimization. Key finding: XS factors underperformed on S&P 100 (17/18 FAIL) — the universe was too small and correlated for rank-based alphas.

**v2.x** pivots to a screen → score → allocate pipeline on S&P 500. Instead of evaluating factors in isolation, it applies all 115 time-series factors per-stock, combines them via IC-weighted z-scores into a composite alpha, and constructs a risk-managed portfolio.

## Key Principles

- **Knowledge-constrained**: The LLM translates documented factor formulas into backtesting code. It does NOT invent arbitrary indicator combinations.
- **Deterministic parsing**: Factor docs follow a fixed markdown format. Spec extraction is regex-based, not LLM-based.
- **Code caching**: LLM is only called in `discover`. Optimize and signals reuse cached code from results.
- **Train/test split**: Optimize uses 2020–2023 for training and 2024+ for held-out testing to guard against overfitting.
- **Existing tools over custom code**: Use established libraries (backtesting.py, pandas, yfinance) instead of building custom infrastructure.
- **knowledge/ is READ-ONLY**: The 145-doc knowledge base is the foundation. Do not modify, auto-grow, or regenerate it.
- **factors/ is READ-ONLY**: The 115 factor docs are curated. Do not auto-generate or modify them.

## Technology Stack

- **Language**: Python 3.10+
- **Backtesting**: backtesting.py
- **Data**: yfinance (+ local Parquet cache when needed)
- **LLM**: Claude API (Anthropic) / OpenAI
- **Broker**: Alpaca (paper trading first, then live)
- **Testing**: pytest
- **Linting**: ruff (line-length 100) + mypy

## Commands

```bash
pip install -e .                         # Install package (editable)
pip install -e ".[dev]"                  # Install with dev tools

# v1.x — Factor discovery & evaluation
python -m stratgen discover             # Factor docs → code → backtest → evaluate
python -m stratgen optimize             # Grid search params on train/test split
python -m stratgen signals              # Generate LONG/FLAT signals from top factors
python -m stratgen analyze              # Cross-sectional factor analysis (SP100 default)
python -m stratgen optimize-xs          # Grid search XS factor params (score by |IC|)

# v2.x — Screen → Score → Allocate
python -m stratgen screen               # Filter S&P 500 by liquidity/price/data quality
python -m stratgen score                # Compute IC-weighted composite alpha per stock
python -m stratgen validate             # Quintile analysis + multi-horizon IC validation
python -m stratgen allocate             # Generate portfolio weights with risk constraints (planned)

# Utilities
python -m stratgen status               # Show Alpaca account + positions
ruff check src/stratgen/                # Lint
mypy src/stratgen/                      # Type check
pytest tests/ -v                        # Run tests
```

## Project Structure

```
pyproject.toml              # Package metadata, ruff/mypy config
knowledge/                  # 145 curated docs — READ-ONLY
  strategies/               #   83 strategy templates + alpha factor reference
  financial-python/         #   14 financial Python guides
  key-concepts/             #   15 general trading concepts
  trading-concepts/         #   33 trading agent modeling concepts
factors/                    # 133 alpha factor docs — READ-ONLY
  momentum/                 #   34 factors
  volume_price/             #   25 factors
  mean_reversion/           #   15 factors
  volatility/               #   13 factors
  price_channel/            #   13 factors
  trend/                    #   12 factors
  composite/                #    3 factors
  cross_sectional/          #   18 cross-sectional (rank-based) factors
src/
  stratgen/
    __init__.py             # Version string
    __main__.py             # python -m stratgen entry point
    cli.py                  # Argparse CLI with subcommands
    paths.py                # PROJECT_ROOT, FACTORS_DIR, result file paths
    core.py                 # FactorSpec, llm_call, codegen (time-series + XS), evaluate
    universe.py             # Universe management: SP100/sector ETFs, download, cache, panels
    cross_section.py        # Cross-sectional: ranking, portfolios, IC, monotonicity
    factor_discover.py      # Discovery loop: parse → codegen → backtest → evaluate
    factor_optimize.py      # Grid search optimization with train/test split
    factor_signals.py       # Signal generation from top optimized factors
    factor_analyze.py       # Cross-sectional analysis loop with resume support
    factor_optimize_xs.py   # XS grid search optimization (score by |IC|, train/test)
    screener.py             # Stock screener: liquidity, price, data quality filters
    scorer.py               # Alpha scoring: factor extraction, z-score, rolling IC, composite
    validator.py            # Validation: quintile analysis, composite IC, multi-horizon
    factor_screen.py        # Screen command runner
    factor_score.py         # Score command runner
    factor_validate.py      # Validate command runner
    trade.py                # Alpaca paper trading: status
archive/                    # Historical files (v0–v6)
docs/                       # Version documentation
data/                       # Cached universe data (Parquet, gitignored)
results_factors.json        # Discovery results (runtime artifact)
results_factors_opt.json    # Optimization results (runtime artifact)
results_factors_xs.json     # Cross-sectional analysis results (runtime artifact)
results_factors_xs_opt.json # XS optimization results (runtime artifact)
results_screen.json         # Screen results (runtime artifact)
results_score.json          # Score results (runtime artifact)
results_validate.json       # Validation results (runtime artifact)
tests/                      # All tests
```

## Pipeline

### v1.x pipeline (factor discovery & evaluation)

| Stage | Command | LLM? | What it does |
|-------|---------|------|-------------|
| **Discover** | `stratgen discover` | Yes | Parse factor docs → LLM codegen → backtest on SPY → evaluate → cache code |
| **Optimize** | `stratgen optimize` | No | Grid search params on train (2020–2023), evaluate on test (2024+) |
| **Signals** | `stratgen signals` | No | Run top factors on recent data → LONG/FLAT signals |
| **Analyze** | `stratgen analyze` | Yes | XS factor analysis on SP100 — rank, quintiles, IC |
| **Optimize-XS** | `stratgen optimize-xs` | No | Grid search XS factor params, score by |IC| |

### v2.x pipeline (screen → score → allocate)

```
S&P 500 → Screen (liquidity/price/data) → ~300 stocks
                                              ↓
                              Run 115 TS factors per stock
                                              ↓
                              Z-score each factor cross-sectionally
                                              ↓
                              IC-weighted combination → composite alpha
                                              ↓
                              Rank → Validate (IC, quintile spread)
                                              ↓
                              Portfolio optimizer (risk constraints, turnover)
                                              ↓
                              Alpaca paper trading
```

| Stage | Command | LLM? | What it does |
|-------|---------|------|-------------|
| **Screen** | `stratgen screen` | No | Filter S&P 500 by ADV, price, data completeness → ~300 stocks |
| **Score** | `stratgen score` | No | Compute all TS factors per stock, IC-weighted z-score combination |
| **Validate** | `stratgen validate` | No | Quintile analysis, composite IC, multi-horizon IC, verdict |
| **Allocate** | `stratgen allocate` | No | *(planned)* Portfolio weights with sector/position limits, turnover penalty |
| **Status** | `stratgen status` | No | Alpaca account balance and positions |

The v2.x pipeline is LLM-free at runtime — it reuses cached factor code from v1.x discovery.

### FactorSpec

```python
@dataclass
class FactorSpec:
    name: str                    # "WQ-002: Negative 2-day log return"
    formula: str                 # "-1 * delta(log(close), 2)"
    interpretation: str          # "Contrarian short-term reversal"
    params: dict                 # {"lookback": 2}
    param_ranges: dict           # {"lookback": [1, 4]}
    category: str                # "momentum"
    source: str                  # "WorldQuant Alpha#002"
    factor_ref: str              # "factors/momentum/wq_002.md"
    factor_type: str             # "time_series" or "cross_sectional"
```

### Common flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--provider {openai,anthropic}` | discover, analyze | LLM provider (default: openai) |
| `--reset` | discover, optimize, analyze, optimize-xs | Ignore previous results, start fresh |
| `--max-tries N` | optimize, optimize-xs | Grid search budget per factor (default: 200) |
| `--top-n N` | signals, score | Number of top factors to use (default: 5 / all) |
| `--ic-window N` | score, validate | Rolling IC window in trading days (default: 60) |
| `--min-verdict {PASS,MARGINAL}` | score, validate | Minimum factor verdict to include (default: MARGINAL) |
| `--weight-method` | score, validate | Factor weighting: global_sign, global_ic, sign, icir, ic (default: global_sign) |
| `--min-ic FLOAT` | score, validate | Min \|mean IC\| to include factor (default: 0.01) |
| `--n-groups N` | analyze, optimize-xs, validate | Number of portfolio groups (default: 5 = quintiles) |
| `--horizons` | validate | Forward return horizons, comma-separated (default: 1,5,10,20) |
| `--universe {sp100,sector-etfs}` | analyze, optimize-xs | Stock universe (default: sp100) |
| `--train-end` / `--test-start` | optimize-xs | Train/test split dates (default: 2022-12-31 / 2023-01-01) |

## Conventions

- All code must pass `ruff check src/stratgen/` and `mypy src/stratgen/` before commit
- Tests in `tests/` with `test_` prefix
- Secrets in `.env` (gitignored), loaded via `python-dotenv`
- Keep modules small and focused — no god classes
- Prefer composition over inheritance
