# Autonomous Trading Agent — Architecture Design

**Date**: 2026-02-26
**Status**: Approved
**Context**: Refactoring of `autonomou_evolving_investment` project. Original failed due to unbounded strategy space and custom infrastructure. New approach uses existing frameworks with constrained strategy generation.

---

## 1. Vision

An autonomous trading agent that:
- Learns from a curated knowledge base of 83 documented trading strategies
- Generates parameterized strategy implementations constrained to known patterns
- Screens candidates rapidly via backtesting.py
- Validates winners realistically via NautilusTrader
- Deploys to IBKR paper trading with zero code changes
- Evolves over time through a principled explore/exploit loop with rich diagnostics

## 2. Key Lessons from Original Project

| Problem | Root Cause | Solution in New Design |
|---------|-----------|----------------------|
| Unbounded strategy space | LLM generated arbitrary indicator combos | Template-based specs from 83 documented strategies |
| Custom backtester bugs | Hand-rolled execution simulation | Use backtesting.py + NautilusTrader |
| Auto-growing curriculum | No curation of knowledge | Fixed 145-doc knowledge base |
| 13 evolution knobs | No principled tuning method | Simplified to 3-4 parameters |
| Backtest ≠ live code path | Different execution engines | NautilusTrader: same code backtest → live |
| No universe selection | Strategies applied to arbitrary securities | Strategy-dependent universe selection |

## 3. Technology Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Language | Python 3.11+ | Primary language |
| Screening | backtesting.py | Fast parameter optimization, walk-forward |
| Validation + Live | NautilusTrader | Realistic backtesting, IBKR live trading |
| Broker | Interactive Brokers (TWS API) | Paper → live trading |
| Data (equities) | yfinance + IBKR API | Free OHLCV + fundamentals |
| Data (crypto) | Binance API (optional) | Free crypto data |
| LLM | Claude API (Anthropic) | Strategy generation, evolution reasoning |
| Persistence | SQLite | Strategy registry, results, evolution history |
| Configuration | YAML | Preferences (immutable), settings (runtime) |
| Testing | pytest | Unit + integration tests |
| Linting | ruff + mypy (strict) | Code quality |

## 4. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS TRADING AGENT                   │
│                                                              │
│  ┌────────────┐    ┌──────────────┐    ┌──────────────────┐ │
│  │ Knowledge  │───▶│  Strategy +  │───▶│   Evolution      │ │
│  │ Base       │    │  Universe    │    │   Engine         │ │
│  │ (145 docs) │    │  Generator   │    │                  │ │
│  └────────────┘    │  (LLM)      │    └────────┬─────────┘ │
│                    └──────┬───────┘             │           │
│                           │                     │           │
│                    ┌──────▼──────┐              │           │
│                    │  Strategy   │◀─────────────┘           │
│                    │  Registry   │  (rich diagnostics)      │
│                    └──────┬──────┘                          │
│                           │                                 │
│                    ┌──────▼──────┐                          │
│                    │  Phase 0    │                          │
│                    │  Universe   │                          │
│                    │  Selection  │                          │
│                    └──────┬──────┘                          │
│                           │                                 │
│                    ┌──────▼──────┐                          │
│                    │  Phase 1    │                          │
│                    │  Screen     │                          │
│                    │  (bt.py)    │                          │
│                    └──────┬──────┘                          │
│                           │ top candidates                  │
│                    ┌──────▼──────┐                          │
│                    │  Phase 2    │                          │
│                    │  Validate   │                          │
│                    │  (Nautilus) │                          │
│                    └──────┬──────┘                          │
│                           │ winners                         │
│                    ┌──────▼──────┐                          │
│                    │  Phase 3    │                          │
│                    │  Live/Paper │                          │
│                    │  (IBKR)    │                          │
│                    └─────────────┘                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Data Layer: IBKR API | yfinance | Parquet cache     │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Safety: Risk Engine | Preferences YAML | Audit Gate │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## 5. Core Data Models

### 5.1 StrategySpec

```python
@dataclass
class StrategySpec:
    # Identity
    id: str                    # UUID
    name: str                  # Human-readable name
    template: str              # Knowledge base reference: "momentum/momentum-effect-in-stocks"
    version: int               # Incremented on evolution

    # Strategy parameters (bounded by knowledge base documentation)
    parameters: dict[str, Any] # e.g., {"lookback": 12, "hold_period": 1, "rebalance": "monthly"}

    # Universe specification
    universe: UniverseSpec     # What securities to trade

    # Risk parameters
    risk: RiskParams           # stop_loss, take_profit, position_size, max_positions

    # Multi-strategy composition (optional)
    combination: list[str]     # e.g., ["momentum", "value"] for multi-factor
    combination_method: str    # "equal_weight", "score_rank", "intersection"

    # Metadata
    parent_id: str | None      # ID of parent spec (for evolution tracking)
    generation: int            # Evolution generation number
    created_at: datetime
    created_by: str            # "llm_explore", "llm_exploit", "human"
```

