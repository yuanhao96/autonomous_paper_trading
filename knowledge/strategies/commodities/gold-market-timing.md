# Gold Market Timing

## Overview

Times gold exposure using the Fed Model framework. Buys gold when the S&P 500 earnings yield exceeds the 10-year Treasury yield by a ratio of at least 2× (indicating stocks are undervalued and gold serves as a hedge). Allocates 90% to gold with monthly rebalancing.

## Academic Reference

- **Paper**: Quantpedia Premium — "Gold Market Timing"
- Based on the Fed Model: "If the forward earnings yield of the S&P 500 is higher than the 10-year government bond yield, stocks are undervalued and vice versa."

## Strategy Logic

### Universe Selection

- Gold: WGC/GOLD_DAILY_USD (via Nasdaq Data Link).
- Signal inputs: S&P 500 earnings yield, 10-year US Treasury yield.

### Signal Generation

Fed Model ratio: Earnings Yield / Bond Yield.

### Entry / Exit Rules

- **Long gold**: Earnings yield > bond yield AND ratio ≥ 2.0.
- **Exit**: Liquidate when conditions no longer met.

### Portfolio Construction

90% gold allocation when signal active. 10% cash buffer.

### Rebalancing Schedule

Monthly, first trading day.

## Key Indicators / Metrics

- S&P 500 trailing 12-month earnings yield
- 10-year US Treasury yield
- Earnings yield / bond yield ratio (threshold: 2.0)
- Gold price (daily, USD/troy oz)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2010 – 2015 |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: Gold
- **Resolution**: Daily
- **External Data**: Bond yield (US Treasury curve), earnings yield (MULTPL), gold price (WGC)
- **Warm-up**: 30 days

## Implementation Notes

- Custom charting: plots earnings yield vs. bond yield relationship.
- 30-day warm-up ensures latest bond yield available before first trade.
- Python on QuantConnect LEAN.

## Risk Considerations

- **Critical**: Datasets discontinued by Nasdaq Data Link — live implementation requires alternative data sources.
- Single-signal dependency (Fed Model) — one indicator drives all allocation decisions.
- 90% gold allocation creates substantial concentration and drawdown risk.
- Fed Model has mixed academic support — its predictive power is debated.
- Gold has "low or negative correlation to other asset classes" — but this can change.
- Monthly rebalancing may miss intra-month regime changes.
- No stop-loss or risk management mechanisms.

## Related Strategies

- [Can Crude Oil Predict Equity Returns](can-crude-oil-predict-equity-returns.md)
- [Trading with WTI BRENT Spread](trading-with-wti-brent-spread.md)
- [VIX Predicts Stock Index Returns](../volatility-and-options/vix-predicts-stock-index-returns.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/gold-market-timing)
