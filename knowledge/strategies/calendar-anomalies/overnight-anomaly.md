# Overnight Anomaly

## Overview

Captures the overnight return anomaly by buying SPY at market close and selling at market open the next day. Based on research showing positive returns occur disproportionately during overnight hours. However, backtest demonstrates that transaction costs entirely eliminate profitability.

## Academic Reference

- **Paper**: Quantpedia — "Overnight Anomaly"

## Strategy Logic

### Universe Selection

Single asset: SPY (S&P 500 ETF).

### Signal Generation

Time-based: no technical indicators. Buy at close, sell at open.

### Entry / Exit Rules

- **Long**: Buy SPY at market close each trading day.
- **Exit**: Liquidate entire position at market open the next trading day.
- Daily round-trip trades.

### Portfolio Construction

100% allocation to SPY when holding overnight. Cash during trading hours.

### Rebalancing Schedule

Daily. Buy at close, sell at open.

## Key Indicators / Metrics

- None — purely time-based scheduling.
- Market open/close times.

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2000 – 2018 |
| Initial Capital | $100,000 |
| Resolution | Hourly |
| Key Finding | Fees for 20 years ≈ 25% of initial capital |
| Verdict | Returns canceled by transaction costs |

## Data Requirements

- **Asset Classes**: US equity ETF (SPY)
- **Resolution**: Hourly
- **Brokerage Model**: Interactive Brokers fee structure

## Implementation Notes

- Scheduled event handlers for close-buy and open-sell.
- Interactive Brokers brokerage model for realistic fee simulation.
- Class-based OOP design.
- Python on QuantConnect LEAN.

## Risk Considerations

- **Transaction costs eliminate profitability**: "Returns are canceled out once transaction costs are taken into account."
- Fees over 20 years consume ~25% of initial capital.
- "Very sensitive to slippage costs and fees" — any execution delay erodes returns.
- Daily round-trip trades amplify market impact and commission expenses.
- Overnight anomaly is widely known — likely arbitraged in modern markets.
- No risk management or stop-loss mechanisms.
- Assumes perfect execution at close and open — unrealistic in practice.

## Related Strategies

- [Pre-Holiday Effect](pre-holiday-effect.md)
- [Turn of the Month in Equity Indexes](turn-of-the-month-in-equity-indexes.md)
- [Option Expiration Week Effect](option-expiration-week-effect.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/overnight-anomaly)
