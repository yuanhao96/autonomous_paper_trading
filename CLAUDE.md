# CLAUDE.md

## Project Purpose

An autonomous trading agent that generates, screens, and evolves trading strategies. It draws from a curated knowledge base of 145 documents (83 strategies, 14 financial Python guides, 15 key concepts, 33 trading agent concepts) to constrain the strategy space to well-documented, academically grounded approaches.

This is the third attempt. Previous iterations failed due to:
1. **v1** (`autonomou_evolving_investment`): Unbounded strategy space + custom infrastructure
2. **v2** (this repo, prior code): Over-engineered multi-stage pipeline, too many abstractions before anything worked end-to-end

**This time**: Get a single strategy running end-to-end first, then generalize.

## Key Principles

- **Knowledge-constrained**: The LLM selects from documented strategy templates and tunes parameters within documented bounds. It does NOT invent arbitrary indicator combinations.
- **End-to-end first**: A single working pipeline (generate → backtest → evaluate) before adding complexity.
- **Existing tools over custom code**: Use established libraries (backtesting.py, pandas, yfinance) instead of building custom infrastructure.
- **knowledge/ is READ-ONLY**: The 145-doc knowledge base is the foundation. Do not modify, auto-grow, or regenerate it.

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
python -m stratgen discover             # Discover + backtest all strategy docs
python -m stratgen optimize             # Optimize params for passing strategies
python -m stratgen signals              # Generate trading signals (no orders)
python -m stratgen run                  # Generate signals + submit Alpaca orders
python -m stratgen status               # Show Alpaca account + positions
ruff check src/stratgen/                # Lint
mypy src/stratgen/                      # Type check
pytest tests/ -v                        # Run tests
```

## Project Structure

```
pyproject.toml          # Package metadata, ruff/mypy config
knowledge/              # 145 curated docs — READ-ONLY
  strategies/           #   83 strategy templates across 10 categories
  financial-python/     #   14 financial Python guides
  key-concepts/         #   15 general trading concepts
  trading-concepts/     #   33 trading agent modeling concepts
src/
  stratgen/
    __init__.py         # Version string
    __main__.py         # python -m stratgen entry point
    cli.py              # Argparse CLI with subcommands
    paths.py            # PROJECT_ROOT, KNOWLEDGE_DIR, result file paths
    core.py             # StrategySpec, llm_call, codegen, evaluate
    spec.py             # Knowledge doc → StrategySpec extraction
    backtest.py         # run_backtest, run_one, print_summary
    discover.py         # Discovery loop over all strategy docs
    optimize.py         # Parameter optimization via grid search
    trade.py            # Alpaca paper trading: signals, orders, status
archive/                # Historical files (v0.py, v1.py)
results_v4.json         # Discovery results (runtime artifact)
results_v5.json         # Optimization results (runtime artifact)
runs_v6.json            # Trading run logs (runtime artifact)
tests/                  # All tests
```

## Pipeline

The pipeline stages build on each other:

| Stage | Command | What it does |
|-------|---------|-------------|
| **Discover** | `python -m stratgen discover` | All strategy docs → spec → code → backtest → evaluate → rank |
| **Optimize** | `python -m stratgen optimize` | Tune params for PASS/MARGINAL strategies via grid search |
| **Signals** | `python -m stratgen signals` | Generate LONG/FLAT signals from top strategies |
| **Run** | `python -m stratgen run` | Signals → reconcile Alpaca positions → submit orders |
| **Status** | `python -m stratgen status` | Show Alpaca account balance and positions |

All LLM subcommands accept `--provider {openai,anthropic}` (default: openai).
Discovery and optimization support `--reset` to start fresh and auto-resume by default.

### StrategySpec

```python
@dataclass
class StrategySpec:
    name: str                    # "SMA Crossover"
    knowledge_ref: str           # "knowledge/strategies/momentum/sma-crossover.md"
    universe: list[str]          # ["SPY"]
    timeframe: str               # "1d"
    entry_signal: str            # "SMA(20) crosses above SMA(50)"
    exit_signal: str             # "SMA(20) crosses below SMA(50)"
    stop_loss_pct: float         # 0.02
    position_size_pct: float     # 0.95
    params: dict                 # {"fast_period": 20, "slow_period": 50}
```

## Conventions

- All code must pass `ruff check src/stratgen/` and `mypy src/stratgen/` before commit
- Tests in `tests/` with `test_` prefix
- Secrets in `.env` (gitignored), loaded via `python-dotenv`
- Keep modules small and focused — no god classes
- Prefer composition over inheritance
