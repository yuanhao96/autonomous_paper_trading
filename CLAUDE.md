# CLAUDE.md

## Project Purpose

An autonomous trading agent that discovers, optimizes, and trades alpha factors. It uses 115 curated factor formulas (106 WorldQuant + 9 traditional) as a structured knowledge base, generates executable backtesting code via LLM, and deploys the best-performing factors to an Alpaca paper trading account.

This is the third attempt. Previous iterations failed due to:
1. **v1** (`autonomou_evolving_investment`): Unbounded strategy space + custom infrastructure
2. **v2** (this repo, prior code): Over-engineered multi-stage pipeline, too many abstractions before anything worked end-to-end

**v1.0** got the strategy-based pipeline working end-to-end. **v1.1** pivots to structured alpha factors with deterministic parsing, cached code, and train/test optimization.

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
python -m stratgen discover             # Factor docs → code → backtest → evaluate
python -m stratgen optimize             # Grid search params on train/test split
python -m stratgen signals              # Generate LONG/FLAT signals from top factors
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
factors/                    # 115 alpha factor docs — READ-ONLY
  momentum/                 #   34 factors
  volume_price/             #   25 factors
  mean_reversion/           #   15 factors
  volatility/               #   13 factors
  price_channel/            #   13 factors
  trend/                    #   12 factors
  composite/                #    3 factors
src/
  stratgen/
    __init__.py             # Version string
    __main__.py             # python -m stratgen entry point
    cli.py                  # Argparse CLI with subcommands
    paths.py                # PROJECT_ROOT, FACTORS_DIR, result file paths
    core.py                 # FactorSpec, llm_call, codegen, evaluate
    factor_discover.py      # Discovery loop: parse → codegen → backtest → evaluate
    factor_optimize.py      # Grid search optimization with train/test split
    factor_signals.py       # Signal generation from top optimized factors
    trade.py                # Alpaca paper trading: status
archive/                    # Historical files (v0–v6)
docs/                       # Version documentation
results_factors.json        # Discovery results (runtime artifact)
results_factors_opt.json    # Optimization results (runtime artifact)
tests/                      # All tests
```

## Pipeline

The pipeline stages build on each other:

| Stage | Command | What it does |
|-------|---------|-------------|
| **Discover** | `python -m stratgen discover` | Parse factor docs → LLM codegen → backtest on SPY 2020–2025 → evaluate → cache code |
| **Optimize** | `python -m stratgen optimize` | Grid search params on train (2020–2023), evaluate on test (2024+) — LLM-free |
| **Signals** | `python -m stratgen signals` | Run top factors on recent data → LONG/FLAT signals — LLM-free |
| **Status** | `python -m stratgen status` | Show Alpaca account balance and positions |

Only `discover` calls the LLM. Optimize and signals reuse cached code from `results_factors.json`.

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
```

### Common flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--provider {openai,anthropic}` | discover | LLM provider (default: openai) |
| `--reset` | discover, optimize | Ignore previous results, start fresh |
| `--max-tries N` | optimize | Grid search budget per factor (default: 200) |
| `--top-n N` | signals | Number of top factors to use (default: 5) |

## Conventions

- All code must pass `ruff check src/stratgen/` and `mypy src/stratgen/` before commit
- Tests in `tests/` with `test_` prefix
- Secrets in `.env` (gitignored), loaded via `python-dotenv`
- Keep modules small and focused — no god classes
- Prefer composition over inheritance
