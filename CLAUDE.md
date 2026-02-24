# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

An autonomous US stock **paper trading** framework with self-evolving capability, running on [OpenClaw](https://github.com/openclaw/openclaw). The system operates as a dual-agent architecture:

- **Trading Agent** — learns trading knowledge, builds strategies, executes paper trades, evolves itself
- **Auditor Agent** — adversarial counterpart that inspects the trading agent's code, backtests, and behavior for biases, exploits, and self-deception

"Paper trading" means no real money is ever at risk.

## Runtime Platform: OpenClaw

The system runs on OpenClaw, a personal AI assistant platform with:
- **WebSocket gateway** at `ws://127.0.0.1:18789`
- **Cron jobs** for scheduled automation (market scans, daily evaluations, nightly learning, weekly evolution)
- **Sessions** for isolated agent instances (trading session, auditor session, knowledge session, etc.)
- **Messaging channels** (iMessage, Slack, Telegram, Web) for human interaction
- **Tool streaming** for real-time LLM tool invocation

Python trading logic is called from OpenClaw via tool/subprocess. OpenClaw handles scheduling, routing, and human communication.

## Technology Stack

- **Platform**: OpenClaw (Node.js >=22)
- **Trading Logic**: Python 3.11+
- **Market Data**: `yfinance` (free) + `alpaca-trade-api` (paper trading execution)
- **Data Store**: SQLite for trade logs, strategy versions
- **LLM**: Moonshot (Kimi) API via OpenAI-compatible client (`moonshot-v1-32k` default). Set MOONSHOT_API_KEY in .env
- **Knowledge Store**: Markdown files with YAML front-matter for structured knowledge; BM25 full-text search via `rank_bm25`
- **Human Preferences**: `config/preferences.yaml` (human-only write, agent read-only)
- **Testing**: pytest
- **Linting**: ruff + mypy

## Dual-Agent Architecture

```
                    Human (iMessage / Slack / Web)
                         │
                         ▼
                  ┌──────────────┐
                  │  Preferences │  (YAML — human-controlled)
                  │  Permissions │
                  └──────┬───────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
     ┌────────────────┐    ┌────────────────┐
     │  Trading Agent │    │  Auditor Agent │
     │                │    │                │
     │ Learn theories │    │ Learn biases   │
     │ Build strategy │    │ Learn exploits │
     │ Execute trades │    │ Inspect code   │
     │ Evolve system  │    │ Flag anomalies │
     └───────┬────────┘    └───────┬────────┘
             │                     │
             ▼                     ▼
     ┌──────────────┐    ┌──────────────────┐
     │  Code Changes │───►│  Audit Gate      │
     │  + Backtests  │    │  (must pass to   │
     └──────────────┘    │   deploy)         │
                         └────────┬─────────┘
                                  │ pass/fail
                                  ▼
                          Live Paper Trading
```

### Autonomy Gradient

| Full autonomy | Human-gated | Human-controlled (immutable) |
|---------------|-------------|------------------------------|
| Read news/theories | Modify strategies | Risk limits |
| Synthesize knowledge | Rewrite backtester | Trading cycle preferences |
| Design indicators | Add UI features | Permission grants/revocations |
| Run backtests | Promote to live trading | Kill switch |

## Directory Structure

```
autonomou_evolving_investment/
├── openclaw/                  # OpenClaw integration layer
│   ├── tools/                 # Tool definitions callable from OpenClaw sessions
│   └── cron/                  # Cron job definitions (schedules)
├── agents/
│   ├── trading/               # Trading Agent: learning, strategy, execution
│   │   ├── agent.py           # Main trading agent loop
│   │   └── state.py           # Persistent state (goals, plan, performance)
│   └── auditor/               # Auditor Agent: inspection, bias detection
│       ├── agent.py           # Auditor loop
│       ├── checks/            # Specific audit checks (look-ahead bias, overfitting, etc.)
│       └── knowledge.py       # Auditor's own knowledge of trading biases/exploits
├── knowledge/
│   ├── ingestion.py           # Fetch articles, SEC filings, earnings, news, pro analysis
│   ├── store.py               # MarkdownMemory: markdown files + BM25 search
│   ├── synthesizer.py         # LLM-driven synthesis of raw content into structured knowledge
│   ├── curriculum.py          # Structured learning curriculum with progression tracking
│   └── memory/                # Persistent knowledge (git-tracked except daily_log/)
│       ├── trading/
│       │   ├── curriculum/    # Staged topic files (stage_1/ .. stage_4/)
│       │   ├── discovered/    # Emergent topics found during learning
│       │   ├── daily_log/     # Raw daily intake (gitignored)
│       │   └── connections.md # Cross-topic insights
│       └── auditor/
│           ├── biases/        # Known trading biases (V2)
│           ├── reviews/       # Audit review records (V2)
│           └── daily_log/     # Auditor daily log (gitignored)
├── strategies/
│   ├── base.py                # Abstract Strategy interface (generate_signals, backtest, score)
│   ├── registry.py            # Strategy registry; load/save/version strategies
│   └── generator.py           # LLM-driven strategy generation and mutation
├── trading/
│   ├── paper_broker.py        # Alpaca paper trading API wrapper
│   ├── executor.py            # Signal → order execution with risk checks
│   └── risk.py                # Position sizing, drawdown guards, exposure limits
├── evaluation/
│   ├── metrics.py             # Sharpe, drawdown, win rate, P&L calculations
│   ├── backtester.py          # Walk-forward backtesting against historical OHLCV
│   └── reporter.py            # Performance reports for evolution loop + human
├── evolution/
│   ├── planner.py             # LLM generates improvement tasks from performance gaps
│   ├── modifier.py            # Applies code/config changes proposed by planner
│   └── validator.py           # Tests + smoke backtests before changes go live
├── config/
│   ├── preferences.yaml       # Human-only: risk tolerance, trading horizon, return targets
│   ├── settings.yaml          # Runtime config: schedule intervals, model names, books_dir
│   ├── curriculum.yaml        # Trading knowledge curriculum definition
│   ├── books.yaml             # Maps curriculum topic_id → list of book filenames
│   └── prompts/               # Versioned prompt templates for LLM components
├── data/                      # gitignored
│   └── market/                # Cached OHLCV data
├── logs/                      # gitignored
├── tests/
├── main.py                    # Entry point
└── requirements.txt
```

## Knowledge Curriculum (Structured Progression)

The trading agent follows a structured curriculum defined in `config/curriculum.yaml`:

- **Stage 1 — Foundations**: Market microstructure, order types, basic TA/FA, market hours, asset classes
- **Stage 2 — Strategy Families**: Momentum, mean reversion, pairs trading, event-driven, factor models
- **Stage 3 — Risk Management**: Kelly criterion, portfolio theory, drawdown management, position sizing
- **Stage 4 — Advanced**: Regime detection, sentiment analysis, options basics, cross-asset signals
- **Ongoing**: Daily news ingestion, earnings, professional trader analysis (filtered by relevance)

Each topic has a mastery score tracked in `knowledge/curriculum.py`. The agent progresses through stages sequentially; Stage N+1 unlocks when Stage N reaches a mastery threshold.

## Human Preferences (Agent Read-Only)

`config/preferences.yaml` is the agent's constitution. Only humans can modify it (directly, or via natural language through OpenClaw messaging channels using a helper agent).

```yaml
risk_tolerance: moderate          # conservative / moderate / aggressive
max_drawdown_pct: 15
trading_horizon: swing            # intraday / swing / position
target_annual_return_pct: 20
allowed_asset_classes: [us_equities]
max_position_pct: 10
evolution_permissions:
  modify_strategies: true
  modify_backtester: true
  modify_indicators: true
  modify_risk_engine: false
  modify_ui: true
  modify_core_agent: false
```

## Staged Implementation

### V1 — Foundation (current target)
- Knowledge ingestion + curriculum progression
- Simple paper trading with manually-approved strategies
- Daily performance reports via OpenClaw messaging
- Preferences YAML + helper agent for human modification
- Basic auditor that checks backtest results for obvious biases

### V2 — Autonomous Strategy Development
- Agent writes strategy code + indicators from knowledge base
- Walk-forward backtesting with agent-designed metrics
- Auditor reviews all code changes and backtest results
- Promotion pipeline: backtest passes audit → paper trade N days → auto-promote

### V3 — Full Self-Evolution
- Agent modifies its own framework (backtester, data pipelines, UI)
- Browser-based inspection dashboard (agent-built)
- Architectural changes require auditor review + human approval for major changes
- Auditor co-evolves: learns new audit techniques as trading agent grows

## Common Commands

```bash
pip install -r requirements.txt          # Install dependencies
python main.py                           # Start agent (connects to OpenClaw)
pytest tests/                            # Run all tests
pytest tests/test_backtester.py -v       # Run single test file
ruff check . && mypy .                   # Lint
```

## Environment Variables

Store in `.env` (gitignored), load via `python-dotenv`:

```
MOONSHOT_API_KEY=...                              # Moonshot (Kimi) API key
ALPACA_API_KEY=...                                # Alpaca paper trading key
ALPACA_SECRET_KEY=...                             # Alpaca paper trading secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets
OPENCLAW_NOTIFY_CHANNEL=imessage                  # Channel for --notify flag
OPENCLAW_NOTIFY_TARGET=chat_id:6                  # Target group/chat for reports
BOOKS_DIR=~/projects/investment-books-text         # Path to plain-text book library (optional)
```

## Safety Invariants

1. `config/preferences.yaml` is **never written by any agent**. Only human modification (direct edit or via OpenClaw helper agent).
2. `trading/risk.py` enforces hard limits regardless of strategy signals. In V1-V2, this file is not modifiable by the evolution loop.
3. The Auditor Agent has **read-only access** to trading agent code and data. It cannot modify the trading system — only flag, report, and block promotion.
4. All LLM calls are logged for auditability via `core/llm.py`.
5. Strategy promotion requires passing the audit gate. No exceptions.
