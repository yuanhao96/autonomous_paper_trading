# stratgen

Autonomous alpha factor discovery, scoring, and trading on a screened S&P 500 universe.

stratgen uses a two-phase workflow:

1. **v1.x — Factor Discovery**: Take 133 curated alpha factor formulas, use an LLM to generate executable code, backtest on SPY, and optimize parameters via grid search with out-of-sample validation.
2. **v2.x — Stock Scoring & Trading**: Screen the S&P 500 by liquidity/data quality, run all optimized factors per-stock, combine via IC-weighted z-scores into a composite alpha, and (planned) construct a risk-managed portfolio for paper trading.

The v2.x pipeline is **LLM-free at runtime** — it reuses cached factor code from v1.x discovery.

## Quick Start

```bash
pip install -e .

# --- v1.x: Factor Discovery & Tuning ---
python -m stratgen discover             # Parse factor docs → LLM codegen → backtest → evaluate
python -m stratgen optimize             # Grid search params on train/test split

# --- v2.x: Screen → Score → Allocate ---
python -m stratgen screen               # Filter S&P 500 by liquidity, price, data quality
python -m stratgen score                # IC-weighted composite alpha per stock

# --- Other ---
python -m stratgen signals              # LONG/FLAT signals from top factors (v1.x)
python -m stratgen analyze              # Cross-sectional factor analysis on S&P 100 (v1.x)
python -m stratgen optimize-xs          # XS factor param optimization (v1.x)
python -m stratgen status               # Alpaca account info
```

