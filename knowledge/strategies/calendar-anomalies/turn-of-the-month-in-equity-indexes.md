# Turn of the Month in Equity Indexes

## Overview

Exploits the turn-of-the-month effect: stocks tend to rise during the last trading day of the month and the first three days of the next month. Goes fully long SPY on the last trading day, holds for 3 trading days, then liquidates. Attributed to pension fund cash flows and portfolio rebalancing cycles.

## Academic Reference

- **Paper**: Quantpedia — "Turn of the Month in Equity Indexes"
- **Source**: quantpedia.com/Screener/Details/41

## Strategy Logic

### Universe Selection

Single asset: SPY (S&P 500 ETF).

### Signal Generation

Calendar-based: scheduled event triggers on the last trading day of each month.

### Entry / Exit Rules

- **Long**: Buy SPY at market open on the last trading day of each month.
- **Exit**: Liquidate after 3 trading days.
- Binary: fully invested or fully cash.

### Portfolio Construction

100% allocation to SPY during the 4-day window. 100% cash otherwise.

### Rebalancing Schedule

Monthly. Entry on last trading day, exit 3 days later.

## Key Indicators / Metrics

- Calendar date (month_end scheduling)
- Days counter (3-day holding period)
- Portfolio.invested (position status)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2001 – Jul 2018 |
| Initial Capital | $100,000 |
| Duration | 17+ years |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: US equity ETF (SPY)
- **Resolution**: Daily
- **External**: Market calendar (trading day identification)

## Implementation Notes

- `month_end()` date rule for entry scheduling.
- `_purchase()` method establishes position.
- `on_data()` counts days and triggers exit after 3.
- `set_holdings("SPY", 1)` for full allocation.
- PEP8 compliant. Python on QuantConnect LEAN.

## Risk Considerations

- Calendar anomalies may not persist — widely documented and potentially arbitraged.
- Single-asset strategy with no diversification.
- No stop-loss mechanisms — fully exposed during the 4-day window.
- Strategy is invested for only ~4 days per month — very low capital utilization.
- Market timing dependency — assumes the effect occurs consistently.
- Gap risk from overnight/weekend exposures at month boundaries.
- Transaction costs from monthly round trips reduce already modest returns.

## Related Strategies

- [Pre-Holiday Effect](pre-holiday-effect.md)
- [January Barometer](january-barometer.md)
- [Overnight Anomaly](overnight-anomaly.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/turn-of-the-month-in-equity-indexes)
