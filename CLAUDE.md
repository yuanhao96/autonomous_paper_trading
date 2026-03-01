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

- **Language**: Python 3.11+
- **Backtesting**: backtesting.py
- **Data**: yfinance (+ local Parquet cache when needed)
- **LLM**: Claude API (Anthropic)
- **Broker**: Alpaca (paper trading first, then live)
- **Testing**: pytest
- **Linting**: ruff (line-length 100) + mypy

## Commands

```bash
conda activate base                      # Or appropriate env
pip install -r requirements.txt          # Install dependencies
pytest tests/ -v                         # Run tests
ruff check .                             # Lint
mypy .                                   # Type check
```

## Project Structure

```
knowledge/           # 145 curated docs — READ-ONLY
  strategies/        #   83 strategy templates across 10 categories
  financial-python/  #   14 financial Python guides
  key-concepts/      #   15 general trading concepts
  trading-concepts/  #   33 trading agent modeling concepts
project_memory/      # Cross-session context (lessons, progress)
goal.md              # Original project goals and source URLs
src/                 # All source code (to be built)
tests/               # All tests
config/              # Configuration files (YAML)
```

## Roadmap

Each version replaces one hand-done step with automation. Don't skip ahead.

| Version | What it does | Status |
|---------|-------------|--------|
| **v0** | Hand-picked SMA crossover, hand-written strategy, backtest SPY, print stats | DONE (`v0.py`) |
| **v1** | LLM generates a backtesting.py strategy class from a StrategySpec | DONE (`v1.py`) |
| **v2** | LLM reads a knowledge doc and produces a valid StrategySpec | DONE (`v2.py`) |
| **v3** | Automated evaluation: pass/fail against performance thresholds | DONE (`v3.py`) |
| **v4** | Full loop: all 92 strategy docs → spec → code → backtest → evaluate → rank | DONE (`v4.py`) |
| **v5** | Parameter evolution: tune params within documented bounds | DONE (`v5.py`) |
| **v6** | Paper trading: deploy winning strategies to Alpaca paper trading | |

### StrategySpec (minimal, introduced at v1)

```python
@dataclass
class StrategySpec:
    name: str                    # "SMA Crossover"
    knowledge_ref: str           # "strategies/momentum/sma-crossover.md"
    universe: list[str]          # ["SPY"]
    timeframe: str               # "1d"
    entry_signal: str            # "SMA(20) crosses above SMA(50)"
    exit_signal: str             # "SMA(20) crosses below SMA(50)"
    stop_loss_pct: float         # 0.02
    position_size_pct: float     # 0.95
    params: dict                 # {"fast_period": 20, "slow_period": 50}
```

Grows as needed. Do not add fields until a version requires them.

## Conventions

- All code must pass `ruff check .` and `mypy .` before commit
- Tests in `tests/` with `test_` prefix
- Configuration in YAML under `config/`
- Secrets in `.env` (gitignored), loaded via `python-dotenv`
- Keep modules small and focused — no god classes
- Prefer composition over inheritance
