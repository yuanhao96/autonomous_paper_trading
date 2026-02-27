# Mean-Reversion Statistical Arbitrage Strategy in Stocks

## Overview

PCA-based statistical arbitrage strategy that uses Principal Component Analysis to extract market factors, then identifies stocks whose prices deviate significantly from model-predicted values. Enters short positions when z-scores fall below -1.5, weighting inversely by deviation magnitude. Rebalances every 30 days.

## Academic Reference

- **Paper**: "Statistical Arbitrage in the U.S. Equities Market" — Avellaneda & Lee
- Finding: "PCA-based strategies have Sharpe ratios that outperform Sharpe ratios from ETF-based strategies" (1997–2007).

## Strategy Logic

### Universe Selection

1. US equities priced above $5.
2. Top 20 stocks by dollar trading volume.

### Signal Generation

**Step 1 — PCA dimensionality reduction**:
Apply PCA to extract 3 uncorrelated market factors from 60 days of log-transformed, centered close prices.

**Step 2 — OLS regression**:
Fit each stock's returns against the 3 PCA components. Calculate standardized residuals (z-scores).

**Step 3 — Signal**:
Stocks with z-score < -1.5 are identified as significantly undervalued relative to the model.

### Entry / Exit Rules

- **Short**: Enter when z-score < -1.5 (counter-intuitive — assumes mean reversion from below).
- **Exit**: Automatic liquidation at 30-day rebalance.
- **Position sizing**: Weight inversely proportional to absolute z-score, normalized to sum to 1.

### Portfolio Construction

Inverse z-score weighting. Short bias. Positions rebalanced every 30 days.

### Rebalancing Schedule

Every 30 days (adjustable parameter).

## Key Indicators / Metrics

- Principal Component Analysis (3 components)
- OLS regression residuals
- Standardized z-scores (threshold: -1.5)
- 60-day lookback window

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2010 – Aug 2019 |
| Annual Return | >6% |
| Max Drawdown | ~49% |
| Initial Capital | $100,000 |

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily (hourly for live trading)
- **Lookback Period**: 60 trading days of daily close prices
- **Libraries**: scikit-learn (PCA), statsmodels (OLS), pandas, numpy

## Implementation Notes

- PCA applied to log-transformed, centered price matrix.
- OLS regression per stock against 3 PCA components.
- Z-score threshold and lookback window are tunable parameters.
- Universe set to hourly resolution for computational efficiency.
- PEP8 compliant. Python on QuantConnect LEAN.

## Risk Considerations

- ~49% max drawdown is extremely high — model risk when mean reversion fails.
- Assumes mean reversion occurs within 30 days — regime changes can break this assumption.
- Small universe (20 stocks) limits diversification and increases concentration risk.
- Parameter sensitivity: results depend heavily on z-score threshold (-1.5), lookback (60 days), PCA components (3), and rebalance frequency (30 days).
- Unhedged — no explicit market-neutral construction.
- Short bias introduces theoretically unlimited loss potential.
- Authors suggest expanding beyond 20 stocks for better results.

## Related Strategies

- [Optimal Pairs Trading](optimal-pairs-trading.md)
- [Pairs Trading - Copula vs Cointegration](pairs-trading-copula-vs-cointegration.md)
- [Residual Momentum](../momentum/residual-momentum.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/mean-reversion-statistical-arbitrage-strategy-in-stocks)
