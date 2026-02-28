# Paper Trading Setup Guide

This guide covers how to run the autonomous trading agent in paper trading mode — from the local PaperBroker simulator to IBKR paper trading, and eventually live promotion.

## Architecture Overview

The system has a three-phase pipeline. Paper trading is Phase 3:

```
Phase 1 (Screening)     →  Phase 2 (Validation)     →  Phase 3 (Paper/Live)
backtesting.py              Multi-regime backtest        Broker execution
Fast param optimization     Realistic cost modeling      Daily rebalancing
Walk-forward analysis       Capacity analysis            Drift monitoring
```

Phase 3 has three broker modes:

| Mode          | Backend       | What it does                                  |
|---------------|---------------|-----------------------------------------------|
| `paper`       | `PaperBroker` | Local in-memory order simulation (default)    |
| `ibkr_paper`  | `IBKRBroker`  | IBKR paper trading account (port 7497)        |
| `live`        | `IBKRBroker`  | IBKR live trading (port 7496)                 |

All backends implement the same `BrokerAPI` interface. The mode is explicitly selected — `paper` always uses the local simulator regardless of whether `ib_insync` is installed.

---

## Option A: Local PaperBroker (No IBKR Needed)

This is the default. No setup required beyond the base install.

### How it works

- Orders fill instantly at current market price (from yfinance data)
- Commission: 0.2% per trade
- Positions and cash tracked in memory, snapshots persisted to SQLite
- No slippage or partial fill simulation

### Running

```python
from src.live.deployer import Deployer
from src.live.monitor import Monitor
from src.strategies.spec import StrategySpec

deployer = Deployer()

# Pre-deployment checks
checks = deployer.validate_readiness(spec, screen_result, validation_result)
if all(c.passed for c in checks):
    deployment = deployer.deploy(spec, symbols, mode="paper")

    # Daily rebalance (call on schedule)
    trades = deployer.rebalance(deployment, spec, prices)

    # Monitor performance
    monitor = Monitor()
    comparison = monitor.compare(deployment, validation_result)
    print(comparison.summary())
```

### Limitations

- Fills at close price — no bid/ask spread modeling
- No market impact or order rejection
- Prices update only when you fetch new data via yfinance

---

## Option B: IBKR Paper Trading

Real paper trading through Interactive Brokers. Orders execute against IB's simulated market.

### Prerequisites

