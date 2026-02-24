# Setup Guide

This guide covers installation, configuration, and first-run instructions for the Autonomous Evolving Investment System.

## Prerequisites

- **Python 3.11 or later** -- required for type syntax used throughout the codebase (`X | Y` union types, `list[str]` generics).
- **OpenClaw** (optional for V1) -- the platform that handles scheduling, messaging, and tool routing. Required for cron-based automation and human messaging channels. Not required for manual `python main.py` invocations.
- **Alpaca account** (optional for V1) -- paper trading API account. Not required when running in mock mode (the default), which uses a local SQLite-backed broker.

## Step-by-Step Installation

### 1. Clone the repository

```bash
git clone https://github.com/yuanhao96/autonomous_paper_trading.git
cd autonomous_paper_trading
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate    # macOS / Linux
# .venv\Scripts\activate     # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs the core dependencies: `yfinance`, `pandas`, `numpy`, `anthropic`, `chromadb`, `pyyaml`, `python-dotenv`, `alpaca-trade-api`, `pyarrow`, and testing/linting tools (`pytest`, `ruff`, `mypy`).

### 4. Set up environment variables

Create a `.env` file in the project root directory:

```bash
touch .env
```

Add the following variables:

```
ANTHROPIC_API_KEY=sk-ant-...
ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

The `.env` file is gitignored and loaded automatically by `python-dotenv`.

## Environment Variable Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes (for LLM features) | Anthropic API key for Claude. Required for knowledge synthesis, strategy generation, and any LLM-driven features. Not required for `--dry-run` status checks. |
| `ALPACA_API_KEY` | No (mock mode) | Alpaca paper trading API key. Only required when running with `--no-mock`. |
| `ALPACA_SECRET_KEY` | No (mock mode) | Alpaca paper trading secret key. Paired with `ALPACA_API_KEY`. |
| `ALPACA_BASE_URL` | No | Alpaca API base URL. Defaults to `https://paper-api.alpaca.markets`. Always use the paper trading URL -- never the live trading endpoint. |

## Running in Mock Mode

Mock mode is the default. It requires no Alpaca API keys and uses a local SQLite database to simulate a paper trading account.

```bash
# View current status (portfolio, curriculum stage, strategies)
python main.py --dry-run

# Run a full daily trading cycle in mock mode
python main.py

# Equivalent explicit invocation
python main.py --mock
```

The `--dry-run` flag prints the current agent status and exits without executing any trades. It displays:

- Current curriculum stage
- Active strategies
- Portfolio equity, cash, and open positions
- Next learning tasks (if curriculum is loaded)
- Registered strategies

### Specifying tickers

```bash
python main.py --tickers AAPL,MSFT,GOOG,TSLA
```

Without the `--tickers` flag, the default universe is `SPY, QQQ, AAPL, MSFT, GOOG`.

### Running with Alpaca paper trading

```bash
python main.py --no-mock --tickers AAPL,MSFT
```

This connects to the Alpaca paper trading API using the credentials in your `.env` file.

## Configuring Preferences

Edit `config/preferences.yaml` to set your trading parameters. This file is the agent's constitution -- only humans should modify it.

```yaml
# Risk appetite: conservative | moderate | aggressive
risk_tolerance: moderate

# Maximum portfolio drawdown before protective measures activate
max_drawdown_pct: 15

# Trading style: intraday | swing | position
trading_horizon: swing

# Annual return target (used for performance evaluation)
target_annual_return_pct: 20

# Asset classes the agent is allowed to trade
allowed_asset_classes:
  - us_equities

# Maximum single-position size as a percentage of total equity
max_position_pct: 10

# Daily loss limit; new buy orders are blocked when breached
max_daily_loss_pct: 3

# Maximum exposure to any single sector
max_sector_concentration_pct: 30

# Controls what the evolution loop is allowed to modify
evolution_permissions:
  modify_strategies: true
  modify_backtester: true
  modify_indicators: true
  modify_risk_engine: false    # NEVER set to true in V1-V2
  modify_ui: true
  modify_core_agent: false
```

