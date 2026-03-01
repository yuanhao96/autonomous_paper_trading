# stratgen

Autonomous alpha factor discovery, optimization, and cross-sectional analysis for trading.

stratgen takes a curated set of 133 alpha factor formulas (115 time-series + 18 cross-sectional), uses an LLM to generate executable code for each, evaluates them against performance thresholds, optimizes parameters via grid search with out-of-sample validation, and generates trading signals from the winners.

## Quick Start

```bash
pip install -e .

# 1. Discover — parse factor docs, generate code, backtest, evaluate
python -m stratgen discover

# 2. Optimize — grid search params on train/test split
python -m stratgen optimize

# 3. Signals — generate LONG/FLAT from top factors
python -m stratgen signals

# 4. Analyze — cross-sectional factor analysis on sector ETFs
python -m stratgen analyze

# 5. Status — Alpaca account info
python -m stratgen status
```

Requires Python 3.10+ and at least one LLM API key (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`) in a `.env` file.

## How It Works

### Time-series pipeline (single-ticker backtesting)

```
Factor doc (.md)  →  Deterministic parse  →  LLM codegen  →  Backtest  →  Evaluate
                                                  ↓ (code cached)
                                             Optimize (grid search, train/test split)
                                                  ↓
                                             Signals (LONG / FLAT per factor)
```

### Cross-sectional pipeline (multi-ticker ranking)

```
Factor doc (.md)  →  Deterministic parse  →  LLM codegen  →  Compute alpha panel
                                                  ↓ (code cached)
                                             Rank across tickers  →  Form terciles
                                                  ↓
                                             IC, monotonicity, long-short spread
```

## Factor Knowledge Base

- **115 time-series factors** across 7 categories (momentum, volume-price, mean reversion, volatility, price channel, trend, composite) — backtested on SPY
- **18 cross-sectional factors** using `rank()` for cross-sectional ranking — evaluated on 11 sector ETFs (XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY)
- Sourced from Kakushadze (2015) "101 Formulaic Alphas" + 9 traditional strategy factors
- **Deterministic parsing** — factor docs follow a fixed markdown format, no LLM needed for spec extraction
- **Code caching** — LLM is only called in `discover` and `analyze`; optimize and signals reuse cached code

## Pipeline

| Stage | Command | LLM? | What it does |
|-------|---------|------|-------------|
| Discover | `python -m stratgen discover` | Yes | Parse 115 factor docs → LLM codegen → backtest on SPY → evaluate |
| Optimize | `python -m stratgen optimize` | No | Grid search params on train set (2020–2023), evaluate on test (2024+) |
| Signals | `python -m stratgen signals` | No | Run top factors on recent data → LONG/FLAT signals |
| Analyze | `python -m stratgen analyze` | Yes | Parse 18 XS factor docs → LLM codegen → rank across 11 ETFs → IC/mono |
| Status | `python -m stratgen status` | No | Show Alpaca account balance and positions |

## Configuration

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...          # Required for discover/analyze
ANTHROPIC_API_KEY=sk-ant-...   # Alternative LLM provider
ALPACA_API_KEY=PK...           # Required for status
ALPACA_SECRET_KEY=...
```

## Project Structure

```
factors/                    # 133 alpha factor docs (read-only)
  momentum/                 #   34 time-series factors
  volume_price/             #   25 time-series factors
  mean_reversion/           #   15 time-series factors
  volatility/               #   13 time-series factors
  price_channel/            #   13 time-series factors
  trend/                    #   12 time-series factors
  composite/                #    3 time-series factors
  cross_sectional/          #   18 cross-sectional (rank-based) factors
knowledge/                  # 145 curated trading knowledge docs (read-only)
src/stratgen/               # Main package
  cli.py                    #   CLI entry point
  core.py                   #   FactorSpec, LLM calls, TS + XS codegen, evaluate
  universe.py               #   Sector ETF download, Parquet cache, build panels
  cross_section.py          #   Ranking, portfolios, IC, monotonicity, XS evaluation
  factor_discover.py        #   Time-series discovery loop
  factor_optimize.py        #   Grid search optimization
  factor_signals.py         #   Signal generation
  factor_analyze.py         #   Cross-sectional analysis loop
  trade.py                  #   Alpaca integration
  paths.py                  #   Path constants
data/                       # Cached universe data (Parquet, gitignored)
results_factors.json        # Discovery results (runtime)
results_factors_opt.json    # Optimization results (runtime)
results_factors_xs.json     # Cross-sectional analysis results (runtime)
docs/                       # Detailed documentation
```

## Documentation

- [v1.2 Documentation](docs/v1.2.md) — cross-sectional analysis, evaluation metrics, design decisions
- [v1.1 Documentation](docs/v1.1.md) — time-series factor pipeline architecture
- [v1.0 Documentation](docs/v1.0.md) — previous strategy-based pipeline

## License

Private project.
