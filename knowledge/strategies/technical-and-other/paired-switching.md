# Paired Switching

## Overview

Simple rotation strategy between two negatively correlated assets — SPY (equities) and AGG (bonds). Every quarter, invests 100% in whichever asset had the higher return over the prior 90 days. Exploits the premise that recent relative performance indicates which asset class is in a favorable regime.

## Academic Reference

- **Paper**: Quantpedia — "Paired Switching"

## Strategy Logic

### Universe Selection

Two ETFs: SPY (S&P 500) and AGG (Bloomberg Aggregate Bond).

### Signal Generation

Compare 90-day (quarterly) returns: (current_price − price_90_days_ago) / current_price.

### Entry / Exit Rules

- **Long**: 100% in whichever asset (SPY or AGG) had the higher prior-quarter return.
- **Exit**: Liquidate the underperforming asset when switching.
- Binary: fully in SPY or fully in AGG.

### Portfolio Construction

100% allocation to the selected asset. No diversification or partial allocation.

### Rebalancing Schedule

Quarterly (every 3 months). Monthly scheduled events trigger evaluation; rebalancing executes every third month.

## Key Indicators / Metrics

- 90-day trailing return (primary signal)
- Quarterly evaluation cycle
- Negative correlation between SPY and AGG

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Mar 2005 – Jul 2018 |
| Initial Capital | $100,000 |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: US equity ETF (SPY) + US bond ETF (AGG)
- **Resolution**: Daily
- **Lookback**: 90 days

## Implementation Notes

- `history()` requests for 90-day lookback.
- `schedule.on()` for quarterly rebalancing.
- Simple performance comparison logic.
- Python on QuantConnect LEAN.

## Risk Considerations

- Binary positioning (100% one asset) creates concentration risk.
- Quarterly rebalancing is slow — may miss regime changes within the quarter.
- Assumes SPY and AGG remain negatively correlated — correlation can spike during crises.
- 90-day lookback is arbitrary — different windows may produce very different results.
- No risk management, stop-loss, or drawdown controls.
- Simple momentum-based switching may lag during sharp reversals.
- Two-asset universe provides minimal diversification.

## Related Strategies

- [Leveraged ETFs with Systematic Risk Management](../volatility-and-options/leveraged-etfs-with-systematic-risk-management.md)
- [Asset Class Trend Following](../momentum/asset-class-trend-following.md)
- [January Barometer](../calendar-anomalies/january-barometer.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/paired-switching)
