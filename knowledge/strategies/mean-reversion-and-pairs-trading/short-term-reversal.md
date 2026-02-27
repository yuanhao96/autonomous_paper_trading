# Short Term Reversal

## Overview

Exploits mean reversion in US large-cap equities by going long the worst weekly performers and shorting the best weekly performers. Uses Rate of Change (ROC) over a 22-day lookback on the top 20 most liquid stocks, rebalancing weekly.

## Academic Reference

- **Paper**: Quantpedia — "Short Term Reversal in Stocks"

## Strategy Logic

### Universe Selection

1. All US equities priced above $4.
2. Top 100 by dollar volume.
3. Top 20 by market capitalization.

### Signal Generation

Rate of Change (ROC) indicator with 22-day lookback (approximately 1 month). Rank all 20 stocks by ROC.

### Entry / Exit Rules

- **Long**: 10 stocks with lowest ROC (worst performers).
- **Short**: 10 stocks with highest ROC (best performers).
- **Exit**: Positions held until next weekly rebalance (end-of-week expiry).

### Portfolio Construction

Equal-weight across all active positions. 50% long / 50% short. Market-neutral design.

### Rebalancing Schedule

Weekly, at market open.

## Key Indicators / Metrics

- Rate of Change (ROC): 22-day lookback
- Warm-up period: 23 days of historical data
- Dollar volume and market capitalization screens

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Mar 2023 – Mar 2024 |
| Initial Capital | $1,000,000 |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily
- **Lookback Period**: 22 trading days (ROC)
- **Warm-up**: 23 days

## Implementation Notes

- Three-module Python system: `universe.py` (selection), `alpha.py` (ROC signals), `main.py` (orchestration).
- `MostLiquidFundamentalUniverseSelectionModel` for universe.
- `ShortTermReversalAlphaModel` manages ROC indicators per security.
- Indicator reset on corporate actions (splits/dividends).
- NullRiskManagementModel, ImmediateExecutionModel.
- Python on QuantConnect LEAN.

## Risk Considerations

- Mean reversion assumption may fail during sustained trends.
- Equal-weighting 20 stocks across long/short can concentrate impact costs.
- Corporate action indicator resets may cause execution gaps.
- 22-day ROC may not capture true reversal patterns in all market regimes.
- Short availability assumed for all selected securities — not always realistic.
- No explicit stop-loss or volatility controls.

## Related Strategies

- [Short Term Reversal with Futures](short-term-reversal-with-futures.md)
- [Short-Term Reversal Strategy in Stocks](short-term-reversal-strategy-in-stocks.md)
- [Momentum - Short Term Reversal Strategy](../momentum/momentum-short-term-reversal-strategy.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/short-term-reversal)
