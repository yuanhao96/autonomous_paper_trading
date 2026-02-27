# Can Crude Oil Predict Equity Returns

## Overview

Tests whether prior-month crude oil returns can predict next-month equity returns using OLS regression. Goes long SPY when predicted equity return exceeds the risk-free rate, otherwise exits to cash. 24-month rolling regression window with monthly rebalancing. Based on the "Striking Oil" paper.

## Academic Reference

- **Paper**: "Striking Oil: Another Puzzle?" — Gerben Driesprong, Ben Jacobsen & Benjamin Maat (2007)

## Strategy Logic

### Universe Selection

- Primary: SPY (S&P 500 ETF).
- Signal: S&P GSCI Crude Oil Total Return Index (Nasdaq Data Link).
- Alternative: Short-term US Treasury bills.

### Signal Generation

OLS regression: Monthly stock returns = α + β × (prior month oil returns) + ε.

24-month rolling lookback window, refreshed monthly.

### Entry / Exit Rules

- **Long SPY**: Predicted equity return > risk-free rate.
- **Exit**: If predicted return ≤ risk-free rate (intended to buy T-bills, but not implemented).
- Binary: fully invested or fully out.

### Portfolio Construction

100% SPY or 100% cash. No partial allocation.

### Rebalancing Schedule

Monthly, at month start.

## Key Indicators / Metrics

- Pearson correlation (oil vs. stock returns)
- OLS regression p-values
- Beta and alpha coefficients
- 24-month rolling window
- Risk-free rate (Treasury bill rates)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2010 – 2017 |
| Sharpe Ratio | 0.726 |
| Benchmark (SPY) Sharpe | 0.735 |
| Total Trades | 9 |
| Market Exposure | Predominantly long (bull market) |

## Data Requirements

- **Asset Classes**: US equity ETF (SPY) + crude oil index
- **Resolution**: Daily
- **External Data**: OPEC/ORB crude oil prices (Nasdaq Data Link), US Treasury bill rates
- **Lookback**: 24 months

## Implementation Notes

- History function for data retrieval.
- NumPy for regression calculations.
- Scheduled events for monthly automation.
- Securities pricing API for T-bill rates.
- Python on QuantConnect LEAN.

## Risk Considerations

- Oil-equity correlation has "significantly weakened since the 1980s" — predictive power is declining.
- Most monthly regressions show p-values too high to reject null hypothesis of zero correlation.
- **Critical**: Nasdaq Data Link datasets have been discontinued.
- Only 9 trades over 9 years — predominantly long due to bull market, masking strategy's true predictive power.
- Cannot actually purchase T-bills in the implementation — cash alternative is imperfect.
- Binary allocation (100% SPY or 0%) creates concentration risk.
- Bull market bias (2010–2017) makes it impossible to evaluate downside protection.

## Related Strategies

- [Gold Market Timing](gold-market-timing.md)
- [Trading with WTI BRENT Spread](trading-with-wti-brent-spread.md)
- [Momentum Effect in Commodities Futures](../momentum/momentum-effect-in-commodities-futures.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/can-crude-oil-predict-equity-returns)
