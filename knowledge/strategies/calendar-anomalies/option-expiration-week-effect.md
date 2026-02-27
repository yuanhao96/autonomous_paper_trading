# Option Expiration Week Effect

## Overview

Exploits the finding that large-cap stocks with actively traded options tend to have higher average weekly returns during option expiration weeks. Goes fully long OEF (S&P 100 ETF) on Monday of expiration weeks and liquidates on the expiration date itself.

## Academic Reference

- **Paper**: "Returns and Option Activity over the Option-Expiration Week for S&P 100 Stocks" — Chris & Licheng, Journal of Financial Economics
- Finding: Large-cap stocks with active options exhibit higher returns during expiration weeks.

## Strategy Logic

### Universe Selection

Single asset: OEF (S&P 100 Index ETF). The S&P 100 includes 102 leading US stocks with exchange-listed options, representing ~51% of US equity market capitalization.

### Signal Generation

Use TradingCalendar filtered by `TradingDayType.OPTION_EXPIRATION` to identify expiration dates. Calculate days remaining to nearest expiration.

### Entry / Exit Rules

- **Long**: Every Monday, if option expiration occurs within 5 days → 100% OEF.
- **Exit**: Liquidate on the expiration date itself.
- Binary: fully invested during expiration week, cash otherwise.

### Portfolio Construction

100% allocation to OEF during expiration weeks. Cash otherwise.

### Rebalancing Schedule

Weekly check every Monday at 10:00 AM via ScheduledEvent.

## Key Indicators / Metrics

- TradingCalendar: option expiration date detection
- Days to expiration (≤ 5 triggers entry)
- Option chain: strikes -3 to +3, 0–60 day expiration range

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2013 – 2018 |
| Benchmark | OEF |
| Initial Capital | $10,000 |
| Resolution | Minute |

## Data Requirements

- **Asset Classes**: US equity ETF (OEF)
- **Resolution**: Minute-level equity data
- **External Data**: Option chain data (strikes, expiration dates), trading calendar

## Implementation Notes

- TradingCalendar integration for precise expiration identification.
- Monday-scheduled event for weekly evaluation.
- `set_holdings()` for binary position management.
- Option chain filtering for expiration detection.
- Python on QuantConnect LEAN.

## Risk Considerations

- Single-asset concentration (OEF) — no diversification.
- Strategy is invested only during expiration weeks (~12 per year) — very low capital utilization.
- Gap risk around expiration dates as options are exercised/expired.
- Expiration week effect may be weakening as options markets become more efficient.
- No stop-loss or risk management mechanisms.
- Market regime changes post-2018 not tested.
- Small initial capital ($10,000) may not be representative.

## Related Strategies

- [Pre-Holiday Effect](pre-holiday-effect.md)
- [Turn of the Month in Equity Indexes](turn-of-the-month-in-equity-indexes.md)
- [Overnight Anomaly](overnight-anomaly.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/option-expiration-week-effect)