Requires Python 3.10+ and at least one LLM API key (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`) in a `.env` file.

## How It Works

### End-to-end workflow

```
v1.x: Factor Discovery                    v2.x: Stock Scoring
─────────────────────                      ────────────────────
Factor docs (133)                          S&P 500 (~503 tickers)
      ↓ LLM codegen                             ↓
Backtest on SPY → Evaluate               Screen (liquidity/price/data)
      ↓                                         ↓ ~478 passing
Optimize (grid search)                    Run 48 optimized TS factors per stock
      ↓                                         ↓
results_factors_opt.json ──────────────→  Z-score cross-sectionally
  (48 PASS/MARGINAL,                            ↓
   cached code + params)                  IC-weighted combination
                                                ↓
                                          Composite alpha → Rank stocks
                                                ↓ (planned)
                                          Portfolio optimizer → Alpaca
```

## Factor Knowledge Base

- **115 time-series factors** across 7 categories (momentum, volume-price, mean reversion, volatility, price channel, trend, composite) — backtested on SPY
- **18 cross-sectional factors** using `rank()` for cross-sectional ranking — evaluated on S&P 100 (~101 stocks, quintiles ~20 per group)
- Sourced from Kakushadze (2015) "101 Formulaic Alphas" + 9 traditional strategy factors
- **Deterministic parsing** — factor docs follow a fixed markdown format, no LLM needed for spec extraction
- **Code caching** — LLM is only called in `discover` and `analyze`; optimize and signals reuse cached code

## Pipeline

### v1.x — Factor Discovery & Evaluation

| Stage | Command | LLM? | What it does |
|-------|---------|------|-------------|
| Discover | `stratgen discover` | Yes | Parse 115 factor docs → LLM codegen → backtest on SPY → evaluate |
| Optimize | `stratgen optimize` | No | Grid search params on train set (2020–2023), evaluate on test (2024+) |
| Signals | `stratgen signals` | No | Run top factors on recent data → LONG/FLAT signals |
| Analyze | `stratgen analyze` | Yes | Parse 18 XS factor docs → LLM codegen → rank across S&P 100 → IC/mono |
| Optimize-XS | `stratgen optimize-xs` | No | Grid search XS factor params, score by |IC| on train (2019–2022) |

### v2.x — Screen → Score → Allocate

| Stage | Command | LLM? | What it does |
|-------|---------|------|-------------|
| Screen | `stratgen screen` | No | Filter S&P 500 by ADV, price, data completeness → ~478 stocks |
| Score | `stratgen score` | No | Run optimized TS factors per stock, IC-weighted z-score → composite alpha |
| Allocate | `stratgen allocate` | No | *(planned)* Portfolio weights with sector/position limits, turnover penalty |
| Status | `stratgen status` | No | Alpaca account balance and positions |

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
  universe.py               #   Universe management: SP100/SP500/sector ETFs, download, cache
  cross_section.py          #   Ranking, portfolios, IC, monotonicity, XS evaluation
  screener.py               #   Stock screener: liquidity, price, data quality filters
  scorer.py                 #   Alpha scoring: extract values, z-score, rolling IC, composite
  factor_discover.py        #   Time-series discovery loop
  factor_optimize.py        #   Grid search optimization
  factor_signals.py         #   Signal generation
  factor_analyze.py         #   Cross-sectional analysis loop
  factor_optimize_xs.py     #   XS grid search optimization (score by |IC|)
  factor_screen.py          #   Screen command runner
  factor_score.py           #   Score command runner
  trade.py                  #   Alpaca integration
  paths.py                  #   Path constants
data/                       # Cached universe data (Parquet, gitignored)
results_factors.json        # Discovery results (runtime)
results_factors_opt.json    # Optimization results (runtime)
results_factors_xs.json     # Cross-sectional analysis results (runtime)
results_factors_xs_opt.json # XS optimization results (runtime)
results_screen.json         # Screen results (runtime)
results_score.json          # Score results (runtime)
docs/                       # Detailed documentation
```

## Roadmap

### v1.x — Factor Discovery & Cross-Sectional Analysis (done)

- v1.0: Strategy-based pipeline (end-to-end working)
- v1.1: Structured alpha factors with deterministic parsing, cached code, train/test optimization
- v1.2: Cross-sectional factor analysis on sector ETFs
- v1.3: S&P 100 universe, `optimize-xs` command, quintile support

**Lessons learned:** Cross-sectional factors underperformed on S&P 100 (17/18 FAIL, 1 MARGINAL). WorldQuant-style short-horizon XS alphas need 500+ stocks for meaningful cross-sectional dispersion. The 100 large-cap stocks are too correlated.

### v2.0 — S&P 500 Universe + Stock Screener (done)

- S&P 500 ticker list (~503 stocks) with survivorship bias caveat
- Quantitative screener: liquidity (ADV > $5M), price floor ($10+), data completeness (>95%), history (>2yr)
- Efficient batch download with Parquet cache
- `screen` command: filters ~503 tickers to ~478 passing stocks

### v2.1 — Single-Stock Alpha Factor Scoring (done)

- Mock Strategy extraction: run cached factor code per-stock without full backtests
- Cross-sectional z-scoring: normalize factor values across stocks at each date
- Rolling IC computation: Spearman rank correlation of factors vs forward returns
- IC-weighted combination: weight factors by trailing 60-day IC, sign-adjusted
- Composite alpha score per stock per day
- `score` command: computes and ranks stocks by composite alpha

### v2.2 — Cross-Sectional Validation

Validate that the composite scoring actually predicts forward returns on the larger universe.

- Rank stocks by composite alpha → form quintiles on the 500-stock universe
- Measure IC, monotonicity, long-short spread on out-of-sample data
- Per-category IC analysis: which factor categories contribute most?
- Factor decay analysis: how quickly does alpha decay over 1/5/10/20 day horizons?

### v2.3 — Portfolio Construction

Convert alpha scores into tradeable portfolio weights with risk controls.

- Long-only portfolio: top N stocks weighted by alpha score
- Risk constraints: max position size, sector concentration limits
- Turnover penalty: penalize excessive rebalancing
- Transaction cost model: estimate slippage and commissions
- `allocate` command: Generate target weights from composite alpha

### v2.4 — Live Paper Trading Loop

- Wire allocation output to Alpaca paper trading via `trade.py`
- Scheduled daily runs (cron/scheduler)
- Order execution: submit Alpaca orders from allocation
- Performance tracking: log fills, P&L, slippage vs backtest
- Alerting on signal changes and drawdown breaches

### Longer Term

- Long-short portfolio construction (requires margin account)
- Sector-neutral portfolio variants
- ML meta-model (XGBoost/Ridge) using factor z-scores as features
- Alternative data (sentiment, fundamentals, options flow)
- Intraday data for VWAP-dependent factors
- Multi-asset expansion (crypto, futures, international ETFs)

## Documentation

- [v2.1 Design](docs/v2.1.md) — Single-stock alpha factor scoring, IC-weighted composite
- [v2.0 Design](docs/v2.0.md) — S&P 500 universe, stock screener, revised pipeline
- [v1.3 Documentation](docs/v1.3.md) — expanded universe (S&P 100), XS optimization, quintiles
- [v1.2 Documentation](docs/v1.2.md) — cross-sectional analysis, evaluation metrics, design decisions
- [v1.1 Documentation](docs/v1.1.md) — time-series factor pipeline architecture
- [v1.0 Documentation](docs/v1.0.md) — previous strategy-based pipeline

## License

Private project.
