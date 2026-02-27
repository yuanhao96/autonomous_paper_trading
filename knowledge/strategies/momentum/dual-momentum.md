# Dual Momentum

## Overview

Combines relative (cross-sectional) momentum with absolute (time-series) momentum. First, rank assets by relative performance to select the best performers, then apply an absolute momentum filter — only invest when the selected asset's trailing return exceeds a risk-free benchmark (e.g., T-bills).

## Academic Reference

- **Paper**: "Dual Momentum Investing", Gary Antonacci (2014)
- **Link**: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2042750

## Strategy Logic

### Universe Selection

Two or more asset classes (e.g., US equities via SPY, international equities via EFA, bonds via AGG).

### Signal Generation

1. **Relative momentum**: Compare trailing returns across assets over lookback period (typically 12 months). Select the asset with the highest return.
2. **Absolute momentum**: Check if the selected asset's return exceeds T-bill returns. If not, allocate to bonds or cash.

### Entry / Exit Rules

- **Entry**: Go long the top-ranked asset if it passes the absolute momentum filter.
- **Exit**: Switch to bonds/cash when absolute momentum is negative.

### Portfolio Construction

100% allocation to the single selected asset (concentrated).

### Rebalancing Schedule

Monthly.

## Key Indicators / Metrics

- **Lookback period**: 252 days (12 months)
- **Relative momentum**: Cross-sectional ranking by trailing return
- **Absolute momentum**: Trailing return vs risk-free rate

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | 1974–2013 | 60/40 portfolio |
| Annual Return | ~15% | ~9% |
| Sharpe Ratio | ~0.9 | ~0.5 |
| Max Drawdown | ~20% | ~45% |

## Data Requirements

- **Asset Classes**: Multi-asset (equities, bonds, international)
- **Resolution**: Daily or monthly
- **Lookback Period**: 252 trading days

## Implementation Notes

- Simple to implement — requires only price data for 2-3 ETFs.
- The absolute momentum filter acts as a crash protection mechanism.
- Can be extended with more asset classes for diversification.

## Risk Considerations

- Single-asset concentration risk at any given time.
- Lookback period sensitivity — whipsaw during regime transitions.
- Monthly rebalancing may miss rapid market shifts.
- Performance degrades in trendless markets.

## Related Strategies

- [Time-Series Momentum](time-series-momentum.md)
- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)
- [Asset Class Momentum](asset-class-momentum.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/dual-momentum)
