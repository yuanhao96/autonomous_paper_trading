# Momentum Effect in Stocks

## Overview

Exploits the momentum anomaly — the empirical observation that stocks with strong recent performance tend to continue outperforming peers in the near term. Stocks that outperform on a 3–12 month period tend to perform well in the future.

## Academic Reference

- **Paper**: "Momentum Effect in Stocks" — Quantpedia Screener #14
- **Link**: https://quantpedia.com/Screener/Details/14

## Strategy Logic

### Universe Selection

1. **Coarse filter**: Eliminate stocks trading below $5, exclude ETFs (no fundamental data), select top 100 securities by dollar volume.
2. **Fine filter**: Choose 50 largest companies by market capitalization.

### Signal Generation

Momentum calculated as percentage change over 252 trading days (12 months):

```
Momentum = (Close_t - Close_{t-252}) / Close_{t-252}
```

Uses LEAN's `MomentumPercent` indicator class, updated daily.

### Entry / Exit Rules

- **Entry**: Go long the top 5 stocks ranked by 12-month momentum.
- **Exit**: Liquidate positions for stocks no longer in the top 5 at rebalance.

### Portfolio Construction

Equal-weight allocation across 5 selected stocks (20% each).

### Rebalancing Schedule

Monthly. Tracks current month to trigger universe reselection; returns `Universe.UNCHANGED` on non-rebalance days.

## Key Indicators / Metrics

- **MomentumPercent**: 252-day lookback (12 months)
- Dollar volume (for universe filtering)
- Market capitalization (for fine selection)

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | Jul 2009 – Jul 2019 | SPY |
| Initial Capital | $100,000 | — |
| Resolution | Daily | — |

*(Detailed Sharpe/return metrics not disclosed in source.)*

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily
- **Lookback Period**: 252 trading days (12 months)
- **Fundamental Data**: Morningstar (market cap, dollar volume)

## Implementation Notes

- New symbols added to a momentum tracking dictionary with indicator warm-up via historical data requests.
- Positions liquidated for removed or non-selected symbols at each rebalance.
- Python implementation on QuantConnect LEAN engine.

## Risk Considerations

- Momentum crashes: strategy is vulnerable to sharp reversals (e.g., momentum crash of 2009).
- Concentrated portfolio (5 stocks) increases idiosyncratic risk.
- No short leg — long-only implementation misses the full momentum premium.
- Transaction costs from monthly rebalancing not explicitly modeled.

## Related Strategies

- [Momentum Effect in Stocks in Small Portfolios](momentum-effect-in-stocks-in-small-portfolios.md)
- [Price and Earnings Momentum](price-and-earnings-momentum.md)
- [Residual Momentum](residual-momentum.md)
- [Momentum and Style Rotation Effect](momentum-and-style-rotation-effect.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/momentum-effect-in-stocks)
