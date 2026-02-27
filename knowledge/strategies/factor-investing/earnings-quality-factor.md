# Earnings Quality Factor

## Overview

Constructs a composite earnings quality score from four fundamental factors — Accruals Ratio, Cash Flow to Assets, Return on Equity, and Debt-to-Assets — to identify firms with sustainable, high-quality earnings. Stocks with the highest composite quality scores tend to outperform those with the lowest scores, capturing a broad quality premium that is more robust than any single factor alone.

## Academic Reference

- **Paper**: "Earnings Quality Factor" — Quantpedia Screener
- **Link**: https://quantpedia.com/

## Strategy Logic

### Universe Selection

1. Select all common stocks listed on major US exchanges.
2. Exclude financial companies to avoid distortions from leverage-dependent business models where high debt and different accrual dynamics are structural features rather than quality signals.
3. Require sufficient fundamental data to compute all four component factors.

### Signal Generation

Each stock is scored on four fundamental factors:

1. **Accruals Ratio**: Balance sheet accruals scaled by total assets (lower is better).
2. **Cash Flow to Assets**: Operating cash flow divided by total assets (higher is better).
3. **Return on Equity (ROE)**: Net income divided by shareholders' equity (higher is better).
4. **Debt-to-Assets**: Total debt divided by total assets (lower is better).

```
Composite Score = Rank(Accruals, ascending) + Rank(CF/Assets, descending) + Rank(ROE, descending) + Rank(Debt/Assets, ascending)
```

Each factor is ranked cross-sectionally, and the sum of ranks produces the composite earnings quality score. Higher composite scores indicate higher quality.

### Entry / Exit Rules

- **Entry (Long)**: Go long the top 10% of stocks by composite earnings quality score.
- **Entry (Short)**: Go short the bottom 10% of stocks by composite earnings quality score.
- **Exit**: Liquidate positions at annual rebalance for stocks that no longer qualify for the top or bottom decile.

### Portfolio Construction

- Equal-weight allocation within each leg (long and short).
- 50/50 capital allocation between the long and short sides.

### Rebalancing Schedule

Annual. Rebalance in June or July each year to ensure fiscal year-end financial statements (typically December) are fully released and incorporated.

## Key Indicators / Metrics

- **Accruals Ratio**: Balance sheet accruals / Total Assets
- **Cash Flow to Assets**: Operating Cash Flow / Total Assets
- **Return on Equity (ROE)**: Net Income / Shareholders' Equity
- **Debt-to-Assets**: Total Debt / Total Assets
- **Composite Quality Score**: Sum of cross-sectional ranks across all four factors

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | Jun 2003 – Aug 2018 | SPY |
| Initial Capital | $1,000,000 | — |
| Resolution | Daily | — |

*(Detailed Sharpe/return metrics not disclosed in source.)*

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily prices; annual fundamental data
- **Lookback Period**: Most recent fiscal year for all four component factors
- **Fundamental Data**: Net Income, Total Assets, Shareholders' Equity, Total Debt, Operating Cash Flow, Current Assets, Cash, Current Liabilities, Depreciation, sector/industry classification

## Implementation Notes

- Each factor must be ranked independently before summing, ensuring equal contribution to the composite score regardless of scale differences.
- Ascending vs. descending rank direction must be set correctly: lower accruals and lower debt are higher quality, while higher cash flow and higher ROE are higher quality.
- Financial sector exclusion requires reliable industry classification data (SIC or GICS codes).
- Point-in-time fundamental data is essential to avoid look-ahead bias.
- Python implementation on QuantConnect LEAN engine using fine universe selection with Morningstar fundamentals.
- Handling missing data: stocks missing any of the four factors should be excluded from the ranking to avoid biased composite scores.

## Risk Considerations

- Composite scoring may mask deterioration in a single important factor (e.g., rising debt offset by strong ROE).
- Annual rebalancing limits responsiveness to mid-year fundamental changes.
- The equal weighting of four factors is arbitrary; different factor weightings could materially change portfolio composition.
- Quality factors can underperform during speculative, risk-on market environments where low-quality, high-beta stocks rally.
- ROE can be artificially inflated by share buybacks that reduce equity, potentially misclassifying leveraged firms as high quality.
- Short leg targets the lowest quality firms, which may include distressed companies with elevated borrowing costs.

## Related Strategies

- [Accrual Anomaly](accrual-anomaly.md)
- [ROA Effect Within Stocks](roa-effect-within-stocks.md)
- [Asset Growth Effect](asset-growth-effect.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/earnings-quality-factor)
