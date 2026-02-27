# Asset Growth Effect

## Overview

Exploits the asset growth anomaly — firms with low total asset growth tend to outperform firms with high asset growth. Companies that aggressively expand their asset base often experience diminishing returns, while conservative growers deliver superior risk-adjusted performance. The effect is consistent with investor overreaction to expansion and empire-building behavior.

## Academic Reference

- **Paper**: "Asset Growth Effect" — Quantpedia Screener
- **Link**: https://quantpedia.com/

## Strategy Logic

### Universe Selection

1. Select all common stocks listed on major US exchanges.
2. Exclude financial companies (SIC codes 6000–6999) and real estate firms to avoid balance sheet distortions from leverage-dependent business models.
3. Require at least two consecutive years of total asset data for growth calculation.

### Signal Generation

Asset growth is calculated as the year-over-year percentage change in total assets:

```
Asset Growth = (Total Assets_t - Total Assets_{t-1}) / Total Assets_{t-1}
```

All eligible stocks are ranked by their asset growth rate from lowest to highest.

### Entry / Exit Rules

- **Entry (Long)**: Go long the lowest 10% of stocks by asset growth (conservative growers).
- **Entry (Short)**: Go short the highest 10% of stocks by asset growth (aggressive expanders).
- **Exit**: Liquidate positions at annual rebalance for stocks that no longer qualify for the top or bottom decile.

### Portfolio Construction

- Equal-weight allocation within each leg (long and short).
- Balanced long-short construction.

### Rebalancing Schedule

Annual. Rebalance at the end of June each year to ensure fiscal year-end data (typically December) is fully available and incorporated.

## Key Indicators / Metrics

- **Asset Growth Rate**: Year-over-year percentage change in total assets
- **Total Assets**: Primary balance sheet metric for signal generation
- **Sector Classification**: Used to exclude financials and real estate

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | Jun 2008 – Jul 2018 | SPY |
| Initial Capital | $1,000,000 | — |
| Resolution | Daily | — |

*(Detailed Sharpe/return metrics not disclosed in source.)*

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily prices; annual fundamental data
- **Lookback Period**: Two consecutive years of total asset data
- **Fundamental Data**: Total Assets, sector/industry classification (SIC or GICS codes)

## Implementation Notes

- Annual rebalance timing at end of June accounts for the reporting lag in fiscal year-end financial statements.
- Financial and real estate sector exclusion requires reliable industry classification data.
- Signal is simple to compute but requires clean, point-in-time fundamental data to avoid look-ahead bias.
- Python implementation on QuantConnect LEAN engine using fine universe selection with Morningstar fundamentals.

## Risk Considerations

- Annual rebalancing means the portfolio cannot react to material changes in a company's asset base mid-year.
- The asset growth effect has shown some decay in recent decades as the anomaly has become more widely known.
- Short leg may include high-growth companies with strong momentum, creating potential for short squeezes.
- Sector exclusions reduce diversification; if financials or real estate outperform, the strategy misses that contribution.
- Asset growth can be driven by acquisitions, organic expansion, or accounting reclassifications — each with different return implications.

## Related Strategies

- [ROA Effect Within Stocks](roa-effect-within-stocks.md)
- [Accrual Anomaly](accrual-anomaly.md)
- [Earnings Quality Factor](earnings-quality-factor.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/asset-growth-effect)