### 5.2 UniverseSpec

```python
@dataclass
class UniverseSpec:
    # Asset class
    asset_class: str           # "us_equity", "forex", "crypto", "etf", "futures"

    # Filter chain (applied in order)
    filters: list[Filter]

    # Size constraints
    max_securities: int        # Cap on universe size
    min_securities: int        # Minimum viable universe

    # Refresh schedule
    rebalance_frequency: str   # "daily", "weekly", "monthly", "quarterly"

    # For static universes
    static_symbols: list[str] | None  # e.g., ["SPY", "QQQ", "IWM"]


@dataclass
class Filter:
    field: str      # "market_cap", "avg_volume", "sector", "momentum_12m", "pe_ratio"
    operator: str   # "greater_than", "less_than", "top_n", "bottom_n", "in_set", "between"
    value: Any      # Threshold, count, or set
```

### 5.3 RiskParams

```python
@dataclass
class RiskParams:
    stop_loss_pct: float | None        # e.g., 0.05 (5%)
    take_profit_pct: float | None      # e.g., 0.15 (15%)
    trailing_stop_pct: float | None    # e.g., 0.03 (3%)
    max_position_pct: float            # Max single position as % of portfolio
    max_positions: int                 # Max concurrent positions
    position_size_method: str          # "equal_weight", "volatility_target", "kelly"
```

### 5.4 StrategyResult (Rich Diagnostics)

```python
@dataclass
class StrategyResult:
    spec_id: str
    phase: str                 # "screen", "validate", "live"

    # Performance metrics
    total_return: float
    annual_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int # Days
    win_rate: float
    profit_factor: float
    total_trades: int

    # Regime performance (for LLM analysis)
    regime_results: dict[str, RegimeResult]  # "bull", "bear", "sideways", "high_vol"

    # Drawdown series (for visualization)
    drawdown_series: list[float]
    equity_curve: list[float]

    # Failure analysis
    failure_reason: str | None     # "low_sharpe", "high_drawdown", "few_trades", etc.
    failure_details: str | None    # Human-readable explanation

    # Costs
    total_fees: float
    total_slippage: float          # Only from NautilusTrader phase

    # Metadata
    backtest_start: date
    backtest_end: date
    run_duration_seconds: float
```

## 6. Universe Selection — Three Levels

### Level 1: Static Universes
Fixed lists refreshed quarterly. Examples:
- `sp500`: S&P 500 components
- `nasdaq100`: NASDAQ 100 components
- `g10_forex`: 10 major currency pairs
- `sector_etfs`: 11 SPDR sector ETFs
- `crypto_top20`: Top 20 cryptocurrencies by market cap

### Level 2: Filtered Universes
Broad pool + filter chain. Example for a momentum strategy:
```yaml
asset_class: us_equity
filters:
  - field: market_cap
    operator: greater_than
    value: 1_000_000_000        # > $1B
  - field: avg_daily_volume
    operator: greater_than
    value: 500_000              # > 500K shares/day
  - field: price
    operator: greater_than
    value: 5.0                  # > $5 (no penny stocks)
  - field: momentum_12m
    operator: top_n
    value: 50                   # Top 50 by 12-month return
max_securities: 50
rebalance_frequency: monthly
```

### Level 3: Dynamic/Computed Universes
Statistical computation required. Example for pairs trading:
```yaml
asset_class: us_equity
filters:
  - field: sector
    operator: in_set
    value: ["Technology", "Financials"]  # Within-sector pairs
  - field: market_cap
    operator: greater_than
    value: 5_000_000_000
computation: cointegration_pairs     # Special computed universe
computation_params:
  method: engle_granger
  p_value_threshold: 0.05
  lookback_days: 252
max_securities: 20                   # 10 pairs
rebalance_frequency: monthly
```

## 7. Two-Stage Backtesting Pipeline

### Phase 1: Screening (backtesting.py)

**Purpose**: Rapidly evaluate strategy viability and find optimal parameters.

**Process**:
1. Translate `StrategySpec` → backtesting.py `Strategy` class (deterministic translator)
2. Run `Backtest.run()` with default parameters
3. Run `Backtest.optimize()` within parameter bounds from knowledge base
4. Run walk-forward analysis (train/test splits)
5. Apply pass/fail filters

**Pass criteria**:
- Sharpe ratio > 0.5 (walk-forward, out-of-sample)
- Max drawdown < 30%
- Total trades > 20 (statistical significance)
- Profit factor > 1.2

**Output**: Top N candidates with optimized parameters → Phase 2.

### Phase 2: Validation (NautilusTrader)

