# Architecture

This document describes the architecture of the Autonomous Evolving Investment System, including the dual-agent model, component responsibilities, knowledge curriculum design, safety invariants, and integration with the OpenClaw platform.

## Dual-Agent Architecture

The system operates as two cooperating (but adversarial) agents with a human-controlled preference layer sitting above both.

```
                    Human (iMessage / Slack / Web)
                         |
                         v
                  +----------------+
                  |  Preferences   |  (YAML -- human-controlled)
                  |  Permissions   |
                  +-------+--------+
                          |
              +-----------+-----------+
              v                       v
     +----------------+      +----------------+
     | Trading Agent  |      | Auditor Agent  |
     |                |      |                |
     | Learn theories |      | Learn biases   |
     | Build strategy |      | Learn exploits |
     | Execute trades |      | Inspect code   |
     | Evolve system  |      | Flag anomalies |
     +-------+--------+      +-------+--------+
             |                        |
             v                        v
     +----------------+      +------------------+
     | Code Changes   +----->| Audit Gate       |
     | + Backtests    |      | (must pass to    |
     +----------------+      |  deploy)         |
                              +--------+---------+
                                       | pass/fail
                                       v
                               Live Paper Trading
```

**Data flow:**

1. The human sets risk limits and permissions in `config/preferences.yaml`.
2. The Trading Agent reads preferences, fetches market data, generates signals through registered strategies, and executes them via the paper broker after risk checks.
3. Before any strategy is promoted, the Auditor Agent inspects the backtest results and strategy code through a battery of checks.
4. Only artefacts that pass the audit gate reach live paper trading.
5. Performance reports are generated and delivered to the human through OpenClaw messaging channels.

---

## Component Descriptions

### `core/` -- LLM Wrapper and Preferences

**`core/llm.py`**

Centralized Anthropic Claude API wrapper. Provides a `call_llm(prompt, system_prompt, model)` function with automatic retries (exponential backoff on rate limits and 5xx errors), structured JSON-line logging of every call (prompt hash, model, token counts, latency), and prompt template loading from `config/prompts/`.

- Input: user prompt string, optional system prompt, optional model override.
- Output: assistant text response.
- Key class: module-level `_client` singleton (`anthropic.Anthropic`).

**`core/preferences.py`**

Reads and validates the human-controlled `config/preferences.yaml`. Returns a frozen `Preferences` dataclass that is immutable at runtime. Validates all fields: risk tolerance enum, trading horizon enum, percentage bounds [0, 100], allowed asset classes, and evolution permission flags.

- Input: path to YAML file.
- Output: `Preferences` (frozen dataclass).

### `knowledge/` -- Knowledge Store, Ingestion, Synthesis, Curriculum

**`knowledge/store.py`**

ChromaDB wrapper for semantic knowledge storage. Documents are stored in named collections aligned with curriculum stages (`general`, `stage_1_foundations`, `stage_2_strategies`, `stage_3_risk_management`, `stage_4_advanced`). Supports adding documents, semantic similarity queries, and topic-based filtering.

- Input: `Document` objects with title, content, source, timestamp, topic tags.
- Output: query results with content, metadata, and distance scores.
- Key class: `KnowledgeStore`.

**`knowledge/ingestion.py`**

Fetches raw content from external sources: articles, SEC filings, earnings reports, news, and professional trader analysis.

- Input: source URLs, ticker symbols, date ranges.
- Output: raw content passed to the synthesizer.

**`knowledge/synthesizer.py`**

LLM-driven synthesis of raw ingested content into structured knowledge documents suitable for storage in ChromaDB.

- Input: raw content from the ingestion module.
- Output: structured `Document` objects with topic tags.

**`knowledge/curriculum.py`**

Tracks learning progression through a four-stage curriculum defined in `config/curriculum.yaml`. Per-topic mastery scores are persisted in SQLite. The tracker determines the current stage, returns the next learning tasks (lowest mastery topics), and checks whether a stage is complete (all topics above the mastery threshold).

