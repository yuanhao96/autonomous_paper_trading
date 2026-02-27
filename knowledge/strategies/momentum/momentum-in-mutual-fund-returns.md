# Momentum in Mutual Fund Returns

## Overview

Uses two factors — historical returns (rate of change) and nearness to historical high (NAV proximity) — from asset management firms to construct a balanced long-short portfolio. Research suggests momentum persistence in mutual funds may stem from investor herding, macroeconomic variables, and anchoring bias.

## Academic Reference

- **Paper**: Sapp (2010) — loosely based on research about mutual fund return persistence
- **Key Finding**: Historical returns and nearness of NAV to previous high provide significant predictive power about future fund returns.

## Strategy Logic

### Universe Selection

US securities in the asset management industry, filtered using `MorningstarIndustryCode.AssetManagement`.

### Signal Generation

Two factors combined:

1. **Rate of Change (ROC)**: Performance over configurable lookback (default 6 months).
2. **Nearness**: How close the closing price is to its maximum price over a separate lookback (default 12 months).

```
Nearness = Close / Max(Close, 12-month window)
```

Securities ranked by combined ROC and Nearness scores.

### Entry / Exit Rules

- **Long**: Top-ranked securities by combined score.
- **Short**: Bottom-ranked securities by combined score.
- **Exit**: Positions liquidate when all related insights expire (default 6-month holding period).

### Portfolio Construction

Net Direction Weighted Portfolio Construction Model — allocates capital based on aggregate insight direction by symbol. Default 25% allocation for long/short positions.

### Rebalancing Schedule

Monthly.

## Key Indicators / Metrics

- Rate of Change (6-month lookback)
- Nearness to 12-month high
- Combined ranking score

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2015 – Aug 2020 |
| Initial Capital | $1,000,000 |

**Note**: The strategy does not consistently outperform the benchmark according to the authors.

## Data Requirements

- **Asset Classes**: US equities (asset management sector)
- **Resolution**: Daily
- **Lookback Period**: 13 months minimum (12-month nearness + buffer)
- **Fundamental Data**: Morningstar industry classification

## Implementation Notes

- Uses Morningstar's industry code filter to identify asset management firms as proxies for mutual fund performance.
- Net Direction Weighted PCM handles position sizing based on insight aggregation.
- Configurable parameters: ROC lookback, nearness lookback, holding period, allocation percentages.

## Risk Considerations

- Strategy does not consistently outperform the benchmark.
- Using asset management firm stock prices as proxies for mutual fund NAV introduces tracking error.
- Sector concentration risk (all positions in asset management).
- Anchoring bias (nearness factor) may be regime-dependent.

## Related Strategies

- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)
- [Momentum and Style Rotation Effect](momentum-and-style-rotation-effect.md)
- [Asset Class Momentum](asset-class-momentum.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/momentum-in-mutual-fund-returns)
