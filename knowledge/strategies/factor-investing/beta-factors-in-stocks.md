# Beta Factors in Stocks

## Overview

Exploits the low-beta anomaly — the empirical finding that low-beta stocks deliver higher risk-adjusted returns than high-beta stocks, contradicting the CAPM prediction. The strategy goes long low-beta stocks and short high-beta stocks to capture the beta factor premium while maintaining a roughly market-neutral exposure.

## Academic Reference

- **Paper**: Quantpedia Screener #77 — "Beta Factor in Stocks"
- **Link**: https://quantpedia.com/Screener/Details/77

## Strategy Logic

### Universe Selection

1. **Coarse filter**: Select US equities listed on NYSE/NASDAQ trading above $5 per share. Exclude ETFs.
2. **Volume filter**: Ensure sufficient liquidity via dollar volume thresholds.

### Signal Generation

Beta is calculated for each stock relative to the market index over a 252-day (1-year) rolling window:

```
Beta = Cov(R_asset, R_market) / Var(R_market)
```

Where:
- `R_asset` = daily returns of the individual stock
- `R_market` = daily returns of the Wilshire 5000 Total Market Index

**Note**: The Wilshire 5000 has been discontinued as a live benchmark. Implementation may substitute with a broad market ETF (e.g., VTI) or the S&P 500.

### Entry / Exit Rules

- **Entry (Long)**: Go long the 5 stocks with the lowest beta values.
- **Entry (Short)**: Go short the 5 stocks with the highest beta values.
- **Exit**: Liquidate positions for stocks that fall out of the top/bottom 5 at rebalance.

### Portfolio Construction

- Long portfolio: 40% of total capital, equal-weight across 5 lowest-beta stocks (8% each).
- Short portfolio: 40% of total capital, equal-weight across 5 highest-beta stocks (8% each).
- Remaining 20% held as cash buffer for margin and rebalancing.

### Rebalancing Schedule

Monthly. Beta rankings are recalculated and portfolio is reconstituted at the beginning of each calendar month.

## Key Indicators / Metrics

- **Beta**: 252-day rolling covariance of stock returns with market returns, divided by market variance
- **Dollar volume**: For universe filtering
- **Price filter**: Minimum $5 per share

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | Jan 2018 – Jan 2022 | SPY |
| Initial Capital | $1,000,000 | — |

*(Detailed Sharpe/return metrics not disclosed in source.)*

## Data Requirements

- **Asset Classes**: US equities (NYSE/NASDAQ)
- **Resolution**: Daily
- **Lookback Period**: 252 trading days (1 year) for beta calculation
- **Market Index**: Wilshire 5000 Total Market Index (or substitute broad market proxy)

## Implementation Notes

- Beta calculation requires a 252-day warm-up period before the first trade signal is generated.
- The Wilshire 5000 index was discontinued; implementation should use a suitable proxy such as VTI or the Russell 3000.
- Covariance and variance are calculated using daily log returns over the trailing window.
- Python implementation on QuantConnect LEAN engine.

## Risk Considerations

- The low-beta anomaly may weaken or reverse during strong bull markets where high-beta stocks outperform.
- Concentrated portfolio (10 positions) introduces significant idiosyncratic risk.
- Short positions carry unlimited loss potential and borrowing costs.
- Wilshire 5000 discontinuation requires a proxy, which may introduce tracking differences.
- Beta estimates are noisy and can be sensitive to the estimation window length.
- Transaction costs from monthly rebalancing and short-selling fees are not explicitly modeled.

## Related Strategies

- [Beta Factor in Country Equity Indexes](beta-factor-in-country-equity-indexes.md)
- [Fama-French Five Factors](fama-french-five-factors.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/beta-factors-in-stocks)