- Input: curriculum YAML definition, SQLite database path.
- Output: current stage number, mastery scores, next learning tasks.
- Key classes: `CurriculumTracker`, `Topic`.

### `trading/` -- Market Data, Risk, Broker, Executor

**`trading/data.py`**

Market data fetching and caching. Uses yfinance to retrieve OHLCV data and caches results as Parquet files keyed by ticker, interval, and date. Daily-or-larger intervals are cached for the day; intraday intervals always refetch.

- Input: ticker symbol, period, interval.
- Output: `pd.DataFrame` with columns `Open`, `High`, `Low`, `Close`, `Volume` and a `DatetimeIndex`.
- Key function: `get_ohlcv()`.

**`trading/risk.py`** (SAFETY CRITICAL -- immutable in V1-V2)

Enforces hard risk limits derived from human-controlled preferences. Every order must pass all checks before execution:

1. **Basic sanity** -- positive quantity, valid side/order type, positive equity.
2. **Max position size** -- no single position may exceed `max_position_pct` of total equity.
3. **Max daily loss** -- new buy orders are blocked when daily P&L loss exceeds `max_daily_loss_pct`.
4. **Max sector concentration** -- no single sector may exceed `max_sector_concentration_pct` of equity.

Also provides `check_portfolio_health()` for non-blocking warnings when approaching limits (>80% of any hard limit).

- Input: `OrderRequest`, `PortfolioState`.
- Output: `RiskCheckResult` (approved/rejected with reason).
- Key class: `RiskManager`.

**`trading/paper_broker.py`**

Alpaca paper trading API wrapper. Supports two modes: mock (local SQLite, no external dependencies) and live (Alpaca paper trading API). Provides order submission, portfolio retrieval, current price lookup, and position management.

- Input: order requests.
- Output: `Order` objects, `Portfolio` snapshots.
- Key class: `PaperBroker(mock=True|False)`.

**`trading/executor.py`**

Converts trading signals into broker orders after risk checks. Signals are processed in descending order of strength so that the highest-conviction trades get first access to available capital. Position sizing is computed as `strength * max_allocation / current_price`.

- Input: list of `Signal` objects, broker, risk manager, portfolio state.
- Output: list of `ExecutionResult` objects (executed/rejected with details).
- Key classes: `Signal` (frozen dataclass), `ExecutionResult`.

### `evaluation/` -- Metrics, Backtester, Reporter

**`evaluation/metrics.py`**

Standard trading performance calculations: annualized Sharpe ratio (with configurable risk-free rate), maximum drawdown, win rate, and aggregate P&L statistics. The `generate_summary()` function bundles all metrics into a `PerformanceSummary` dataclass.

- Input: equity curve (`pd.Series`), list of trade dicts.
- Output: `PerformanceSummary`.

**`evaluation/backtester.py`**

Walk-forward backtesting engine. Splits historical data into rolling train/test windows (configurable via `BacktestConfig`: train window 252 days, test window 63 days, step 21 days by default). For each window, the strategy sees only the test slice. Trades are simulated: buy at next day's open after a buy signal, sell at the next sell signal or end of window.

- Input: `Strategy` object, OHLCV `DataFrame`.
- Output: `BacktestResult` with trades, equity curve, metrics, and window count.
- Key classes: `Backtester`, `BacktestConfig`, `BacktestResult`.

**`evaluation/reporter.py`**

Generates Markdown-formatted performance reports for human consumption. Supports daily reports (portfolio value, positions, trades, key metrics) and weekly reports (adds curriculum progress section). Reports are concise enough for iMessage delivery.

- Input: portfolio state, trades, metrics, curriculum progress.
- Output: Markdown string.
- Key functions: `generate_daily_report()`, `generate_weekly_report()`.

