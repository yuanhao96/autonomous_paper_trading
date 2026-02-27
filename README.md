# Autonomous Trading Agent

An autonomous trading system that uses LLMs to generate, screen, validate, and evolve quantitative trading strategies. The LLM selects from 87 documented strategy templates and tunes parameters within documented bounds — it does not invent arbitrary indicator combinations.

## How It Works

```
                    ┌─────────────────┐
                    │  Knowledge Base  │  169 curated docs: strategies,
                    │   (read-only)   │  indicators, concepts
                    └────────┬────────┘
                             │
                             ▼
┌──────────┐    ┌─────────────────────┐    ┌──────────────────┐
│  LLM     │───▶│  Strategy Generator │───▶│   StrategySpec   │
│ (GPT-5.2)│    │  explore / exploit  │    │  (structured JSON)│
└──────────┘    └─────────────────────┘    └────────┬─────────┘
                                                    │
                    ┌───────────────────────────────┘
                    │
                    ▼
        ┌───────────────────┐      ┌────────────────────┐
        │  Phase 1: Screen  │─────▶│  Phase 2: Validate  │
        │  backtesting.py   │      │  Multi-regime test   │
        │  Walk-forward opt │      │  Realistic costs     │
        └───────────────────┘      └──────────┬──────────┘
                                              │
                    ┌─────────────────────────┘
                    │
                    ▼
        ┌───────────────────┐      ┌────────────────────┐
        │  Audit Gate       │─────▶│  Phase 3: Deploy    │
        │  Risk checks      │      │  Paper → Live       │
        │  Consistency      │      │  IBKR or simulated  │
        └───────────────────┘      └──────────┬──────────┘
                                              │
                    ┌─────────────────────────┘
                    ▼
        ┌───────────────────┐      ┌────────────────────┐
        │  Monitor          │─────▶│  Promoter           │
        │  Drift detection  │      │  Paper → Live eval  │
        │  Risk alerts      │      │  20-day minimum     │
        └───────────────────┘      └────────────────────┘
                    │
                    └──────▶ Learning loop feeds back to Generator
```

The evolution engine runs an explore/exploit loop:
- **Explore**: Try new templates from the knowledge base
- **Exploit**: Refine top-performing strategies based on diagnostics

A learning-from-failure system feeds parameter optimization insights, overfitting analysis, and parameter-outcome correlations back into the LLM prompts.

## Quick Start

### Prerequisites

- Python 3.11+
- An OpenAI API key (or Anthropic API key)

### Install

```bash
git clone <repo-url> && cd autonomous-trading
pip install -r requirements.txt
```

### Configure

```bash
# Set your API key
echo "OPENAI_API_KEY=sk-..." > .env

# Or for Anthropic
# echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
# Then edit config/settings.yaml: llm.provider: "anthropic"
```

### Run

```bash
# Full pipeline: evolve → screen → validate → deploy (paper)
python main.py run

# Run 3 evolution cycles on S&P 500
python main.py evolve --cycles 3 --universe sp500

# Deploy a specific strategy to paper trading
python main.py deploy <SPEC_ID> --mode paper

# Start the automated scheduler
python main.py schedule

# Show available templates and universes
python main.py info

# Check pipeline status
python main.py status
```

## Project Structure

```
autonomous-trading/
├── main.py                  # CLI entry point
├── config/
│   ├── settings.yaml        # Runtime configuration (editable)
│   └── preferences.yaml     # Risk limits (immutable at runtime)
├── knowledge/               # 169 curated strategy docs (read-only)
│   ├── strategies/          #   87 strategy templates
│   ├── key-concepts/        #   Core quant concepts
│   ├── trading-concepts/    #   Trading mechanics
│   └── financial-python/    #   Implementation patterns
├── src/
│   ├── orchestrator.py      # Top-level pipeline orchestrator
│   ├── scheduler.py         # Automated trading scheduler
│   ├── agent/               # LLM agent
│   │   ├── generator.py     #   Strategy generation (explore/exploit)
│   │   ├── evolver.py       #   Evolution engine (explore/exploit loop)
│   │   └── reviewer.py      #   Diagnostics formatting for LLM feedback
│   ├── strategies/          # Strategy data models
│   │   ├── spec.py          #   StrategySpec, StrategyResult, RiskParams
│   │   └── registry.py      #   SQLite persistence
│   ├── screening/           # Phase 1: fast backtesting
│   │   ├── screener.py      #   Screen + walk-forward optimization
│   │   └── translator.py    #   StrategySpec → backtesting.py Strategy class
│   ├── validation/          # Phase 2: multi-regime validation
│   │   ├── validator.py     #   Regime detection + per-regime backtest
│   │   ├── regimes.py       #   Bull/bear/high_vol/sideways detection
│   │   ├── capacity.py      #   Capacity analysis from volume data
│   │   └── translator.py    #   StrategySpec → NautilusTrader strategy
│   ├── live/                # Phase 3: paper/live trading
│   │   ├── deployer.py      #   Deployment lifecycle
│   │   ├── broker.py        #   BrokerAPI + IBKRBroker + PaperBroker
│   │   ├── monitor.py       #   Performance tracking + drift detection
│   │   ├── promoter.py      #   Paper → live promotion evaluation
│   │   └── signals.py       #   Target weight computation
│   ├── data/                # Data layer
│   │   └── manager.py       #   yfinance + IBKR + Parquet cache
│   ├── universe/            # Universe selection
│   │   ├── static.py        #   Predefined symbol lists
│   │   └── computed.py      #   Dynamic screening (momentum, etc.)
│   ├── risk/                # Safety layer
│   │   ├── engine.py        #   Risk limit enforcement
│   │   └── auditor.py       #   Deterministic pre-deployment audit
│   ├── core/                # Shared infrastructure
│   │   ├── llm.py           #   OpenAI/Anthropic client wrapper
│   │   ├── config.py        #   Settings + preferences loader
│   │   └── db.py            #   SQLite setup
│   └── reporting/           # Human-readable reports
│       └── reporter.py
├── tests/
│   ├── unit/                # Fast, no network
│   └── integration/         # Requires data/API access
├── data/cache/              # Parquet data cache (gitignored)
└── docs/
    └── paper-trading-setup.md
```

