# OpenClaw Integration Guide

This guide explains how to run the Autonomous Evolving Investment System as a long-term service
on an OpenClaw instance, and how the agent interacts with OpenClaw and with you via iMessage.

---

## Overview

OpenClaw is a personal AI assistant platform that runs on your Mac and bridges messaging channels
(iMessage, Slack, Telegram, etc.) to an LLM agent runtime. This system integrates with it in
two ways:

1. **Cron jobs** — OpenClaw schedules and triggers Python actions automatically (market scans,
   learning sessions, daily reports)
2. **Tool calls** — When you send a message like *"how's my portfolio?"*, OpenClaw's LLM agent
   calls the registered tools, which invoke Python, and returns the result to you via iMessage

```
You (iMessage)
    │
    ▼
OpenClaw Gateway (ws://127.0.0.1:18789)
    │
    ├─ Main LLM Session ──► tool calls ──► Python tool handlers ──► SQLite / yfinance / Alpaca
    │
    └─ Cron Sessions ──────► scheduled commands ──► Python main.py --action ...
                                                         │
                                                         └─► result pushed back via iMessage
```

---

## Prerequisites

On the OpenClaw machine (your Mac running iMessage):

- OpenClaw installed and running (`openclaw start`)
- iMessage channel configured (see [iMessage setup](#imessage-setup))
- Python 3.11+ with the project's `.venv` set up
- Project cloned to a stable path (e.g. `~/projects/autonomous_paper_trading`)
- `.env` file in the project root with `ANTHROPIC_API_KEY` set

---

## Step 1: Clone and Install on the OpenClaw Machine

```bash
git clone https://github.com/yuanhao96/autonomous_paper_trading.git ~/projects/autonomous_paper_trading
cd ~/projects/autonomous_paper_trading

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Verify the install:

```bash
python main.py --dry-run
# Should print: portfolio status + curriculum stage + next learning tasks
```

Copy and fill in `.env`:

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY at minimum
```

---

## Step 2: Add `--action` Dispatch to `main.py`

The cron jobs and tool handlers call `main.py` with an `--action` flag. Add this dispatch
to `main.py`'s `_parse_args()` and `main()`:

```python
# In _parse_args(), add:
parser.add_argument(
    "--action",
    choices=[
        "market_scan", "daily_eval", "daily_report",
        "learn", "weekly_review",
        "query_portfolio", "query_performance",
        "query_knowledge", "run_backtest",
    ],
    help="Action to run (used by OpenClaw cron jobs and tools)",
)
parser.add_argument(
    "--query", type=str, default="",
    help="Query string for query_knowledge and run_backtest actions",
)
parser.add_argument(
    "--notify", action="store_true", default=False,
    help="Send result via OpenClaw outbound message after running",
)
```

```python
# In main(), add the action dispatch branch alongside --dry-run:
elif args.action == "market_scan":
    agent = TradingAgent(mock=mock)
    result = agent.run_market_scan()
    print(result)

elif args.action == "daily_eval":
    agent = TradingAgent(mock=mock)
    result = agent.run_daily_evaluation()
    print(result)

elif args.action == "daily_report":
    agent = TradingAgent(mock=mock)
    result = agent.run_daily_evaluation()
    print(result)
    if args.notify:
        _send_openclaw_message(result)   # see Step 5

elif args.action == "learn":
    agent = TradingAgent(mock=mock)
    result = agent.run_learning_session()
    print(result)

elif args.action == "query_portfolio":
    import asyncio
    from openclaw.tools.query_portfolio import handle
    print(asyncio.run(handle({})))

# ... etc for remaining actions
```

---

## Step 3: Register Cron Jobs

OpenClaw stores cron jobs in `~/.openclaw/cron/jobs.json`. Each job mints a fresh isolated
session, runs an agent turn, and optionally delivers the result back to a channel.

Create or append to `~/.openclaw/cron/jobs.json`:

```json
[
  {
    "name": "trading-market-scan",
    "schedule": {
      "kind": "cron",
      "expr": "30 9 * * 1-5",
      "tz": "America/New_York"
    },
    "sessionTarget": "isolated",
    "payload": {
      "kind": "agentTurn",
      "message": "Run the market open scan: execute `python ~/projects/autonomous_paper_trading/main.py --action market_scan --mock` and report any signals found."
    },
    "delivery": { "mode": "none" }
  },
  {
    "name": "trading-daily-report",
    "schedule": {
      "kind": "cron",
      "expr": "30 17 * * 1-5",
      "tz": "America/New_York"
    },
    "sessionTarget": "isolated",
    "payload": {
      "kind": "agentTurn",
      "message": "Generate the daily trading report: execute `python ~/projects/autonomous_paper_trading/main.py --action daily_report --mock` and send the full output to me via iMessage."
    },
    "delivery": { "mode": "announce" }
  },
  {
    "name": "trading-nightly-learning",
    "schedule": {
      "kind": "cron",
      "expr": "0 22 * * *",
      "tz": "America/New_York"
    },
    "sessionTarget": "isolated",
    "payload": {
      "kind": "agentTurn",
      "message": "Run the nightly learning session: execute `python ~/projects/autonomous_paper_trading/main.py --action learn --mock` and summarise what was studied."
    },
    "delivery": { "mode": "none" }
  },
  {
    "name": "trading-weekly-review",
    "schedule": {
      "kind": "cron",
      "expr": "0 10 * * 6",
      "tz": "America/New_York"
    },
    "sessionTarget": "isolated",
    "payload": {
      "kind": "agentTurn",
      "message": "Run the weekly trading review: execute `python ~/projects/autonomous_paper_trading/main.py --action weekly_review --mock` and send the summary to me."
    },
    "delivery": { "mode": "announce" }
  }
]
```

> **Note:** OpenClaw cron jobs run an LLM agent turn, not a raw shell command. The agent is
> instructed to run the Python script and relay results back. If you want raw shell execution
> without an LLM turn, wrap the Python call in an OpenClaw plugin command (see Step 4).

Reload cron jobs after editing:

```bash
openclaw cron reload
# or restart the gateway:
openclaw restart
```

---

## Step 4: Register Tool Commands via a Plugin

For user-facing commands (portfolio queries, preference changes, backtests), create a minimal
OpenClaw plugin that shells out to your Python handlers. This makes them available as slash
commands and as LLM tool calls.

Create `~/projects/autonomous_paper_trading/openclaw/plugin/openclaw.plugin.json`:

```json
{
  "id": "trading-agent",
  "name": "Autonomous Trading Agent",
  "description": "Paper trading agent tools — portfolio, performance, backtest, preferences"
}
```

Create `~/projects/autonomous_paper_trading/openclaw/plugin/index.ts` (or `.js`):

```typescript
import { execSync } from "child_process";

const PYTHON = "~/projects/autonomous_paper_trading/.venv/bin/python";
const MAIN   = "~/projects/autonomous_paper_trading/main.py";

function run(action: string, extra = ""): string {
  try {
    return execSync(`${PYTHON} ${MAIN} --action ${action} --mock ${extra}`, {
      encoding: "utf8",
      timeout: 30_000,
    });
  } catch (e: any) {
    return `Error: ${e.message}`;
  }
}

export default function (api: any) {
  api.registerCommand({
    name: "portfolio",
    description: "Show current paper trading portfolio",
    handler: async () => ({ text: run("query_portfolio") }),
  });

  api.registerCommand({
    name: "performance",
    description: "Show trading performance metrics",
    handler: async () => ({ text: run("query_performance") }),
  });

  api.registerCommand({
    name: "backtest",
    description: "Backtest a strategy. Usage: /backtest sma_crossover AAPL",
    acceptsArgs: true,
    handler: async (ctx: any) => ({
      text: run("run_backtest", `--query "${ctx.args ?? "sma_crossover SPY"}"`),
    }),
  });

  api.registerCommand({
    name: "set-pref",
    description: "Change a trading preference. Usage: /set-pref risk_tolerance conservative",
    acceptsArgs: true,
    requireAuth: true,
    handler: async (ctx: any) => ({
      text: run("modify_prefs", `--query "${ctx.args ?? ""}"`),
    }),
  });

  api.registerCommand({
    name: "trading-status",
    description: "Show agent status: portfolio, curriculum stage, active strategies",
    handler: async () => ({ text: run("", "--dry-run").replace("--action", "") }),
  });
}
```

Install the plugin:

```bash
openclaw plugin install ~/projects/autonomous_paper_trading/openclaw/plugin
openclaw restart
```

---

## Step 5: iMessage Setup

iMessage is the primary interaction channel. Requirements on the OpenClaw Mac:

1. macOS with Messages app signed in to your Apple ID
2. Install `imsg` CLI: `brew install bluebubbles-tools/tools/imsg` (or the OpenClaw-recommended
   tool — check `openclaw onboard` for the current recommendation)
3. Grant Full Disk Access to the terminal / OpenClaw process in
   **System Settings → Privacy & Security → Full Disk Access**
4. Grant Automation permission for Messages when prompted

Configure iMessage in `~/.openclaw/openclaw.json`:

```json
{
  "agent": {
    "model": "anthropic/claude-sonnet-4-6"
  },
  "channels": {
    "imessage": {
      "enabled": true,
      "imsgPath": "/usr/local/bin/imsg",
      "dmPolicy": "pairing",
      "allowFrom": ["+1YOURNUMBER"]
    }
  }
}
```

Set `allowFrom` to your own phone number so only you can trigger the agent.

Test outbound messaging:

```bash
openclaw message send --to "+1YOURNUMBER" --message "Trading agent is online"
```

---

## Step 6: What the Interaction Looks Like

Once everything is wired, here is how you interact via iMessage:

### User-initiated queries

```
You:    /portfolio
Bot:    === Portfolio Status ===
        Total Equity:  $103,421.50
        Cash:          $82,000.00
        Positions (1):
          AAPL  qty=10  avg=$187.50  pnl=+$340.00

You:    /backtest sma_crossover SPY
Bot:    SMA Crossover on SPY (2y walk-forward):
        Trades: 6 | Win Rate: 67% | Sharpe: 1.21
        Max Drawdown: 8.3% | Total P&L: +$12,400
        Auditor: PASSED (1 warning)

You:    /set-pref risk_tolerance conservative
Bot:    Updated: risk_tolerance  moderate → conservative

You:    how is my trading doing this week?
Bot:    (LLM agent calls query_performance tool automatically)
        Week to date: +$841 (+0.84%)
        3 trades: 2 wins, 1 loss | Win rate: 67%
        Sharpe (rolling): 1.4
```

### Cron-triggered (proactive push to your iMessage)

```
[5:30 PM weekday — pushed automatically]
Bot:    📊 Daily Report — Mon Feb 24

        Portfolio: $103,421 (+$421 today, +0.41%)
        Cash: $82,000 | Positions: 1

        Today's trades:
          BUY  AAPL ×10 @ $189.20 (RSI oversold signal)

        Performance:
          Sharpe (30d): 1.4 | Max DD: 2.1% | Win rate: 67%

        Curriculum: Stage 1 — studying Order Types [40% mastery]

[10:00 AM Saturday — weekly review]
Bot:    📈 Weekly Review — Week of Feb 17

        Net P&L: +$1,204 (+1.2%)
        Best trade: MSFT +$380 | Worst: GOOGL -$120
        ...
```

---

## Step 7: Keeping the Service Running

OpenClaw handles its own process management. To ensure it restarts after reboots:

```bash
# Add OpenClaw to macOS login items:
openclaw install-service
# or use launchd:
openclaw launchd install
```

Your Python `.venv` and SQLite databases persist between restarts automatically since they are
stored in the project directory (not `/tmp`).

To monitor that the service is healthy:

```bash
openclaw status          # check gateway is running
openclaw cron list       # verify cron jobs are registered
tail -f ~/projects/autonomous_paper_trading/logs/agent.log   # Python-side logs
```

---

## Next Steps

### Immediate (on the OpenClaw machine)

| # | Task | How |
|---|------|-----|
| 1 | Add `--action` dispatch to `main.py` | Edit as shown in Step 2 |
| 2 | Create and load `~/.openclaw/cron/jobs.json` | Copy from Step 3, run `openclaw cron reload` |
| 3 | Install the plugin | Step 4 — `openclaw plugin install` |
| 4 | Configure iMessage | Step 5 — edit `openclaw.json`, set `allowFrom` |
| 5 | Send test message | `/portfolio` or `/trading-status` via iMessage |

### V1 → V2 evolution (once running)

| # | What changes | Impact |
|---|--------------|--------|
| 6 | Agent progresses through curriculum | Better knowledge base for strategy reasoning |
| 7 | Enable `modify_strategies: true` in preferences | Agent can propose new indicator code |
| 8 | Auditor review gate for strategy code changes | Changes only apply if auditor passes |
| 9 | Walk-forward promotion: backtest N days → paper trade M days | Strategies proven before going live |

### Configuration to tune as you go

- `config/preferences.yaml` — adjust `risk_tolerance`, `max_position_pct`, `max_drawdown_pct`
  to match your actual comfort level
- `config/settings.yaml` — change `llm.model` to `claude-opus-4-6` for higher-quality
  synthesis at the cost of API spend
- `config/curriculum.yaml` — add or reorder topics to focus learning on areas you care about
- Cron schedule timezones — make sure `tz` matches where your OpenClaw machine is physically
  located, not where the markets are (the ET times are pre-adjusted in the cron expressions)

---

## Troubleshooting

**Cron job fires but nothing happens**
The isolated session spins up a fresh LLM context with no tools registered. Make sure the
plugin is installed (`openclaw plugin list`) so the agent has `Bash`/`computer` tool access
to run the Python subprocess.

**iMessage not delivering**
Check Full Disk Access permission and run `openclaw channels test imessage`. Also confirm
Messages is open and signed in on the Mac.

**Python errors in logs**
```bash
tail -100 ~/projects/autonomous_paper_trading/logs/agent.log
```
The most common cause is a missing `.env` (no `ANTHROPIC_API_KEY`) or the `.venv` not being
activated when the subprocess runs. Use the full path to `.venv/bin/python` in all cron and
plugin commands.

**Database locked errors**
SQLite doesn't handle concurrent writes well. If cron jobs and tool calls overlap, you may
see `database is locked`. The fix in V2 will be to add write queuing; for V1, the cron schedule
is spaced enough to avoid this in practice.