**Purpose**: Confirm performance survives realistic execution conditions.

**Process**:
1. Translate `StrategySpec` → NautilusTrader `Strategy` class (deterministic translator)
2. Run backtest with full reality modeling (slippage, fees, partial fills, spreads)
3. Test across multiple market regimes:
   - Bull market period
   - Bear market period
   - High volatility period
   - Sideways/range-bound period
4. Run capacity analysis (how much capital before market impact degrades returns)

**Pass criteria**:
- Sharpe ratio > 0.3 (stricter after costs — drop from screen is expected)
- Max drawdown < 35%
- Performance positive in ≥ 2 of 4 regimes
- Capacity > $50K (minimum viable for IBKR)

**Output**: Validated strategies with rich diagnostics → Strategy Registry.

### Phase 3: Live (NautilusTrader + IBKR)

**Purpose**: Paper trading to confirm real-market behavior.

**Process**:
1. Deploy validated strategy to IBKR paper account (same NautilusTrader code)
2. Monitor for N days (configurable, default 20 trading days)
3. Compare live performance to backtest expectations
4. Promote to live if within tolerance, or flag for review

## 8. Evolution Engine

### Cycle Structure

```
EXPLORE phase:
  LLM reads knowledge base, selects strategy templates
  Generates StrategySpecs with universe + parameters
  → Screen → Validate → Store results

EXPLOIT phase:
  LLM reviews rich diagnostics from previous cycles
  Proposes refinements:
    - Parameter adjustments (neighboring values)
    - Universe modifications (different filters, sizes)
    - Strategy combinations (multi-factor)
    - Risk parameter tuning
  → Screen → Validate → Store results

EXPLORE/EXPLOIT balance:
  If last 3 cycles improved best Sharpe → exploit more
  If plateau (no improvement in 5 cycles) → explore new templates
  If exhaustion (no improvement in 10 cycles) → pause evolution
```

### Evolution Parameters (simplified from old project's 13)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `batch_size` | 5 | Strategies per evolution cycle |
| `top_n_screen` | 3 | Candidates passing from screen to validation |
| `explore_ratio` | 0.4 | Fraction of batch allocated to new templates |
| `exhaustion_cycles` | 10 | Cycles without improvement before pausing |

### Rich Diagnostics for LLM Feedback

When a strategy fails, the LLM receives:
```
Strategy: momentum/momentum-effect-in-stocks (v3)
Parameters: lookback=12, hold_period=1, top_n=50
Universe: US equities, market_cap > $1B, top 50 by 12m momentum

SCREENING RESULT: PASS (Sharpe: 1.2, MaxDD: -18%)
VALIDATION RESULT: FAIL

Failure reason: Performance degrades significantly with realistic costs
  - Screen Sharpe: 1.2 → Validation Sharpe: -0.1
  - Total slippage cost: 4.2% annually
  - 73% of trades had partial fills

Regime breakdown:
  - Bull (2019-2021): +12% annual, Sharpe 0.8
  - Bear (2022): -28% annual, Sharpe -1.4
  - High vol (2020 Mar-Jun): -15%, Sharpe -0.9
  - Sideways (2023): +3%, Sharpe 0.2

Diagnosis: Strategy requires high turnover (monthly rebalance of 50 stocks).
  Transaction costs and slippage consume most of the alpha.

Suggested directions:
  - Reduce universe size (top 20 instead of 50) to reduce turnover
  - Extend hold period (quarterly instead of monthly)
  - Add turnover constraint to parameter optimization
```

## 9. Safety Guardrails (Carried from Original Project)

### Immutable (human-controlled)
- **preferences.yaml**: Max position size, max daily loss, max portfolio drawdown, allowed asset classes, max leverage
- **Risk engine**: Hard limits enforced at execution time, cannot be overridden by LLM
- **Audit gate**: Every strategy must pass deterministic checks before live deployment

### Deterministic Audit Checks (replacing old LLM-based Layer 2)
1. Look-ahead bias detection (strategy uses future data)
2. Survivorship bias check (universe includes delisted securities)
3. Overfitting detection (in-sample vs out-of-sample Sharpe ratio gap > 1.0)
4. Minimum trade count (< 20 trades = statistically meaningless)
5. Concentration risk (single position > preferences max)
6. Drawdown limit (max drawdown exceeds preferences limit)

## 10. Directory Structure

