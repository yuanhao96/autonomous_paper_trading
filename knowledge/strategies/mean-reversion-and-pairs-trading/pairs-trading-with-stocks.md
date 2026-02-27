# Pairs Trading with Stocks

## Overview

Distance-based pairs trading on 34 financial and technology sector stocks. Normalizes prices over a 1-year formation period, selects the 4 closest pairs by sum of squared deviations, and trades when spreads diverge by 2 standard deviations. Pairs reselected semi-annually.

## Academic Reference

- **Paper**: Quantpedia — "Pairs Trading with Stocks"
- **Source**: quantpedia.com/Screener/Details/12

## Strategy Logic

### Universe Selection

34 stocks across financial and technology sectors: XLK, QQQ, BANC, BBVA, BBD, BCH, BLX, BSBR, BSAC, SAN, CIB, BXS, BAC, BOH, BMO, BK, BNS, BKU, BBT, NBHC, OFG, BFR, CM, COF, C, VLY, WFC, WAL, WBK, RBS, SHG, STT, STL, SCNB, SMFG.

### Signal Generation

**Formation period (252 trading days)**:
1. Normalize prices to $1 at period start.
2. Calculate distance: D = Σ[(x_i/x_1) − (y_i/y_1)]² for all pairs.
3. Select top 4 pairs with smallest distances.

**Trading period**:
Monitor spread between each pair.

### Entry / Exit Rules

- **Enter**: When spread diverges by 2 standard deviations from the mean (long the underperformer, short the outperformer).
- **Exit**: When prices revert toward historical relationship.

### Portfolio Construction

Equal-weight. 0.1 allocation per pair (reduced from original to avoid margin calls). Maximum 4 concurrent pair positions.

### Rebalancing Schedule

Semi-annual pair reselection. Daily trade signal evaluation.

## Key Indicators / Metrics

- Normalized price spread
- Sum of squared deviations (distance metric)
- Mean and standard deviation of historical price spreads
- 2σ divergence threshold
- Formation period: 252 days
- Trading period: 6 months

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2014 – 2018 |
| Initial Capital | $100,000 |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: US equities (financial + tech sectors)
- **Resolution**: Daily
- **Lookback Period**: 252 trading days (1-year formation)
- **Trading Period**: 6 months per cycle

## Implementation Notes

- History requests for formation period data.
- Normalized price deques for rolling calculations.
- Numpy array operations for distance computation.
- Scheduled events for semi-annual pair reselection.
- Position sizing reduced to 0.1 per pair to avoid margin calls.
- Python on QuantConnect LEAN.

## Risk Considerations

- "A temporary shock could move one stock out of the common price band" — pairs may permanently diverge.
- Structural market changes can break historical correlations.
- Financial sector concentration increases systemic risk exposure.
- Semi-annual pair reselection is slow — relationships may decay within 6 months.
- 2σ threshold is arbitrary — may be too tight or too loose for different pairs.
- Small universe (34 stocks) limits pair selection quality.
- Short availability and borrowing costs not modeled.

## Related Strategies

- [Pairs Trading with Country ETFs](pairs-trading-with-country-etfs.md)
- [Pairs Trading - Copula vs Cointegration](pairs-trading-copula-vs-cointegration.md)
- [Optimal Pairs Trading](optimal-pairs-trading.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/pairs-trading-with-stocks)
