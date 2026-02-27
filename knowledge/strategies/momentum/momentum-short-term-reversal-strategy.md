# Momentum - Short Term Reversal Strategy

## Overview

Combines momentum analysis with mean-reversion principles to avoid stocks in final overreaction stages. Uses the Geometric Average Rate of Return (GARR) ratio to distinguish between stocks with sustainable momentum and those likely to reverse.

## Academic Reference

- **Paper**: "Momentum - Short Term Reversal Strategy" — Quantpedia Premium

## Strategy Logic

### Universe Selection

All NYSE and NASDAQ equities priced above $10. Minimum 50 stocks with 12-month price history.

### Signal Generation

**Step 1 — 12-month return ranking**:
- Top 30%: Winner group
- Bottom 30%: Loser group
- Middle 40%: Excluded

**Step 2 — GARR Ratio** (identifies overreaction):
```
GARR_n = ∏(1 + r_i)^(1/n) - 1
GARR_Ratio = GARR_1month / GARR_12month
```

Low GARR ratio in winners → sustainable momentum (not overreacting).
High GARR ratio in losers → overreacting to the downside (short candidates).

### Entry / Exit Rules

- **Long**: 13–15 "Decrease-Return Winners" (winners with lowest GARR ratios).
- **Short**: 15 "Increase-Return Losers" (losers with highest GARR ratios).
- **Exit**: At monthly rebalance when stocks leave selection.

### Portfolio Construction

Equal-weight: 50% long / 50% short. Per-stock weight = 0.5 / N.

### Rebalancing Schedule

Monthly, at month start. 365-day warm-up before trading begins.

## Key Indicators / Metrics

- 12-month total return
- GARR (1-month and 12-month)
- GARR ratio
- RollingWindow of 13 monthly prices

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2010 – May 2018 |
| Initial Capital | $100,000 |
| Resolution | Daily |
| Warm-up | 365 days |

## Data Requirements

- **Asset Classes**: US equities (NYSE, NASDAQ)
- **Resolution**: Daily
- **Lookback Period**: 12 months + 1 month
- **Price Filter**: > $10

## Implementation Notes

- `SymbolData` class: RollingWindow of 13 monthly prices, computes yearly_return and garr_ratio.
- Coarse selection filters by fundamental data.
- Fine selection validates tradability.
- Updated version: 0.25 exposure per side (from 0.5) to avoid margin calls.
- Python on QuantConnect LEAN.

## Risk Considerations

- GARR ratio effectiveness may vary with market volatility regime.
- $10 price filter excludes many small-caps where momentum is strongest.
- Survivorship bias from using available historical data.
- Monthly turnover creates transaction friction.
- 12-month history requirement limits universe, especially for newer listings.
- The "overreaction" thesis is behavioral — may weaken as markets become more efficient.

## Related Strategies

- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)
- [Residual Momentum](residual-momentum.md)
- [Short Term Reversal](../mean-reversion-and-pairs-trading/short-term-reversal.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/momentum-short-term-reversal-strategy)
