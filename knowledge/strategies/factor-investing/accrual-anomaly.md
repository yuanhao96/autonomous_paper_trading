# Accrual Anomaly

## Overview

Exploits the accrual anomaly — firms with low accruals (earnings driven primarily by cash flows rather than accounting adjustments) tend to outperform firms with high accruals. High accruals signal less reliable earnings that are more likely to reverse, while low accruals indicate higher earnings quality and persistence.

## Academic Reference

- **Paper**: "Accrual Anomaly" — Quantpedia Screener
- **Link**: https://quantpedia.com/

## Strategy Logic

### Universe Selection

1. Select all common stocks listed on major US exchanges.
2. Require sufficient balance sheet data to compute the accrual measure (current assets, cash, current liabilities, current portion of long-term debt, income tax payable, depreciation, and total assets for two consecutive years).

### Signal Generation

Accruals are calculated using the balance sheet approach, scaled by average total assets:

```
Accrual = [(ΔCurrent Assets - ΔCash) - (ΔCurrent Liabilities - ΔCurrent Debt - ΔIncome Tax Payable) - Depreciation] / Average Total Assets
```

Where:
- `Δ` denotes year-over-year change
- `Average Total Assets = (Total Assets_t + Total Assets_{t-1}) / 2`

All eligible stocks are ranked by their accrual ratio from lowest to highest.

### Entry / Exit Rules

- **Entry (Long)**: Go long the bottom 10% of stocks by accrual ratio (lowest accruals, highest earnings quality).
- **Entry (Short)**: Go short the top 10% of stocks by accrual ratio (highest accruals, lowest earnings quality).
- **Exit**: Liquidate positions at annual rebalance for stocks that no longer qualify for the top or bottom decile.

### Portfolio Construction

- 25% portfolio exposure allocated to the long side.
- 25% portfolio exposure allocated to the short side.
- Remaining 50% held in cash or risk-free assets.

### Rebalancing Schedule

Annual. Rebalance in June each year to ensure fiscal year-end financial statements are fully available.

## Key Indicators / Metrics

- **Accrual Ratio**: Balance sheet accruals scaled by average total assets
- **Current Assets / Cash / Current Liabilities**: Core balance sheet components for accrual computation
- **Current Debt / Income Tax Payable / Depreciation**: Adjustments in the accrual formula
- **Total Assets**: Used for scaling and averaging

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | May 2007 – Jul 2018 | SPY |
| Initial Capital | $1,000,000 | — |
| Resolution | Daily | — |

*(Detailed Sharpe/return metrics not disclosed in source.)*

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily prices; annual fundamental data
- **Lookback Period**: Two consecutive years of balance sheet data
- **Fundamental Data**: Current Assets, Cash, Current Liabilities, Current Portion of Long-Term Debt, Income Tax Payable, Depreciation and Amortization, Total Assets

## Implementation Notes

- The accrual formula requires careful mapping of balance sheet line items across different accounting standards and data providers.
- Point-in-time fundamental data is critical to avoid look-ahead bias; fiscal year-end data should not be used before it is publicly available.
- The 25% exposure per side (50% total) means 50% of capital remains uninvested, reducing volatility but also limiting absolute returns.
- Python implementation on QuantConnect LEAN engine using fine universe selection with Morningstar fundamentals.
- Missing data fields (e.g., income tax payable, current debt) should be handled with zero imputation or stock exclusion depending on materiality.

## Risk Considerations

- Accrual computation depends on granular balance sheet data; data quality issues or missing fields can distort rankings.
- Annual rebalancing limits responsiveness to mid-year changes in earnings quality.
- The short leg targets firms with high accruals, which may include high-growth companies — introducing momentum risk on the short side.
- Accounting standard changes (e.g., IFRS adoption, lease accounting under ASC 842) can shift accrual distributions over time.
- The reduced exposure (25% per side) dampens drawdowns but also reduces the capture of the accrual premium.

## Related Strategies

- [Earnings Quality Factor](earnings-quality-factor.md)
- [ROA Effect Within Stocks](roa-effect-within-stocks.md)
- [Asset Growth Effect](asset-growth-effect.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/accrual-anomaly)
