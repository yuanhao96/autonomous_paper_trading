# Intraday ETF Momentum

## Overview

Exploits intraday momentum by observing the first half-hour return direction to predict the final half-hour return direction. A positive correlation exists between opening and closing period returns, particularly in actively traded ETFs.

## Academic Reference

- **Paper**: "Intraday Momentum" — Gao, Han, Li, and Zhou (2017)
- **Supporting**: Bogousslavsky (2016) — documented positive correlation between opening and closing period directions
- **Key Finding**: "Momentum pattern is statistically and economically significant, even after accounting for trading fees."

## Strategy Logic

### Universe Selection

Manual selection of liquid ETFs:
- **Original paper universe**: DIA, QQQ, IWM, EEM, FXI, EFA, VWO, XLF, IYR, TLT
- **Implementation universe**: SPY, IWM, IYR

Data resolution: Minute-level.

### Signal Generation

**Morning window** (first 30 minutes):
```
morning_return = (current_close - yesterdays_close) / yesterdays_close
```

**Signal direction**: `sign = 1` if morning return positive, `-1` if negative.

### Entry / Exit Rules

- **Entry**: Market order at beginning of final 30-minute window (triggered when 31 minutes remain until close).
- **Exit**: Market-on-close order submitted simultaneously for the opposite quantity.
- All positions are flat by market close each day.

### Portfolio Construction

Equal-weight across 3 ETFs (EqualWeightingPortfolioConstructionModel).

### Rebalancing Schedule

Intraday — positions opened and closed every trading day.

## Key Indicators / Metrics

- Morning 30-minute return (configurable via `return_bar_count`)
- Constraint: `0 < return_bar_count < 195` minutes
- Previous day's close price tracked per security

## Backtest Performance

| Period | Dates | Strategy Sharpe | Strategy ASD | Benchmark Sharpe | Benchmark ASD |
|--------|-------|-----------------|--------------|------------------|---------------|
| Full Backtest | Jan 2015 – Aug 2020 | -0.628 | 0.002 | 0.582 | 0.023 |
| Fall 2015 Selloff | Aug–Oct 2015 | -0.417 | 0.002 | -0.642 | 0.044 |
| 2020 Crash | Feb–Mar 2020 | **1.452** | 0.045 | -1.466 | 0.416 |
| 2020 Recovery | Mar–Jun 2020 | 0.305 | 0.007 | 7.925 | 0.101 |

**Original paper returns (Gao et al. 2017)**: SPY 6.67%, IWM 11.72%, IYR 24.22%, equal-weighted 14.2% annual.

## Data Requirements

- **Asset Classes**: US ETFs (SPY, IWM, IYR)
- **Resolution**: Minute
- **Lookback Period**: 1 day (previous close)

## Implementation Notes

- Custom `CloseOnCloseExecutionModel` submits market order for entry and `market_on_close_order` for exit in same timestep.
- `IntradayMomentum` class tracks per-security: `bars_seen_today`, `yesterdays_close`, `morning_return`, exchange reference.
- State resets daily at market close.
- Files: `execution.py`, `alpha.py`, `main.py`, `research.ipynb`.

## Risk Considerations

- Strategy underperformed SPY benchmark over the full backtest period (Sharpe -0.628 vs 0.582).
- Outperformed during the 2020 crash but lagged significantly during recovery.
- Lower annual standard deviation indicates more consistent but lower-magnitude returns.
- Transaction costs from daily round-trips can erode returns.
- First/last 30-minute periods have higher volume and volatility — execution slippage risk.

## Related Strategies

- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)
- [Overnight Anomaly](../calendar-anomalies/overnight-anomaly.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/intraday-etf-momentum)
