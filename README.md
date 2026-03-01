# stratgen

Autonomous alpha factor discovery, optimization, and signal generation for trading.

stratgen takes a curated set of 115 alpha factor formulas, uses an LLM to generate executable backtesting code for each, evaluates them against performance thresholds, optimizes parameters via grid search with out-of-sample validation, and generates trading signals from the winners.

## Quick Start

```bash
pip install -e .

# 1. Discover — parse factor docs, generate code, backtest, evaluate
python -m stratgen discover

# 2. Optimize — grid search params on train/test split
python -m stratgen optimize

# 3. Signals — generate LONG/FLAT from top factors
python -m stratgen signals

# 4. Status — Alpaca account info
python -m stratgen status
```

Requires Python 3.10+ and at least one LLM API key (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`) in a `.env` file.

## How It Works

```
Factor doc (.md)  →  Deterministic parse  →  LLM codegen  →  Backtest  →  Evaluate
                                                  ↓ (code cached)
                                             Optimize (grid search, train/test split)
                                                  ↓
                                             Signals (LONG / FLAT per factor)
```

- **115 alpha factors** across 7 categories (momentum, volume-price, mean reversion, volatility, price channel, trend, composite) sourced from Kakushadze (2015) "101 Formulaic Alphas"
- **Deterministic parsing** — factor docs follow a fixed markdown format, no LLM needed for spec extraction
- **Code caching** — LLM is only called in `discover`; optimize and signals reuse cached code
- **Train/test split** — optimize trains on 2020–2023, tests on 2024+ to guard against overfitting
- **backtesting.py** engine with SPY daily OHLCV data from yfinance

## Pipeline

| Stage | Command | LLM? | What it does |
|-------|---------|------|-------------|
| Discover | `python -m stratgen discover` | Yes | Parse 115 factor docs → LLM codegen → backtest → evaluate |
| Optimize | `python -m stratgen optimize` | No | Grid search params on train set, evaluate on held-out test set |
| Signals | `python -m stratgen signals` | No | Run top factors on recent data → LONG/FLAT signals |
| Status | `python -m stratgen status` | No | Show Alpaca account balance and positions |

## Configuration

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...          # Required for discover
ANTHROPIC_API_KEY=sk-ant-...   # Alternative LLM provider
ALPACA_API_KEY=PK...           # Required for status
ALPACA_SECRET_KEY=...
```

## Project Structure

```
factors/                    # 115 alpha factor docs (read-only)
knowledge/                  # 145 curated trading knowledge docs (read-only)
src/stratgen/               # Main package
  cli.py                    #   CLI entry point
  core.py                   #   FactorSpec, LLM calls, codegen, evaluate
  factor_discover.py        #   Discovery loop
  factor_optimize.py        #   Grid search optimization
  factor_signals.py         #   Signal generation
  trade.py                  #   Alpaca integration
  paths.py                  #   Path constants
results_factors.json        # Discovery results (runtime)
results_factors_opt.json    # Optimization results (runtime)
docs/                       # Detailed documentation
```

## Documentation

- [v1.1 Documentation](docs/v1.1.md) — full architecture, data formats, design decisions
- [v1.0 Documentation](docs/v1.0.md) — previous strategy-based pipeline

## License

Private project.