### Field descriptions

| Field | Type | Description |
|-------|------|-------------|
| `risk_tolerance` | string | Overall risk appetite. Affects position sizing heuristics. |
| `max_drawdown_pct` | number (0-100) | Portfolio drawdown limit in percent. |
| `trading_horizon` | string | Time horizon for strategy selection. |
| `target_annual_return_pct` | number (0-100) | Target annual return for performance evaluation. |
| `allowed_asset_classes` | list of strings | Asset classes the agent may trade. Currently only `us_equities`. |
| `max_position_pct` | number (0-100) | Maximum single position as percent of total equity. |
| `max_daily_loss_pct` | number (0-100) | Daily loss limit. New buys blocked when breached. |
| `max_sector_concentration_pct` | number (0-100) | Maximum exposure to one GICS sector. |
| `evolution_permissions` | map of booleans | Per-module flags controlling what the evolution loop can modify. |

## Connecting to OpenClaw

OpenClaw is the platform layer that provides cron scheduling, messaging channels, and tool streaming. For V1, it is optional -- you can run the system manually with `python main.py`.

When OpenClaw is available:

1. Ensure the OpenClaw WebSocket gateway is running at `ws://127.0.0.1:18789`.
2. Tool definitions in `openclaw/tools/` expose Python trading logic as callable tools.
3. Cron jobs in `openclaw/cron/` define the automated schedule (market scans, evaluations, reports, learning, evolution).
4. Messaging channels (iMessage, Slack, Telegram, Web) are configured through the OpenClaw platform settings.

Refer to the [OpenClaw documentation](https://github.com/openclaw/openclaw) for platform-specific setup instructions.

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_backtester.py -v

# Run tests with coverage
pytest tests/ --cov=. --cov-report=term-missing

# Lint
ruff check .
mypy .
```

## Troubleshooting

### `ANTHROPIC_API_KEY is not set`

The LLM wrapper requires an Anthropic API key. Either:
- Add `ANTHROPIC_API_KEY=sk-ant-...` to your `.env` file, or
- Export it in your shell: `export ANTHROPIC_API_KEY=sk-ant-...`

This error does not occur in `--dry-run` mode or for operations that do not invoke the LLM.

### `yfinance returned empty DataFrame`

This means yfinance could not fetch data for the requested ticker. Common causes:
- Invalid ticker symbol.
- Network connectivity issues.
- yfinance rate limiting (wait a few minutes and retry).
- Market data not available for the requested period/interval combination.

### `Preferences file not found`

The system expects `config/preferences.yaml` to exist. Ensure you have not renamed or deleted this file. If it is missing, recreate it using the template shown in the configuration section above.

### `ChromaDB persistence errors`

ChromaDB stores its data in `data/knowledge_base/` by default. Ensure this directory is writable. If you encounter corruption, delete the directory and let the system recreate it:

```bash
rm -rf data/knowledge_base/
```

### `ModuleNotFoundError`

Ensure you are running from the project root directory and your virtual environment is activated:

```bash
cd autonomou_evolving_investment
source .venv/bin/activate
python main.py --dry-run
```

### Mock broker starts with zero equity

The mock broker initializes with a default paper trading balance. If you see zero equity, check that the SQLite database in `data/paper_trades.db` is not corrupted. Deleting the file will reset the mock account:

```bash
rm -f data/paper_trades.db
```

### Logs and debugging

- Agent logs: `logs/agent.log` (all levels, including DEBUG)
- LLM call logs: `logs/llm_calls.jsonl` (structured JSON lines)
- Trade logs: `logs/trades.jsonl`
- Console output: INFO level and above

To increase console verbosity, modify the `logging.level` field in `config/settings.yaml`.
