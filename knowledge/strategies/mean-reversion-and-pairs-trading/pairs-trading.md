# Pairs Trading

## Overview

A market-neutral strategy that identifies two co-moving securities, goes long the underperformer and short the outperformer when their spread deviates from its historical mean, profiting from the spread's reversion. Pairs trading captures relative value while hedging systematic risk.

## Academic Reference

- **Paper**: "Pairs Trading: Performance of a Relative Value Arbitrage Rule", Gatev, Goetzmann, Rouwenhorst (2006)
- **Link**: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=141615

## Strategy Logic

### Universe Selection

Stocks within the same sector or ETFs tracking related indices. Pairs selected based on cointegration tests or minimum-distance methods over a formation period.

### Signal Generation

Compute the spread between the two securities and its z-score:

```
Spread = Price_A - beta * Price_B
Z-Score = (Spread - Mean(Spread, lookback)) / StdDev(Spread, lookback)
```

### Entry / Exit Rules

- **Entry**: Go long the underperformer and short the outperformer when |z-score| > entry_z (typically 2.0).
- **Exit**: Close both legs when |z-score| < exit_z (typically 0.5) or reverts to mean.
- **Stop-loss**: Close if z-score exceeds a maximum threshold (e.g., 4.0) indicating breakdown.

### Portfolio Construction

Dollar-neutral: equal dollar exposure on long and short legs. Beta-adjusted for imperfect hedges.

### Rebalancing Schedule

Daily monitoring, with trades triggered by z-score crossings.

## Key Indicators / Metrics

- **Lookback period**: 60 days (configurable, range 20–120)
- **Entry z-score**: 2.0 (configurable, range 1.5–3.0)
- **Exit z-score**: 0.5 (configurable, range 0.0–1.0)
- **Cointegration test**: Engle-Granger or Johansen

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | 1962–2002 | Market-neutral |
| Annual Return | ~11% | — |
| Sharpe Ratio | ~0.6–1.0 | — |
| Max Drawdown | ~15% | — |

## Data Requirements

- **Asset Classes**: US equities (same sector pairs), ETFs
- **Resolution**: Daily
- **Lookback Period**: 60–120 trading days for spread estimation

## Implementation Notes

- Formation period (6–12 months) to identify cointegrated pairs, then trading period.
- Implementation simplified to long-only for our pipeline — go long the underperformer when z-score is very negative.
- Hedge ratio (beta) can be estimated via OLS regression or Kalman filter.

## Risk Considerations

- Pair relationships can break down permanently (structural breaks).
- Convergence not guaranteed — spread may diverge further before reverting.
- Short-selling constraints and borrowing costs reduce profitability.
- Crowding risk — popular pairs may have compressed returns.

## Related Strategies

- [Pairs Trading with Stocks](pairs-trading-with-stocks.md)
- [Mean Reversion Statistical Arbitrage in Stocks](mean-reversion-statistical-arbitrage-in-stocks.md)
- [Optimal Pairs Trading](optimal-pairs-trading.md)
- [Pairs Trading Copula vs Cointegration](pairs-trading-copula-vs-cointegration.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/pairs-trading)
