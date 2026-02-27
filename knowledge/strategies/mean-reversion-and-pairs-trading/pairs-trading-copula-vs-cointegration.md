# Pairs Trading - Copula vs Cointegration

## Overview

Compares two pairs trading methodologies — copula-based and cointegration-based — on ETF pairs. The copula method uses Archimedean copulas (Clayton, Gumbel, Frank) to model non-linear dependence and generate mispricing indices. The cointegration method uses spread z-scores with ±1σ thresholds. Copula approach generates higher returns but with larger drawdowns.

## Academic Reference

- **Copula**: "Trading Strategies with Copulas" — Stander, Marais & Botha (2013)
- **Cointegration**: "Statistical Arbitrage Trading Strategies and High-Frequency Trading" — Hanson & Hall (2012)

## Strategy Logic

### Universe Selection

14 ETFs traded on NASDAQ/NYSE: QQQ, XLK, XME, EWG, TNA, TLT, FAS, FAZ, XLF, XLU, EWC, EWA, QLD, QID.
- Copula pair: QQQ & XLK.
- Cointegration pair: GLD & DGL.

### Signal Generation

**Copula method**:
1. Transform log returns to uniform distributions via empirical CDFs.
2. Estimate Kendall's tau correlation.
3. Fit 3 Archimedean copula families (Clayton, Gumbel, Frank); select best via AIC.
4. Compute mispricing indices as conditional probabilities: MI(Y|X) and MI(X|Y).

**Cointegration method**:
1. Fit OLS regression on log prices to generate spread series.
2. Set thresholds at ±1 standard deviation from mean spread.

### Entry / Exit Rules

**Copula**:
- **Long pair**: MI(Y|X) < 0.05 AND MI(X|Y) > 0.95.
- **Short pair**: MI(Y|X) > 0.95 AND MI(X|Y) < 0.05.
- **Exit**: When signal reverses.

**Cointegration**:
- **Long pair**: Spread < mean − 1σ.
- **Short pair**: Spread > mean + 1σ.
- **Exit**: When spread reverts to mean.

### Portfolio Construction

Position sizing via linear regression coefficient β for proportional hedging. Monthly parameter recalculation.

### Rebalancing Schedule

Monthly parameter recalculation. Daily trade execution.

## Key Indicators / Metrics

- Kendall's tau (rank correlation)
- Pearson and Spearman correlation
- Mispricing indices (conditional probabilities)
- Spread z-score
- AIC (copula model selection)

## Backtest Performance

| Metric | Copula | Cointegration |
|--------|--------|---------------|
| Return | 7.057% | 4.506% |
| Sharpe Ratio | 0.098 | 0.179 |
| Max Drawdown | 24.0% | 3.9% |
| Transactions | 498 | 126 |
| Period | Jan 2010 – Sep 2019 | Jan 2011 – May 2017 |

Key finding: Copula generates 56% higher returns by detecting non-linear dependencies, but with 6× larger drawdown.

## Data Requirements

- **Asset Classes**: US ETFs
- **Resolution**: Daily
- **Lookback**: 1,000 days formation period; 250-day rolling windows
- **Libraries**: SciPy, NumPy, StatsModels

## Implementation Notes

- Monthly universe selection on first trading day.
- Copula parameter estimation via maximum likelihood.
- AIC for model selection among Clayton, Gumbel, Frank families.
- Empirical CDFs for probability integral transform.
- Python on QuantConnect LEAN.

## Risk Considerations

- Copula assumes stable dependence structure — may fail during regime shifts.
- Computationally intensive — copula fitting is slower than cointegration.
- Cointegration assumes linear relationships — fails during low-volatility regimes (only 91 trades over 5 years).
- Rolling parameter estimates are subject to market regime shifts.
- Historical correlation/dependence may not persist forward.
- Empirical CDFs unreliable with limited data in tail regions.
- Copula's 24% drawdown is significant for a pairs trading strategy.

## Related Strategies

- [Optimal Pairs Trading](optimal-pairs-trading.md)
- [Pairs Trading with Stocks](pairs-trading-with-stocks.md)
- [Intraday Dynamic Pairs Trading](intraday-dynamic-pairs-trading.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/pairs-trading-copula-vs-cointegration)
