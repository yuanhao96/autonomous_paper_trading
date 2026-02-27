# Price Earnings Anomaly

## Overview

Exploits the well-documented P/E anomaly by going long stocks with the lowest price-to-earnings ratios. Filters a broad US equity universe for fundamental data, ranks by P/E, and equal-weights the 10 cheapest stocks with annual rebalancing.

## Academic Reference

- **Paper**: "P/E and EV/EBITDA Investment Strategies vs. the Market" — Persson & Ståhlberg (2006), Master's thesis, Linköping University
- **Supporting**: "Multifactor Explanations of Asset Pricing Anomalies" — Fama & French (1996), Journal of Finance, Vol. 51 No. 1

## Strategy Logic

### Universe Selection

1. All US equities with fundamental data available.
2. Price filter: > $5.
3. Sort by dollar volume, select top 200.
4. Fine filter: require valid P/E ratio > 0.

### Signal Generation

Rank the 200 stocks by P/E ratio ascending. Select the 10 stocks with the lowest P/E ratios.

### Entry / Exit Rules

- **Long**: Equal-weight the 10 lowest-P/E stocks.
- **Exit**: Liquidate positions removed from selection at annual rebalance.
- No short positions.

### Portfolio Construction

Equal-weight: 10% allocation per stock.

### Rebalancing Schedule

Annual, at the beginning of each calendar year.

## Key Indicators / Metrics

- Price-to-Earnings ratio (primary selection criterion)
- Dollar volume (liquidity screen)
- Price filter (> $5)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2016 – Jul 2019 |
| Initial Capital | $100,000 |
| Benchmark | S&P 500 (SPY) |
| Result | Outperformed benchmark |

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily
- **Fundamental Data**: P/E ratio, earnings per share, dollar volume
- **Lookback**: None (cross-sectional ranking)

## Implementation Notes

- Coarse selection filters by `has_fundamental_data` and price > $5.
- Fine selection sorts by P/E ratio, takes bottom 10.
- `on_securities_changed()` handles liquidation and rebalancing.
- Python on QuantConnect LEAN.

## Risk Considerations

- Heavy exposure to small-cap "size factor" — most selected stocks are small-cap, amplifying volatility and liquidity risk.
- Value trap risk: low P/E may reflect genuine earnings deterioration, not undervaluation.
- 10-stock portfolio is highly concentrated — single-stock events dominate returns.
- Annual rebalancing may be too infrequent during volatile markets.
- Backtest period (2016–2019) is relatively short and coincides with a bull market.
- No risk management, stop-loss, or drawdown controls.

## Related Strategies

- [Book-to-Market Value Anomaly](book-to-market-value-anomaly.md)
- [G-Score Investing](g-score-investing.md)
- [Stock Selection Based on Fundamental Factors](stock-selection-based-on-fundamental-factors.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/price-earnings-anomaly)
