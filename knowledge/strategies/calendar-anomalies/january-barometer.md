# January Barometer

## Overview

Uses January's S&P 500 return as a barometer for the full year. If January is positive, holds SPY for the remaining 11 months. If January is negative, switches to Treasury bills (BIL). Binary allocation: 100% equities or 100% T-bills based on a single monthly signal.

## Academic Reference

- **Paper**: Quantpedia — "January Barometer"
- Based on the calendar anomaly that January equity performance forecasts rest-of-year returns.

## Strategy Logic

### Universe Selection

Two assets: SPY (S&P 500 ETF) and BIL (Treasury Bills ETF).

### Signal Generation

Compute SPY's return over the month of January. Positive → bullish signal. Negative → bearish signal.

### Entry / Exit Rules

- **Month 1 (January)**: Buy SPY, record opening price.
- **Month 2 (February)**: Calculate January return.
  - If return > 0 → continue holding SPY for remaining 11 months.
  - If return < 0 → liquidate SPY, buy BIL for remaining 11 months.
- **Months 3–12**: Maintain position based on January result.

### Portfolio Construction

Binary: 100% SPY or 100% BIL. No partial allocation.

### Rebalancing Schedule

Annual. Decision made in February based on January performance. Scheduled event at month start of January.

## Key Indicators / Metrics

- January monthly return (SPY)
- Binary signal: positive/negative

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2008 – Aug 2018 |
| Initial Capital | $100,000 |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: US equity ETF (SPY) + Treasury ETF (BIL)
- **Resolution**: Daily
- **Lookback**: 1 month (January only)

## Implementation Notes

- Scheduled event triggers at month start of January.
- February evaluation: compare close vs. open price from January.
- `set_holdings()` for full allocation switches.
- Python on QuantConnect LEAN.

## Risk Considerations

- Binary allocation creates extreme concentration risk — no partial or defensive positioning.
- Single-month signal is inherently noisy — January return may not predict remaining 11 months.
- Misses intra-year regime changes — locked into position for 11 months.
- Treasury bills may significantly underperform during equity rallies following negative Januarys.
- Calendar anomalies lack guaranteed predictive power and may weaken over time.
- No stop-loss or drawdown management — fully exposed to market risk when holding SPY.

## Related Strategies

- [January Effect in Stocks](january-effect-in-stocks.md)
- [Turn of the Month in Equity Indexes](turn-of-the-month-in-equity-indexes.md)
- [Seasonality Effect Based on Same-Calendar Month Returns](seasonality-effect-same-calendar-month.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/january-barometer)
