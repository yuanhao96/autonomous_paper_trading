# 12 Month Cycle in Cross-Section of Stocks Returns

## Overview

Exploits the January Effect seasonal anomaly at the cross-sectional level. Ranks large-cap AMEX and NYSE stocks by their prior-year January return, then goes long the winner decile and shorts the loser decile. Monthly rebalancing with equal-weight long/short construction.

## Academic Reference

- **Paper**: Quantpedia — "12 Month Cycle in Cross-Section of Stocks Returns"
- Based on the hypothesis that prior-year January performance predicts current-year January returns.

## Strategy Logic

### Universe Selection

1. AMEX and NYSE stocks only.
2. Require fundamental data.
3. Top 30% by market capitalization (large-cap filter).
4. Market cap calculated from BasicAverageShares × BasicEPS × PERatio.

### Signal Generation

Compute prior-year January return using historical prices from 365 and 335 days ago. Rank stocks by this return and divide into 10 decile portfolios.

### Entry / Exit Rules

- **Long**: Stocks in the winner decile (highest prior January return).
- **Short**: Stocks in the loser decile (lowest prior January return).
- **Exit**: Full reconstitution at monthly rebalance.

### Portfolio Construction

Equal-weight: 1/(portfolio_size × 2) per position. Long-short with simultaneous opposing positions.

### Rebalancing Schedule

Monthly, at month start.

## Key Indicators / Metrics

- Prior-year January price return
- Market capitalization (size filter, top 30%)
- 365-day and 335-day price lookback

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2013 – Aug 2018 |
| Initial Capital | $100,000 |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: US equities (AMEX, NYSE)
- **Resolution**: Daily
- **Fundamental Data**: Market cap, EPS, P/E ratio, shares outstanding
- **Lookback**: 365 days (prior-year January)

## Implementation Notes

- CoarseSelectionFunction and FineSelectionFunction for universe filtering.
- Scheduled monthly rebalancing.
- Security initializer to avoid trading errors.
- Python on QuantConnect LEAN.

## Risk Considerations

- January anomaly is one of the most studied — may be significantly arbitraged away.
- Using a single month (January) from one year ago as the signal is extremely noisy.
- Large-cap filter (top 30%) may miss where the January effect is strongest (small-caps).
- Monthly rebalancing generates transaction costs on a relatively weak signal.
- Potential for margin calls from simultaneous long/short positions.
- Exchange restriction (AMEX/NYSE only) excludes NASDAQ stocks.

## Related Strategies

- [January Effect in Stocks](january-effect-in-stocks.md)
- [January Barometer](january-barometer.md)
- [Seasonality Effect Based on Same-Calendar Month Returns](seasonality-effect-same-calendar-month.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/12-month-cycle-in-cross-section-of-stocks-returns)