### `strategies/` -- Base Interface, Registry, Starter Strategies

**`strategies/base.py`**

Abstract base class that all trading strategies must implement. Defines four required members:

- `name` (property) -- unique identifier string.
- `version` (property) -- semantic version string.
- `generate_signals(data: pd.DataFrame) -> list[Signal]` -- analyse OHLCV data and return trading signals.
- `describe() -> str` -- human-readable strategy description.

**`strategies/registry.py`**

In-memory registry of named strategies. Provides `register()`, `get()`, `list_strategies()`, and `get_all()`. A module-level singleton `registry` is used across the application.

**`strategies/sma_crossover.py`**

SMA Crossover momentum strategy. Generates buy signals when the short-period SMA (default 20) crosses above the long-period SMA (default 50), and sell signals on the inverse crossover. Signal strength is the normalized absolute distance between the two averages.

**`strategies/rsi_mean_reversion.py`**

RSI Mean Reversion strategy. Generates buy signals when the 14-period RSI drops below 30 (oversold) and sell signals when it rises above 70 (overbought). Signal strength reflects how far the RSI has moved past the threshold.

**`strategies/generator.py`**

LLM-driven strategy generation and mutation. Uses the knowledge base and performance gaps to propose new strategies or modify existing ones.

### `agents/` -- Trading Agent and Auditor Agent

**`agents/trading/agent.py`**

Main trading agent loop. Orchestrates the daily cycle: load preferences, register strategies, fetch market data, generate signals, execute through the risk-checked broker, and update state.

**`agents/trading/state.py`**

Persistent agent state (current goals, plan, active strategies, self-assessment, curriculum stage). Backed by SQLite.

**`agents/auditor/agent.py`**

Adversarial auditor that inspects backtest results and market data. Aggregates four check categories into a unified `AuditReport`:

1. **Look-ahead bias** -- scans strategy source code for future-data-leak patterns (`shift(-N)`, open-ended `.loc` slices, etc.) and validates trade entry dates against available data.
2. **Overfitting** -- compares in-sample vs out-of-sample performance metrics to detect excessive parameter fitting.
3. **Survivorship bias** -- checks whether the backtest universe includes only currently-listed tickers.
4. **Data quality** -- inspects equity curves and OHLCV data for gaps, NaN values, and anomalies.

An audit passes only when there are zero critical findings. The auditor has read-only access to all trading agent code and data.

**`agents/auditor/checks/`**

Individual audit check modules: `look_ahead_bias.py`, `overfitting.py`, `survivorship_bias.py`, `data_quality.py`. Each exports a check function that returns a list of `Finding` objects with severity levels (`critical`, `warning`, `info`).

### `openclaw/` -- Platform Integration

**`openclaw/tools/`**

Tool definitions callable from OpenClaw sessions. These expose Python trading logic as tools that can be invoked by the OpenClaw platform via WebSocket.

**`openclaw/cron/`**

Cron job definitions for scheduled automation. Schedules are defined in `config/settings.yaml`:

| Job | Schedule | Description |
|-----|----------|-------------|
| Market open scan | `30 9 * * 1-5` | Scan market at 9:30 AM on weekdays |
| Daily evaluation | `0 17 * * 1-5` | Evaluate performance at 5 PM |
| Daily report | `30 17 * * 1-5` | Generate and send daily report |
| Nightly learning | `0 22 * * *` | Curriculum learning session |
| Weekly evolution | `0 10 * * 6` | Weekly evolution review on Saturday |

---

## Knowledge Curriculum Design

The trading agent follows a structured four-stage curriculum defined in `config/curriculum.yaml`.

### Stages

| Stage | Name | Topics |
|-------|------|--------|
| 1 | Foundations | Market microstructure, order types, basic TA/FA, market hours, asset classes |
| 2 | Strategy Families | Momentum, mean reversion, pairs trading, event-driven, factor models |
| 3 | Risk Management | Kelly criterion, portfolio theory, drawdown management, position sizing |
| 4 | Advanced | Regime detection, sentiment analysis, options basics, cross-asset signals |