1. **IBKR account** — Apply at [interactivebrokers.com](https://www.interactivebrokers.com). A paper trading account is included with every IBKR account (even if unfunded).

2. **TWS or IB Gateway** — Download and install one:
   - **TWS (Trader Workstation)**: Full GUI, paper port `7497`
   - **IB Gateway**: Headless, paper port `4002` (better for servers)
   - Download: [IBKR Software](https://www.interactivebrokers.com/en/trading/tws.php)

3. **`ib_insync` package**:
   ```bash
   pip install ib_insync
   ```

### TWS/Gateway Configuration

1. Launch TWS (or Gateway) and log in with your **paper trading** credentials
2. Enable API access:
   - TWS: Edit → Global Configuration → API → Settings
   - Check "Enable ActiveX and Socket Clients"
   - Set Socket port to `7497` (TWS paper) or `4002` (Gateway paper)
   - Check "Allow connections from localhost only"
   - Uncheck "Read-Only API" (required for order placement)
3. Leave TWS/Gateway running — the agent connects via localhost

### Settings

In `config/settings.yaml`, the live section controls IBKR connection:

```yaml
live:
  ibkr_host: "127.0.0.1"
  ibkr_paper_port: 7497        # TWS paper=7497, Gateway paper=4002
  ibkr_live_port: 7496         # TWS live=7496, Gateway live=4001
  ibkr_client_id: 1            # Unique per concurrent connection
  initial_cash: 100000         # Starting capital for tracking
  rebalance_frequency: "daily"
  comparison_tolerance: 0.30   # 30% drift tolerance (live vs backtest)
  max_sharpe_drift: 1.0
  drawdown_alert_pct: 0.15     # Alert if drawdown exceeds 15%
  daily_loss_alert_pct: 0.03   # Alert if daily loss exceeds 3%
```

Port reference:

| Application  | Paper | Live |
|-------------|-------|------|
| TWS          | 7497  | 7496 |
| IB Gateway   | 4002  | 4001 |

### Verifying the Connection

```python
from src.live.broker import IBKRBroker, is_ibkr_available

print(is_ibkr_available())  # True if ib_insync installed

broker = IBKRBroker(host="127.0.0.1", port=7497, client_id=1)
broker.connect()
print(broker.get_account_summary())
broker.disconnect()
```

If connection fails, check:
- TWS/Gateway is running and logged in
- API is enabled with correct port
- No other client is using the same `client_id`

---

## Risk Controls

Risk limits are enforced at every stage. These are set in `config/preferences.yaml` and are **immutable at runtime** — only human edits allowed.

```yaml
risk_limits:
  max_position_pct: 0.10      # Max 10% in any single position
  max_portfolio_drawdown: 0.25 # Liquidate if portfolio drops 25%
  max_daily_loss: 0.05         # Stop trading if 5% daily loss
  max_leverage: 1.0            # Cash only, no margin
  max_positions: 20
  min_cash_reserve_pct: 0.05   # Always keep 5% in cash

audit_gate_enabled: true       # Must pass audit before deployment
min_paper_trading_days: 20     # Minimum days before live promotion
```

The deployer runs five pre-deployment checks before any strategy goes live:
1. **Risk limits** — spec doesn't violate position/drawdown limits
2. **Audit gate** — deterministic audit of screen + validation results
3. **Screening passed** — Phase 1 passed
4. **Validation passed** — Phase 2 passed (if available)
5. **Drawdown limit** — historical max drawdown within bounds

---

## Monitoring

The `Monitor` class tracks live performance and compares to backtest expectations:

```python
from src.live.monitor import Monitor

monitor = Monitor()

# Compare live to validation backtest
comparison = monitor.compare(deployment, validation_result)
print(comparison.summary())
# Output:
#   Comparison [OK] — 15 days
#     Return: live=+2.30% expected_annual=+15.00%
#     Sharpe: live=1.20 expected=1.50 drift=0.30
#     MaxDD:  live=3.20% expected=15.00%

# Check for risk violations
violations = monitor.check_risk(deployment)

# Compile live results into a StrategyResult
live_result = monitor.compute_live_result(deployment, spec_id="abc123")
```

Alerts trigger when:
- Return drifts >30% from expected (configurable via `comparison_tolerance`)
- Sharpe degrades more than `max_sharpe_drift` from backtest
- Drawdown exceeds `drawdown_alert_pct` (15%) or 1.5x the backtest drawdown
- Daily loss exceeds `daily_loss_alert_pct` (3%)

---

## Paper → Live Promotion

After `min_paper_trading_days` (default 20), the `Promoter` evaluates whether to go live:

```python
from src.live.promoter import Promoter

promoter = Promoter()
report = promoter.evaluate(deployment, validation_result)
print(report.decision)  # "approved" | "rejected" | "needs_review"
print(promoter.get_promotion_summary(deployment, validation_result))
```

Promotion decisions:
- **approved** — all checks pass: time requirement met, performance within tolerance, no risk violations
- **rejected** — active risk violations or severe performance drift (2+ alerts)
- **needs_review** — minor issues (e.g., time requirement not yet met)

### Going live

To progress through broker modes:

1. **Local paper** (`mode="paper"`): Default. No external dependencies.
2. **IBKR paper** (`mode="ibkr_paper"`): Requires TWS/Gateway on port 7497.
   ```python
   deployment = deployer.deploy(spec, symbols, mode="ibkr_paper")
   ```
3. **IBKR live** (`mode="live"`): Log into TWS with **live** credentials (port 7496).
   ```python
   deployment = deployer.deploy(spec, symbols, mode="live")
   ```

**Warning**: Live mode uses real money. The system applies the same risk checks, but always verify manually before enabling live trading.

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `ib_insync not installed` | Missing package | `pip install ib_insync` |
| Connection refused on 7497 | TWS not running or API disabled | Start TWS, enable API in settings |
| `Not connected to IBKR` | Connection dropped | TWS auto-disconnects after idle; restart |
| `client_id` conflict | Another process using same ID | Change `ibkr_client_id` in settings.yaml |
| Orders not filling | TWS in read-only API mode | Uncheck "Read-Only API" in TWS config |
| `PaperBroker` used instead of IBKR | Using `mode="paper"` (default) | Use `mode="ibkr_paper"` for IBKR paper trading |
