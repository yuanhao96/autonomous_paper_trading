# Momentum Effect in Country Equity Indexes

## Overview

Tests the momentum effect across 35 country equity index ETFs, demonstrating that momentum effects exist in country indices. The strategy outperformed an equal-weighted portfolio by approximately 90% per annum over a 22-year period.

## Academic Reference

- **Paper**: "Momentum Effect in Country Equity Indexes" — Quantpedia Screener

## Strategy Logic

### Universe Selection

35 country index ETFs (fixed universe):
- EWJ, EZU, EFNL, EWW, ERUS, IVV, EWQ, EWH, EWY, EWP, EWD, EWL, GXC, EWC, EWZ, and 20 others covering developed and emerging markets.

### Signal Generation

MomentumPercent indicator with 6-month lookback (126 trading days):
```
MOMP = (Price_t - Price_{t-126}) / Price_{t-126}
```
Updated daily with automatic resolution.

### Entry / Exit Rules

- **Long**: Top 5 ETFs by 6-month momentum. Equal-weight positions.
- **Exit**: ETFs no longer in top 5 are liquidated at monthly rebalance.

### Portfolio Construction

Equal weight across 5 selected ETFs (20% each). Fully invested (no cash component).

### Rebalancing Schedule

Monthly, at month start via Scheduled Events API.

## Key Indicators / Metrics

- MomentumPercent (MOMP): 126-day lookback (6 months)
- Warm-up period: 126 days

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2002–2022 (22 years) |
| Initial Capital | $100,000 |
| Outperformance | ~90% per annum vs. equal-weighted portfolio |

## Data Requirements

- **Asset Classes**: International equity ETFs (35 country indexes)
- **Resolution**: Daily OHLCV
- **Lookback Period**: 126 trading days (6 months)

## Implementation Notes

- `CountryEquityIndexesMomentumAlgorithm` class with `initialize()` and `_rebalance()`.
- Dictionary `self._data` maintains indicator objects per symbol.
- Warm-up period matches momentum lookback (126 days).
- Python implementation on QuantConnect LEAN.

## Risk Considerations

- **Survivorship bias**: Historical analysis may not capture delisted ETFs.
- **Trading costs**: Not explicitly modeled; monthly rebalancing of 35-symbol universe.
- **Regime dependency**: 2002–2022 performance may not persist.
- **Liquidity**: No discussion of ETF trading volume or bid-ask spreads.
- **Data gaps**: Some ETFs have limited history before 2002.
- **Country risk**: Concentrated exposure to individual country events.
- **6-month lookback** is shorter than typical 12-month momentum — may be noisier.

## Related Strategies

- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)
- [Asset Class Momentum](asset-class-momentum.md)
- [Mean Reversion Effect in Country Equity Indexes](../mean-reversion-and-pairs-trading/mean-reversion-effect-in-country-equity-indexes.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/momentum-effect-in-country-equity-indexes)
