# Lunar Cycle in Equity Market

## Overview

Trades emerging market equities (EEM) based on lunar phase cycles. Goes long 7 days before each new moon (during Last Quarter phase) and short 7 days before each full moon (during First Quarter phase). Based on research showing lunar cycle effects are strongest in emerging markets.

## Academic Reference

- **Paper**: Quantpedia Premium — "Lunar Cycle in Equity Market"
- Effect is "strongest in emerging markets."

## Strategy Logic

### Universe Selection

Single asset: EEM (iShares MSCI Emerging Markets Index ETF).

### Signal Generation

Lunar phase data sourced from United States Naval Observatory (USNO) via CSV. Four phases:
- New Moon (0)
- First Quarter (1)
- Full Moon (2)
- Last Quarter (3)

### Entry / Exit Rules

- **Long**: Enter when Last Quarter phase detected (phase = 3) → 7 days before new moon.
- **Short**: Enter when First Quarter phase detected (phase = 1) → 7 days before full moon.
- **Exit**: Position reverses at next signal.

### Portfolio Construction

100% allocation to EEM (long or short).

### Rebalancing Schedule

Daily monitoring via `on_data()`. Position adjusts when phase conditions are met. Lunar cycle ≈ 29.5 days.

## Key Indicators / Metrics

- Lunar phase (0–3 from USNO data)
- ~29.5-day cycle period
- Phase-based entry timing (7 days before new/full moon)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2004 – Aug 2018 |
| Initial Capital | $100,000 |
| Asset | EEM |

## Data Requirements

- **Asset Classes**: Emerging market ETF (EEM)
- **Resolution**: Daily
- **External Data**: Lunar phase calendar CSV (USNO)

## Implementation Notes

- Custom `MoonPhase` class extends PythonData for CSV parsing.
- Reads Dropbox-hosted CSV file with lunar phase data.
- Converts string phase names to numerical values (0–3).
- Daily `on_data()` checks for phase conditions.
- Python on QuantConnect LEAN.

## Risk Considerations

- Lunar cycle effects are highly controversial — limited academic consensus.
- Single-asset (EEM) strategy with no diversification.
- Emerging market ETFs have higher volatility, wider spreads, and political risk.
- External data dependency (USNO CSV hosted on Dropbox) is fragile.
- Short positions on EEM carry significant risk during emerging market rallies.
- No stop-loss, risk management, or position sizing adjustments.
- Backtest period may include favorable conditions not representative of future performance.

## Related Strategies

- [Overnight Anomaly](overnight-anomaly.md)
- [Seasonality Effect Based on Same-Calendar Month Returns](seasonality-effect-same-calendar-month.md)
- [Pre-Holiday Effect](pre-holiday-effect.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/lunar-cycle-in-equity-market)
