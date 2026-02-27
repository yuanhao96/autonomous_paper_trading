# G-Score Investing

## Overview

Applies Mohanram's G-Score — a 7-factor fundamental scoring system — to select technology stocks with strong growth characteristics. Awards one point per factor (0–7 scale) and goes long stocks scoring ≥ 5. Benchmarked against QQQ (Nasdaq-100).

## Academic Reference

- **Paper**: "Separating Winners from Losers Among Low Book-to-Market Stocks Using Financial Statement Analysis" — Mohanram (April 2004)

## Strategy Logic

### Universe Selection

1. Low book-to-market stocks (bottom quartile by P/B).
2. Technology sector only.
3. Fundamental data from MorningStar.

### Signal Generation

**G-Score (0–7)** — award 1 point for each condition met:

1. **ROA > Industry Median**: 1-year return on assets exceeds tech sector median.
2. **CFROA > Industry Median**: Cash flow return on assets exceeds peer median.
3. **CFROA > ROA**: Cash generation efficiency surpasses profitability ratio.
4. **Low ROA Variance**: Earnings stability below industry median variance.
5. **R&D Spending > Median**: Research expenditure exceeds sector median.
6. **CapEx > Median**: Capital expenditure exceeds sector median.
7. **Ad Spending > Median**: SG&A expenses exceed peer median.

### Entry / Exit Rules

- **Long**: Stocks with G-Score ≥ 5.
- **Exit**: At quarterly rebalance when G-Score drops below 5.
- No short positions.

### Portfolio Construction

Equal-weight across selected securities. Constant alpha model with 31-day insight duration.

### Rebalancing Schedule

Quarterly, in April following fiscal year-end.

## Key Indicators / Metrics

- G-Score (0–7 composite)
- Return on Assets (1-year and 3-year)
- Cash Flow Return on Assets
- R&D, CapEx, and SG&A spending ratios
- ROA variance (12 quarters rolling)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Apr 2016 – Sep 2020 |
| Sharpe Ratio | 0.609 |
| Benchmark | QQQ (Sharpe: 1.002) |
| Result | Underperformed QQQ |

## Data Requirements

- **Asset Classes**: US equities (technology sector)
- **Resolution**: Daily
- **Fundamental Data**: Net tangible assets, market cap, ROA (1-year, 3-year), operating cash flow, total assets, R&D, CapEx, SG&A
- **Warm-up**: 3 years (for historical ROA variance)

## Implementation Notes

- 3-year warm-up period for ROA variance computation.
- Rolling windows of 12 quarters for ROA variance.
- NaN checks for deterministic results.
- Object store persistence for live trading continuity.
- Python on QuantConnect LEAN.

## Risk Considerations

- Underperformed passive QQQ during 2016–2020 — strong tech bull market favored growth over fundamentals.
- Technology sector concentration increases cyclical exposure.
- G-Score factors are backward-looking (trailing financials) — may lag fast-moving tech dynamics.
- Quarterly rebalancing is relatively slow for the tech sector.
- 7-factor model increases complexity and potential for data errors.
- Small universe (low B/M tech stocks) limits diversification.

## Related Strategies

- [Stock Selection Based on Fundamental Factors](stock-selection-based-on-fundamental-factors.md)
- [Price Earnings Anomaly](price-earnings-anomaly.md)
- [Earnings Quality Factor](../factor-investing/earnings-quality-factor.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/g-score-investing)
