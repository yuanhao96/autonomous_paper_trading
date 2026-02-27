# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

An autonomous trading agent that generates, screens, validates, and evolves trading strategies. Refactored from `autonomou_evolving_investment` — the original failed due to unbounded strategy space and custom infrastructure. This version uses existing frameworks with constrained strategy generation from a curated knowledge base.

**Architecture**: Two-stage backtesting pipeline.
- **Stage 1 (Screening)**: backtesting.py — fast parameter optimization and walk-forward analysis
- **Stage 2 (Validation + Live)**: NautilusTrader — realistic execution modeling, same code deploys to IBKR paper trading

**Key Design Principle**: The LLM selects from 83 documented strategy templates (knowledge base) and tunes parameters within documented bounds. It does NOT invent arbitrary indicator combinations.

See `docs/plans/2026-02-26-autonomous-trading-agent-architecture.md` for full architecture.

## Technology Stack

- **Language**: Python 3.11+
- **Screening**: backtesting.py (fast backtest + parameter optimization)
- **Validation + Live**: NautilusTrader (Rust core, Python API, IBKR adapter)
- **Broker**: Interactive Brokers (paper → live)
- **Data**: yfinance + IBKR API + local Parquet cache
- **LLM**: Claude API (Anthropic) for strategy generation and evolution
- **Persistence**: SQLite (strategy registry, results, evolution history)
- **Testing**: pytest
- **Linting**: ruff (line-length 100, select E/F/W/I) + mypy (strict, ignore_missing_imports)

## Commands

```bash
pip install -r requirements.txt          # Install dependencies
pytest tests/                            # Run all tests
pytest tests/test_foo.py -v              # Run single test file
pytest tests/test_foo.py::test_bar -v    # Run single test
ruff check .                             # Lint
mypy .                                   # Type check
ruff check . && mypy .                   # Lint + type check
python main.py                           # Run (once entry point exists)
```

## Project Structure

```
knowledge/           # 145 curated docs — strategies, concepts, indicators (READ-ONLY)
src/
  agent/             # LLM agent: strategy generation, evolution, review
  universe/          # Universe selection: static lists, filters, computed
  strategies/        # StrategySpec, registry, template patterns
  screening/         # Phase 1: backtesting.py translator + screener
  validation/        # Phase 2: NautilusTrader translator + validator
  live/              # Phase 3: IBKR paper/live deployment + monitoring
  data/              # Unified data layer: yfinance, IBKR, Parquet cache
  risk/              # Safety: risk engine, preferences, deterministic auditor
  core/              # Shared: LLM wrapper, config, logging, DB
config/
  preferences.yaml   # Human-controlled risk limits (IMMUTABLE at runtime)
  settings.yaml      # Runtime configuration
tests/
```

## Conventions

- All code must pass `ruff check .` and `mypy .` before commit
- Tests live in `tests/` with `test_` prefix; pytest discovers them via `pythonpath=["."]`
- Configuration files use YAML; store in `config/`
- Environment variables in `.env` (gitignored), loaded via `python-dotenv`
- LLM prompt templates stored in `config/prompts/` as plain text files
- Strategy specs are the single source of truth — translators convert specs to framework-specific code
- Knowledge base (`knowledge/`) is read-only; do not auto-grow or modify
- preferences.yaml is immutable at runtime — only human edits allowed
