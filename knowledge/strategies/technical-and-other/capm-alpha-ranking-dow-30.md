# CAPM Alpha Ranking Strategy on Dow 30 Companies

## Overview

Ranks Dow 30 stocks by CAPM alpha (regression intercept vs. SPY over 21 days) and goes long the top 2 stocks with highest alpha. Monthly rebalancing. Based on the premise that recent alpha persistence predicts future outperformance. 50% allocation per stock.

## Academic Reference

- **Paper**: Based on the Capital Asset Pricing Model (CAPM) — William F. Sharpe & Harry Markowitz.
- Linear regression identifies alpha (excess return) and beta (systematic risk) per stock.

## Strategy Logic

### Universe Selection

30 Dow Jones Industrial Average components: AAPL, AXP, BA, CAT, CSCO, CVX, DD, DIS, GE, GS, HD, IBM, INTC, JPM, KO, MCD, MMM, MRK, MSFT, NKE, PFE, PG, TRV, UNH, UTX, V, VZ, WMT, XOM.

### Signal Generation

For each stock, run linear regression: stock_returns = α + β × SPY_returns over 21-day lookback. Rank by α (intercept) descending.

### Entry / Exit Rules

- **Long**: Top 2 stocks with highest alpha.
- **Exit**: Liquidate all non-selected positions at monthly rebalance.

### Portfolio Construction

50% allocation per stock (2 positions). Updated from 100% to avoid margin calls.

### Rebalancing Schedule

Monthly, first trading day after market open.

## Key Indicators / Metrics

- CAPM alpha (regression intercept)
- CAPM beta (regression slope)
- 21-day lookback window
- SPY benchmark returns

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2016 – 2024 |
| Finding | Beats market in smooth conditions |
| 2015 Test | −15.463% return |
| Risk | Margin calls triggered due to leverage |

## Data Requirements

- **Asset Classes**: US equities (Dow 30) + SPY benchmark
- **Resolution**: Daily
- **Lookback**: 21 trading days
- **Earliest Start**: Mar 19, 2015 (last Dow composition change)

## Implementation Notes

- `np.linalg.lstsq()` for linear regression.
- `history()` API for 21-day price data.
- Scheduled monthly rebalancing via `date_rules.month_start()`.
- `set_holdings()` for position sizing.
- Python on QuantConnect LEAN.

## Risk Considerations

- 2-stock portfolio is extremely concentrated — single-stock events dominate.
- "When market volatility increases the model fails to capture alpha."
- 21-day lookback has limited statistical power for meaningful regression.
- Alpha persistence is a weak and debated phenomenon.
- No hedging — fully directional exposure to selected stocks.
- Margin call risk during downturns.
- Dow 30 composition changes require manual updates.
- Authors recommend mean-variance optimization and beta-neutral positioning.

## Related Strategies

- [Fama-French Five Factors](../factor-investing/fama-french-five-factors.md)
- [Fundamental Factor Long Short Strategy](../value-and-fundamental/fundamental-factor-long-short-strategy.md)
- [Paired Switching](paired-switching.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/capm-alpha-ranking-strategy-on-dow-30-companies)
