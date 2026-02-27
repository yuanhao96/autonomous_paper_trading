# Sentiment and Style Rotation Effect in Stocks

## Overview

Exploits the relationship between investor sentiment and equity style performance. Rotates between value and growth stocks based on VIX and put-call ratio signals. When sentiment signals conflict, it indicates value outperformance; when both show fear, value underperforms.

## Academic Reference

- **Paper**: "When Do Value Stocks Outperform Growth Stocks?: Investor Sentiment and Equity Style Rotation Strategies" — Lee and Song

## Strategy Logic

### Universe Selection

1. All NYSE and NASDAQ stocks.
2. Sort into deciles by market capitalization; keep top 3 (large-cap only).
3. Require positive earnings, valid P/E and P/B ratios.

### Signal Generation

**Two sentiment indicators**:

1. **VIX Index**: Implied 30-day S&P 500 volatility (Quandl data).
2. **CBOE Put-Call Ratio**: Put volume / call volume (CBOE data).

Both converted to 1-month and 6-month rolling averages.

**Style portfolios**:
- **Value**: Lowest P/B quintile within each of top 3 size deciles.
- **Growth**: Highest P/B quintile within each of top 3 size deciles.

### Entry / Exit Rules

| 1-month VIX vs 6-month | 1-month PCR vs 6-month | Action |
|-------------------------|------------------------|--------|
| VIX ↑ (above 6m avg) | PCR ↓ (below 6m avg) | **Long value** |
| VIX ↑ | PCR ↑ | **Short value** |
| VIX ↓ | Any | **Long both** (neutral) |

### Portfolio Construction

Equal-weight within selected positions. Quarterly rebalancing (3-month holding periods). Monthly universe updates.

### Rebalancing Schedule

Quarterly.

## Key Indicators / Metrics

- VIX (1-month and 6-month rolling averages)
- CBOE Put-Call Ratio (1-month and 6-month rolling averages)
- Price-to-Book ratio (style classification)
- Market capitalization (size filter)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2010 – Jul 2018 |
| Initial Capital | $10,000,000 |

## Data Requirements

- **Asset Classes**: US equities (NYSE, NASDAQ)
- **Resolution**: Daily
- **External Data**: VIX (Quandl), CBOE Put-Call Ratio
- **Fundamental Data**: Market cap, P/E, P/B, earnings

## Implementation Notes

- Security initializer prevents trading errors.
- Asset filter ensures tradability before entry.
- Automatic liquidation for positions outside current selection.
- Large initial capital ($10M) for adequate diversification across style portfolios.

## Risk Considerations

- Sentiment indicators (VIX, PCR) are noisy — signals may whipsaw.
- Quarterly rebalancing may miss rapid sentiment shifts.
- Style definitions (P/B quintiles) are static — may not capture evolving market dynamics.
- External data dependencies (Quandl, CBOE) add fragility.
- Large-cap only — misses small/mid-cap value premium.
- Complex signal logic with multiple conditions increases overfitting risk.

## Related Strategies

- [Momentum and Style Rotation Effect](momentum-and-style-rotation-effect.md)
- [VIX Predicts Stock Index Returns](../volatility-and-options/vix-predicts-stock-index-returns.md)
- [Value Effect within Countries](../value-and-fundamental/value-effect-within-countries.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/sentiment-and-style-rotation-effect-in-stocks)