```
autonomous_trading/
├── knowledge/                     # 145 curated docs (COMPLETE)
│   ├── strategies/                # 83 trading strategies
│   ├── financial-python/          # 14 Python/quant articles
│   ├── key-concepts/              # 15 general trading concepts
│   └── trading-concepts/          # 33 advanced trading concepts
├── src/
│   ├── agent/                     # LLM agent layer
│   │   ├── generator.py           # StrategySpec + UniverseSpec generation
│   │   ├── evolver.py             # Evolution cycle orchestration
│   │   └── reviewer.py            # Rich diagnostics analysis, next-step proposals
│   ├── universe/                  # Universe selection
│   │   ├── spec.py                # UniverseSpec + Filter dataclasses
│   │   ├── static.py              # Curated static lists (SP500, G10, etc.)
│   │   ├── screener.py            # Filter-based selection engine
│   │   ├── computed.py            # Statistical universes (cointegration, etc.)
│   │   └── providers/             # Data source adapters
│   │       ├── yfinance_provider.py
│   │       └── ibkr_provider.py
│   ├── strategies/                # Strategy representation
│   │   ├── spec.py                # StrategySpec + RiskParams dataclasses
│   │   ├── registry.py            # SQLite-backed strategy + results storage
│   │   └── templates/             # Knowledge base → code pattern mapping
│   │       ├── base.py            # Base template interface
│   │       ├── momentum.py        # Momentum strategy patterns
│   │       ├── mean_reversion.py  # Mean reversion patterns
│   │       ├── factor.py          # Factor investing patterns
│   │       └── ...                # One module per category
│   ├── screening/                 # Phase 1: backtesting.py
│   │   ├── translator.py          # StrategySpec → backtesting.py Strategy
│   │   ├── screener.py            # Run backtest, optimize, walk-forward
│   │   └── filters.py             # Pass/fail criteria
│   ├── validation/                # Phase 2: NautilusTrader
│   │   ├── translator.py          # StrategySpec → NautilusTrader Strategy
│   │   ├── validator.py           # Realistic backtest, multi-period, regime testing
│   │   ├── capacity.py            # Strategy capacity analysis
│   │   └── regimes.py             # Market regime detection + period selection
│   ├── live/                      # Phase 3: Paper/Live trading
│   │   ├── deployer.py            # Deploy validated strategy to IBKR
│   │   ├── monitor.py             # Live performance tracking vs backtest expectation
│   │   └── promoter.py            # Paper → live promotion logic
│   ├── data/                      # Unified data layer
│   │   ├── manager.py             # Single entry point for all data
│   │   ├── cache.py               # Local Parquet file cache
│   │   └── sources/               # Data source adapters
│   │       ├── yfinance_source.py
│   │       ├── ibkr_source.py
│   │       └── binance_source.py
│   ├── risk/                      # Safety layer
│   │   ├── engine.py              # Hard risk limits (immutable at runtime)
│   │   ├── auditor.py             # Deterministic pre-live checks
│   │   └── preferences.py         # Preferences YAML loader (frozen dataclass)
│   └── core/                      # Shared infrastructure
│       ├── llm.py                 # Claude API wrapper with logging
│       ├── config.py              # Settings loader
│       ├── logging.py             # Structured logging
│       └── db.py                  # SQLite connection management
├── config/
│   ├── preferences.yaml           # Human-controlled risk limits (IMMUTABLE)
│   └── settings.yaml              # Runtime configuration
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
│   └── plans/
├── main.py                        # Entry point
├── requirements.txt
└── pyproject.toml
```

## 11. Implementation Phases

### Phase A: Foundation (Data + Specs + Screening)
1. Data layer (yfinance + Parquet cache)
2. Core data models (StrategySpec, UniverseSpec, RiskParams, StrategyResult)
3. Universe selection (static + filtered)
4. backtesting.py translator (spec → Strategy class)
5. Screening pipeline (backtest, optimize, walk-forward, filters)
6. Strategy registry (SQLite)

### Phase B: Validation + Safety
7. NautilusTrader translator (spec → Strategy class)
8. Validation pipeline (realistic backtest, multi-regime)
9. Risk engine + preferences YAML
10. Deterministic auditor

### Phase C: Intelligence (LLM Agent)
11. LLM wrapper (Claude API)
12. Strategy generator (knowledge base → StrategySpecs)
13. Rich diagnostics → LLM reviewer
14. Evolution engine (explore/exploit loop)

### Phase D: Live Trading
15. NautilusTrader + IBKR adapter setup
16. Paper trading deployment
17. Live monitoring + alerting
18. Paper → live promotion logic

## 12. Dependencies

```
# Core
python >= 3.11
backtesting >= 0.3.3
nautilus_trader >= 1.200.0
yfinance >= 0.2.0
pandas >= 2.0
numpy >= 1.24

# LLM
anthropic >= 0.40.0

# Broker
ib_insync >= 0.9.86          # IBKR TWS API (for data/scanning)

# Infrastructure
pyyaml >= 6.0
sqlalchemy >= 2.0             # SQLite ORM
pyarrow >= 14.0               # Parquet support

# Dev
pytest >= 8.0
ruff >= 0.5.0
mypy >= 1.10
```