### Progression Rules

- Each topic has a mastery score in [0.0, 1.0] persisted in SQLite.
- A stage is complete when every topic in that stage reaches the mastery threshold (default 0.7).
- Stage N+1 unlocks only when stage N is complete.
- The `CurriculumTracker.get_next_learning_tasks()` method returns the lowest-mastery topics in the current stage, prioritizing the weakest areas.

### Ongoing Learning

In addition to the staged curriculum, ongoing tasks run continuously: daily news ingestion, earnings analysis, and professional trader analysis filtered by relevance to the agent's current strategy universe.

---

## Safety Invariants

The system enforces five safety invariants that cannot be overridden by any agent or evolution loop.

### 1. Preferences are human-only

`config/preferences.yaml` is never written by any agent. Only humans may modify it, either by direct file editing or through the OpenClaw helper agent via natural language commands. The `Preferences` dataclass returned by `core/preferences.py` is frozen (immutable at runtime).

### 2. Risk engine is immutable (V1-V2)

`trading/risk.py` enforces hard limits regardless of strategy signals. The header comment reads: "SAFETY CRITICAL -- DO NOT MODIFY VIA EVOLUTION LOOP." The `evolution_permissions.modify_risk_engine` flag is set to `false` in the default preferences. The risk manager checks every order against position size limits, daily loss guards, and sector concentration caps before allowing execution.

### 3. Auditor is read-only

The Auditor Agent has read-only access to trading agent code and data. It cannot modify the trading system. It can only flag findings, generate reports, and block promotion of strategies that fail audit checks. This separation prevents the auditor from being co-opted by the trading agent's optimization objectives.

### 4. LLM calls are logged

All LLM calls are logged for auditability via `core/llm.py`. Each call records a prompt hash, model name, input/output token counts, and latency to `logs/llm_calls.jsonl`.

### 5. Audit gate is mandatory

Strategy promotion requires passing the audit gate. No exceptions. A strategy with any critical finding in its audit report is blocked from live paper trading.

---

## Autonomy Gradient

| Full Autonomy | Human-Gated | Human-Controlled (Immutable) |
|---------------|-------------|------------------------------|
| Read news and theories | Modify strategies | Risk limits |
| Synthesize knowledge | Rewrite backtester | Trading cycle preferences |
| Design indicators | Add UI features | Permission grants and revocations |
| Run backtests | Promote to live trading | Kill switch |

Activities in the "Full Autonomy" column require no human approval. "Human-Gated" activities are permitted by the evolution permissions in `preferences.yaml` but may require audit review. "Human-Controlled" items can only be changed by the human directly.

---

## OpenClaw Integration Model

The system runs on [OpenClaw](https://github.com/openclaw/openclaw), a personal AI assistant platform.

### Sessions

OpenClaw creates isolated agent instances (sessions) for different concerns:

- **Trading session** -- runs the daily trading cycle.
- **Auditor session** -- runs audit checks on proposed strategies and code changes.
- **Knowledge session** -- handles curriculum learning and knowledge ingestion.

### Cron Jobs

Scheduled automation is handled by OpenClaw cron jobs defined in `openclaw/cron/`. The schedules are configured in `config/settings.yaml` and cover market scans, evaluations, reports, learning, and evolution reviews.

### Messaging

OpenClaw routes performance reports and alerts to the human through configured messaging channels (iMessage, Slack, Telegram, Web). The human can also issue natural language commands through these channels to modify preferences via a helper agent.

### Tool Streaming

Python trading logic is exposed as OpenClaw tools via `openclaw/tools/`. The platform invokes these tools through its WebSocket gateway at `ws://127.0.0.1:18789`, enabling real-time LLM tool use and streaming responses.
