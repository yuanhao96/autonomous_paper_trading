# Stock Selection Strategy Based on Fundamental Factors

## Overview

Multi-factor stock selection model that ranks stocks across four fundamental metrics — FCF Yield, 1-month price change, book value per share, and revenue growth. Divides the universe into quintile portfolios and goes long the top 10 stocks from the highest-ranked quintile with monthly rebalancing.

## Academic Reference

- **Paper**: "Factor Based Stock Selection Model for Turkish Equities" — Ayhan Yüksel (2015)

## Strategy Logic

### Universe Selection

1. All US equities with fundamental data (MorningStar).
2. Filter to top 300 by daily dollar volume.
3. Exclude stocks with missing factor data.

### Signal Generation

**Four factors**, each ranked across the 300-stock universe:

1. **FCF Yield**: Free cash flow productivity (higher = better).
2. **Price Change 1M**: 1-month momentum (inverse ranking — lower recent return preferred).
3. **Book Value Per Share**: Asset backing (higher = better).
4. **Revenue Growth**: Earnings trajectory (higher = better).

**Quintile scoring**: For each factor, stocks are placed into 5 quintile portfolios (P1–P5). P1 = most preferred. Composite score averages quintile ranks across all four factors.

### Entry / Exit Rules

- **Long**: Top 10 stocks by composite score.
- **Exit**: Full portfolio turnover at monthly rebalance.
- No short positions.

### Portfolio Construction

Equal-weight: 10% allocation per stock. Monthly reconstitution eliminates stale positions.

### Rebalancing Schedule

Monthly, at the first trading day of each month.

## Key Indicators / Metrics

- FCF Yield
- 1-month price change (momentum)
- Book Value Per Share
- Revenue Growth
- Quintile composite score

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2009 – May 2017 |
| Factor Correlation Range | -0.987 to 0.939 |
| Win Probability | 63%–72% |
| Excess Returns (top quintile) | 0.21–0.41 annually |
| Bottom Quintile Loss | 0.04–0.06 annually |

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily
- **Fundamental Data**: FCF yield, book value per share, revenue growth, daily dollar volume
- **Price Data**: 20-day trailing prices for monthly return computation
- **Lookback**: 1 month (momentum factor)

## Implementation Notes

- Universe refreshed monthly (not daily) to reduce computation.
- Flag variables control coarse/fine selection staging.
- History API retrieves 20-day trailing prices.
- NumPy/Pandas for factor calculations and correlation analysis.
- Python on QuantConnect LEAN.

## Risk Considerations

- Factor mean reversion risk — factors that worked historically may underperform in changing regimes.
- Monthly turnover generates significant transaction costs not accounted for in backtest.
- 10-stock portfolio is highly concentrated — idiosyncratic risk dominates.
- Dollar volume filter limits universe to larger, more liquid stocks — misses small-cap value.
- Single-country (US equities) concentration.
- Survivorship bias in historical fundamental data.
- Inverse momentum (1M price change) conflicts with traditional momentum literature.

## Related Strategies

- [Fundamental Factor Long Short Strategy](fundamental-factor-long-short-strategy.md)
- [Fama-French Five Factors](../factor-investing/fama-french-five-factors.md)
- [G-Score Investing](g-score-investing.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/stock-selection-strategy-based-on-fundamental-factors)
