# Pre-Holiday Effect

## Overview

Exploits the documented tendency for equity markets to rise in the two trading days before public holidays. Goes fully long SPY when a public holiday is detected within a 2-day forward window, and liquidates when no holidays are upcoming. Binary all-in/all-out positioning.

## Academic Reference

- **Paper**: Quantpedia — "Pre-Holiday Effect"

## Strategy Logic

### Universe Selection

Single asset: SPY (S&P 500 ETF).

### Signal Generation

Use TradingCalendar to identify public holidays within a 2-day forward-looking window. Filter out weekends (`TradingDayType.WEEKEND`) to isolate actual public holidays (`TradingDayType.PUBLIC_HOLIDAY`).

### Entry / Exit Rules

- **Long**: 100% SPY when public holidays detected within 2 trading days.
- **Exit**: Liquidate when no public holidays within the forward window.
- Binary positioning: fully invested or fully cash.

### Portfolio Construction

100% allocation to SPY when signal is active. 100% cash otherwise.

### Rebalancing Schedule

Daily evaluation via `on_data()`.

## Key Indicators / Metrics

- TradingCalendar.GetDaysByType() — holiday detection
- Portfolio.invested — position status
- 2-day forward-looking window

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2000 – Aug 2018 |
| Initial Capital | $100,000 |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: US equity ETF (SPY)
- **Resolution**: Daily
- **External Data**: US equity market trading calendar with public holiday designations

## Implementation Notes

- `timedelta` for date calculations.
- TradingCalendar filters by `TradingDayType.PUBLIC_HOLIDAY`.
- Simple `on_data()` logic: check holidays → buy or liquidate.
- Python on QuantConnect LEAN.

## Risk Considerations

- Single-asset strategy — no diversification.
- Binary positioning (100% or 0%) creates concentration risk.
- Holiday calendars vary by market — US-specific only.
- Gap risk during holiday closures.
- Strategy is invested for very few days per year — low capital utilization.
- Pre-holiday effect is widely documented and may be arbitraged away.
- No stop-loss or risk management mechanisms.

## Related Strategies

- [Turn of the Month in Equity Indexes](turn-of-the-month-in-equity-indexes.md)
- [Option Expiration Week Effect](option-expiration-week-effect.md)
- [Overnight Anomaly](overnight-anomaly.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/pre-holiday-effect)
