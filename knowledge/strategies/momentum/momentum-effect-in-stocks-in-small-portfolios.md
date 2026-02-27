# Momentum Effect in Stocks in Small Portfolios

## Overview

Applies the momentum anomaly to small portfolios (up to 50 stocks) designed for retail investors who cannot diversify like hedge funds. Momentum returns are attributed to behavioral biases including underreaction and confirmation bias.

## Academic Reference

- **Paper**: "Momentum Effect in Stocks in Small Portfolios" — Quantpedia Screener #162
- **Link**: https://quantpedia.com/Screener/Details/162

## Strategy Logic

### Universe Selection

1. **Coarse filter**: All US-listed companies with fundamental data. Excludes blacklisted assets (e.g., data-issue tickers).
2. **Fine filter**: Top 75% by market capitalization (bottom 25% excluded for liquidity).

### Signal Generation

12-month (365-day) momentum: stock return over previous year.

### Entry / Exit Rules

- **Long**: 10 stocks with highest 12-month returns.
- **Short**: 10 stocks with lowest 12-month returns.
- **Exit**: Non-portfolio stocks liquidated at annual rebalance.

### Portfolio Construction

- 50% long, 50% short (equally weighted within each leg).
- Per-stock allocation: 5% long, -5% short.
- Total positions: 20 stocks.

### Rebalancing Schedule

Yearly (monthly schedule triggers check, executes annually).

## Key Indicators / Metrics

- 12-month (365-day) total return
- Market capitalization (universe filter)
- Dollar volume (fundamental data availability)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2008 – Sep 2018 |
| Initial Capital | $1,000,000 |
| Resolution | Daily |
| Benchmark | SPY |

*(Detailed return/Sharpe metrics not disclosed.)*

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily
- **Lookback Period**: 365 days (12 months)
- **Fundamental Data**: Morningstar (market cap)

## Implementation Notes

- Three key methods: coarse selection (fundamental data filter), fine selection (market cap rank + 12-month return calculation), rebalancing (monthly trigger, annual execution).
- History API used for 365-day lookback return calculation.
- Python implementation on QuantConnect LEAN.

## Risk Considerations

- Small sample size (20 positions) vs. thousands in institutional momentum.
- Requires margin for short positions.
- Annual rebalancing may miss momentum shifts within the year.
- Bottom-quartile market cap excluded, but remaining universe still has liquidity risk for smaller names.
- Behavioral biases (underreaction, confirmation) may diminish as market efficiency improves.

## Related Strategies

- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)
- [Small Capitalization Stocks Premium Anomaly](../value-and-fundamental/small-capitalization-stocks-premium-anomaly.md)
- [Momentum and Reversal Combined with Volatility Effect in Stocks](momentum-and-reversal-combined-with-volatility-effect-in-stocks.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/momentum-effect-in-stocks-in-small-portfolios)