## Configuration

### `config/settings.yaml` — Runtime settings

| Section | Key settings |
|---------|-------------|
| `data` | Cache directory, default source (yfinance), resolution |
| `screening` | Initial cash, commission, pass criteria (min Sharpe, max DD, min trades) |
| `validation` | Pass criteria, regime requirements, capacity threshold |
| `evolution` | Batch size, explore ratio, exhaustion threshold |
| `live` | IBKR connection, rebalance frequency, drift tolerance, alert thresholds |
| `llm` | Provider (openai/anthropic), model, temperature, max tokens |

### `config/preferences.yaml` — Risk limits (human-controlled)

These cannot be modified at runtime. The system enforces them at every stage.

```yaml
risk_limits:
  max_position_pct: 0.10       # Max 10% in any single position
  max_portfolio_drawdown: 0.25 # Hard stop at 25% drawdown
  max_daily_loss: 0.05         # Halt trading at 5% daily loss
  max_leverage: 1.0            # Cash only
  max_positions: 20
audit_gate_enabled: true
min_paper_trading_days: 20
```

## Strategy Templates

The LLM selects from 87 supported templates across 9 categories:

| Category | Count | Examples |
|----------|-------|---------|
| Momentum | 22 | Dual momentum, time-series momentum, sector rotation |
| Mean Reversion | 11 | RSI mean reversion, Bollinger bands, pairs trading |
| Technical | 6 | Moving average crossover, breakout, trend following |
| Factor | 11 | Fama-French, beta, liquidity, accrual anomaly |
| Value | 5 | Price-earnings anomaly, book-to-market, G-score |
| Calendar | 7 | Turn of month, January effect, overnight anomaly |
| Volatility | 4 | VIX prediction, volatility risk premium |
| Forex | 5 | Carry trade, momentum, risk premia |
| Commodities | 5 | Term structure, gold timing, trend following |

Run `python main.py info` to see the full list.

## Available Universes

| Universe | Description |
|----------|-------------|
| `sp500` | S&P 500 constituents |
| `nasdaq100` | Nasdaq 100 constituents |
| `sector_etfs` | 11 SPDR sector ETFs |
| `broad_etfs` | Broad market ETFs |
| `g10_forex` | G10 currency pairs |
| `crypto_top` | Top cryptocurrencies |

Computed universes (dynamic screening) are also available — run `python main.py info` for details.

## Two-Stage Backtesting

### Phase 1: Screening (backtesting.py)

Fast parameter optimization with walk-forward analysis:
- Train window: 252 days (1 year)
- Test window: 63 days (~3 months)
- Step: 21 days (~1 month)
- Pass criteria: Sharpe > 0.5, max DD < 30%, min 20 trades, profit factor > 1.2

### Phase 2: Validation

Multi-regime backtesting with realistic cost modeling:
- Detects bull, bear, high-volatility, and sideways regimes from SPY
- Runs backtest in each regime with 2.5x commission (simulating spread + slippage)
- When NautilusTrader is available: uses full reality modeling (partial fills, slippage)
- When unavailable: falls back to backtesting.py with enhanced costs
- Pass criteria: Sharpe > 0.3, max DD < 35%, positive in 2+ regimes, $50K+ capacity

## Paper Trading

The system supports two paper trading backends:

- **PaperBroker** (default): In-memory simulation, no external dependencies
- **IBKRBroker**: Real paper orders via Interactive Brokers TWS/Gateway

See [docs/paper-trading-setup.md](docs/paper-trading-setup.md) for full setup instructions.

## Learning-from-Failure System

The agent improves over time through three feedback mechanisms:

1. **Parameter optimization insights** — Walk-forward optimization discovers better parameters; these shifts are fed back to the LLM in exploit mode
2. **Overfitting analysis** — Tracks the screen→validation gap rate to detect when strategies look good in screening but fail validation
3. **Parameter-outcome correlations** — Identifies which parameter ranges and universes correlate with high/low Sharpe across strategies sharing the same template

## Development

```bash
# Run all tests
pytest tests/

# Run unit tests only (fast, no network)
pytest tests/unit/ -q

# Lint
ruff check .

# Type check
mypy .

# Lint + type check
ruff check . && mypy .
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Screening | backtesting.py |
| Validation | NautilusTrader (optional, falls back to backtesting.py) |
| Broker | Interactive Brokers via ib_insync (optional, falls back to PaperBroker) |
| Data | yfinance + local Parquet cache |
| LLM | OpenAI (GPT-5.2) or Anthropic (Claude) |
| Persistence | SQLite via SQLAlchemy |
| Testing | pytest |
| Linting | ruff, mypy |
