# Price and Earnings Momentum

## Overview

A long/short equity strategy combining two momentum factors — price momentum (quarterly returns) and earnings momentum (EPS growth) — to rank and trade stocks. Based on the academic finding that stocks exhibiting strong performance over 3–12 month periods tend to continue outperforming.

## Academic Reference

- **Paper**: "Momentum" — N. Jegadeesh and S. Titman
- **Concept**: Stocks with strong 3–12 month performance tend to continue; weak performers tend to underperform.

## Strategy Logic

### Universe Selection

1. **Coarse filter**: Price > $5, positive dollar volume, fundamental data available. Top 100 by dollar volume.
2. **Fine filter**: Combined ranking of quarterly return + EPS growth. Top 10 (long) and bottom 10 (short).

### Signal Generation

Two-factor ranking system:

1. **Quarterly return ranking**: Historical close prices over 91-day period.
   ```
   Return = first_close / last_close
   ```
2. **EPS growth ranking**: Uses RollingWindow to track basic EPS across quarters.
   ```
   EPS_growth = (current_EPS - prior_EPS) / prior_EPS
   ```
3. **Combined score**: Sum of ranks from both indicators.

### Entry / Exit Rules

- **Long**: Top 10 stocks by combined momentum score.
- **Short**: Bottom 10 stocks by combined momentum score.
- **Exit**: Positions liquidated if stocks no longer meet selection criteria at rebalance.
- Insights generated with 91-day duration.

### Portfolio Construction

Equal weight across all 20 positions (10 long + 10 short). Margin account enabled (Interactive Brokers brokerage model). Maximum 20% drawdown per security enforced.

### Rebalancing Schedule

Monthly universe refresh; quarterly position rebalancing (91-day cycles).

## Key Indicators / Metrics

- 91-day price return
- Quarterly basic EPS
- EPS growth rate
- Combined rank score
- Dollar volume (universe filter)

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | 2023–2024 (1 year) | S&P 500 |
| Initial Capital | $100,000 | — |
| Sharpe Ratio | -0.268 | 0.758 |

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily (history requests), minute (universe selection)
- **Lookback Period**: 91 days (quarterly return) + quarterly EPS history
- **Fundamental Data**: Basic EPS, dollar volume, price

## Implementation Notes

- Modular architecture: separate modules for universe selection and alpha model.
- RollingWindow data structure for temporal EPS analysis.
- Data normalization mode: Raw/scaled raw pricing.
- Python implementation on QuantConnect LEAN.

## Risk Considerations

- Strategy underperformed passive indexing (Sharpe -0.268 vs 0.758 benchmark).
- Universe size (100 stocks) potentially too restrictive.
- Equal weighting may not capture strength differences among higher-ranked securities.
- Quarterly rebalancing may be too frequent for momentum dynamics.
- EPS data subject to revisions and seasonal effects.

## Related Strategies

- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)
- [Standardized Unexpected Earnings](../factor-investing/standardized-unexpected-earnings.md)
- [Earnings Quality Factor](../factor-investing/earnings-quality-factor.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/price-and-earnings-momentum)
