# Book-to-Market Value Anomaly

## Overview

Exploits the value premium by investing in stocks with the highest book-to-market (B/M) ratios among large-cap equities. Filters the top 20% by market capitalization, then selects the top 20% by B/M ratio within that subset. Market-cap weighted with annual rebalancing.

## Academic Reference

- **Paper**: Quantpedia — "Value (Book-to-Market) Anomaly"
- **Source**: quantpedia.com/Screener/Details/26

## Strategy Logic

### Universe Selection

1. All US equities with fundamental data.
2. Filter to top 20% by market capitalization (large-cap only).
3. Exclude stocks with P/B ratio ≤ 0.

### Signal Generation

Within the large-cap subset, rank by book-to-market ratio (inverse of P/B) descending. Select the top 20% (highest B/M = cheapest stocks).

Final portfolio ≈ 4% of total universe (top 20% of top 20%).

### Entry / Exit Rules

- **Long**: Market-cap weighted positions in the highest B/M quintile of large-cap stocks.
- **Exit**: Liquidate positions removed from selection at annual rebalance.
- No short positions.

### Portfolio Construction

Market-capitalization weighted. Individual stock weight = stock market cap / total portfolio market cap.

### Rebalancing Schedule

Annual.

## Key Indicators / Metrics

- Book-to-Market ratio (primary signal)
- Market capitalization (size filter)
- Price-to-Book ratio (inverted for B/M)
- Common shareholders' equity

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2014 – Jul 2018 |
| Initial Capital | $1,000,000 |
| Benchmark | S&P 500 (SPY) |
| Result | Underperformed benchmark |

Note: Value stocks underperformed during the 2014–2018 bull market, where growth stocks dominated due to optimistic earnings expectations.

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Minute (updated from daily)
- **Fundamental Data**: P/B ratio, market capitalization, shareholders' equity
- **Lookback**: None (cross-sectional)

## Implementation Notes

- Coarse selection filters by `has_fundamental_data`.
- Fine selection computes B/M as inverse of P/B, takes top 20% of top 20%.
- Market-cap weighting applied via `set_holdings()`.
- Security initializer included to prevent trading errors.
- PEP8 compliant. Python on QuantConnect LEAN.

## Risk Considerations

- Value stocks underperform in growth-dominated bull markets (as seen in 2014–2018).
- B/M ratio alone may not capture full value — misses earnings quality, growth trajectory.
- Annual rebalancing is slow to react to fundamental changes.
- Market-cap weighting concentrates in the largest "cheap" stocks — less diversification benefit.
- Fundamental data dependency — stale or incorrect P/B data can lead to poor selection.
- No risk management or stop-loss mechanisms.

## Related Strategies

- [Price Earnings Anomaly](price-earnings-anomaly.md)
- [Fama-French Five Factors](../factor-investing/fama-french-five-factors.md)
- [Value Effect Within Countries](value-effect-within-countries.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/book-to-market-value-anomaly)
