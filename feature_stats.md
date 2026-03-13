# Feature Predictive Power Stats

Computed on S&P 500 universe, 2020-01 to 2025-12, 21-day forward alpha vs SPY.

## 1. Rank IC (Spearman correlation: feature rank vs forward alpha rank)

Higher |IC mean| = more predictive. IC IR > 0.5 is strong. Pct positive > 60% means the signal is consistent.

| Feature | IC Mean | IC Std | IC IR | Pct Positive | Months |
|---------|---------|--------|-------|-------------|--------|
| `debt_to_equity` | +0.1049 | 0.1514 | +0.693 | 66.7% | 12 |
| `roa` | -0.0545 | 0.1398 | -0.390 | 50.0% | 12 |
| `current_ratio` | -0.0433 | 0.1734 | -0.250 | 50.0% | 12 |
| `gross_margin_vs_sector` | -0.0389 | 0.1353 | -0.288 | 50.0% | 12 |
| `operating_margin_stability` | -0.0383 | 0.1190 | -0.322 | 33.3% | 6 |
| `volatility_60d` | +0.0378 | 0.2607 | +0.145 | 49.3% | 71 |
| `volatility_20d` | +0.0343 | 0.2376 | +0.144 | 50.7% | 71 |
| `roe_vs_sector` | +0.0315 | 0.1690 | +0.187 | 50.0% | 12 |
| `roe_stability` | +0.0264 | 0.1524 | +0.173 | 33.3% | 6 |
| `close_vs_sma50` | -0.0257 | 0.2043 | -0.126 | 50.7% | 71 |
| `low_52w_pct` | +0.0256 | 0.1782 | +0.144 | 59.2% | 71 |
| `gross_margin` | -0.0227 | 0.1515 | -0.150 | 58.3% | 12 |
| `return_3m` | -0.0218 | 0.2219 | -0.098 | 54.9% | 71 |
| `high_52w_pct` | -0.0213 | 0.2506 | -0.085 | 52.1% | 71 |
| `drawdown` | -0.0198 | 0.2515 | -0.079 | 50.7% | 71 |
| `volatility_20d_vs_sector` | +0.0191 | 0.1718 | +0.111 | 49.3% | 71 |
| `sector_return_3m` | -0.0157 | 0.1845 | -0.085 | 45.1% | 71 |
| `roe` | +0.0156 | 0.1212 | +0.129 | 58.3% | 12 |
| `sector_breadth` | +0.0155 | 0.1585 | +0.098 | 56.3% | 71 |
| `gross_margin_stability` | +0.0149 | 0.1677 | +0.089 | 50.0% | 6 |
| `operating_margin` | +0.0135 | 0.1186 | +0.114 | 58.3% | 12 |
| `return_12m` | +0.0104 | 0.2307 | +0.045 | 52.1% | 71 |
| `avg_volume_20d` | -0.0060 | 0.1164 | -0.052 | 47.9% | 71 |
| `return_1m` | +0.0059 | 0.1899 | +0.031 | 53.5% | 71 |
| `return_1m_vs_sector` | +0.0059 | 0.1432 | +0.041 | 47.9% | 71 |
| `sma50_vs_sma200` | +0.0044 | 0.2227 | +0.020 | 54.9% | 71 |
| `volume_ratio` | +0.0030 | 0.0713 | +0.042 | 54.9% | 71 |
| `sector_return_1m` | +0.0023 | 0.1768 | +0.013 | 57.7% | 71 |
| `return_6m` | +0.0020 | 0.2204 | +0.009 | 53.5% | 71 |
| `close_vs_sma200` | +0.0012 | 0.2319 | +0.005 | 56.3% | 71 |
| `net_margin` | +0.0005 | 0.1633 | +0.003 | 66.7% | 12 |
| `return_6m_vs_sector` | +0.0004 | 0.1770 | +0.002 | 52.1% | 71 |

## 2. Quintile Long-Short Sharpe

Each month: sort stocks by feature, measure alpha of each quintile. Q5 = top, Q1 = bottom. LS Sharpe = annualized Sharpe of (Q5 - Q1). Monotonic = fraction of Q1→Q5 steps that increase (1.0 = perfect).

| Feature | LS Sharpe | Q1 Alpha% | Q5 Alpha% | Spread% | Monotonic |
|---------|-----------|-----------|-----------|---------|-----------|
| `operating_margin` | +1.989 | -0.92 | +0.08 | +1.00 | 0.75 |
| `net_margin` | +1.212 | -1.27 | +0.30 | +1.58 | 0.75 |
| `debt_to_equity` | +1.092 | -0.87 | +0.30 | +1.17 | 0.75 |
| `gross_margin_vs_sector` | +1.084 | -1.56 | -0.03 | +1.53 | 0.50 |
| `volatility_20d_vs_sector` | +0.921 | -0.37 | +1.05 | +1.42 | 1.00 |
| `volatility_60d` | +0.874 | -0.53 | +1.37 | +1.90 | 1.00 |
| `volatility_20d` | +0.850 | -0.55 | +1.17 | +1.72 | 1.00 |
| `current_ratio` | +0.819 | -1.42 | -0.74 | +0.68 | 0.75 |
| `low_52w_pct` | +0.610 | -0.08 | +0.81 | +0.89 | 0.75 |
| `roe_vs_sector` | +0.470 | -0.78 | -0.20 | +0.58 | 0.50 |
| `sector_breadth` | +0.298 | -0.22 | +0.15 | +0.36 | 0.75 |
| `roe` | +0.297 | -0.65 | -0.28 | +0.37 | 0.75 |
| `volume_ratio` | +0.281 | +0.13 | +0.27 | +0.15 | 0.50 |
| `gross_margin` | +0.173 | -1.42 | -1.23 | +0.20 | 0.50 |
| `return_1m_vs_sector` | +0.092 | +0.30 | +0.42 | +0.11 | 0.50 |
| `avg_volume_20d` | +0.007 | +0.26 | +0.26 | +0.01 | 0.50 |
| `return_12m` | -0.016 | +0.38 | +0.35 | -0.03 | 0.50 |
| `roa` | -0.026 | -0.31 | -0.33 | -0.02 | 0.75 |
| `sma50_vs_sma200` | -0.055 | +0.40 | +0.31 | -0.10 | 0.75 |
| `return_6m` | -0.056 | +0.40 | +0.30 | -0.10 | 0.75 |
| `close_vs_sma200` | -0.061 | +0.39 | +0.28 | -0.11 | 0.25 |
| `return_1m` | -0.096 | +0.35 | +0.20 | -0.15 | 0.50 |
| `return_6m_vs_sector` | -0.105 | +0.49 | +0.34 | -0.15 | 0.50 |
| `sector_return_1m` | -0.175 | +0.06 | -0.21 | -0.27 | 0.50 |
| `return_3m` | -0.318 | +0.66 | +0.08 | -0.59 | 0.50 |
| `sector_return_3m` | -0.336 | +0.52 | -0.04 | -0.56 | 0.50 |
| `close_vs_sma50` | -0.562 | +0.74 | -0.21 | -0.95 | 0.00 |
| `drawdown` | -0.614 | +0.85 | -0.42 | -1.27 | 0.25 |
| `high_52w_pct` | -0.645 | +0.88 | -0.44 | -1.33 | 0.00 |

## 3. Conditional Marginal IC (given core template)

Core template: return_6m > 0.12, close_vs_sma200 > 1.03, drawdown > -0.07, volume_ratio > 1.15

For stocks already passing the core template, which additional features predict forward alpha? Higher |cond IC| = more useful as an add-on filter.

| Feature | Cond IC | Cond IC IR | Pct Positive | Months |
|---------|---------|------------|-------------|--------|
| `return_1m_vs_sector` | +0.0569 | +0.262 | 60.0% | 50 |
| `close_vs_sma50` | +0.0480 | +0.169 | 64.0% | 50 |
| `return_1m` | +0.0422 | +0.156 | 64.0% | 50 |
| `return_12m` | +0.0401 | +0.154 | 58.0% | 50 |
| `low_52w_pct` | +0.0383 | +0.143 | 56.0% | 50 |
| `high_52w_pct` | +0.0368 | +0.164 | 62.0% | 50 |
| `sector_breadth` | +0.0228 | +0.086 | 50.0% | 50 |
| `volatility_20d` | +0.0169 | +0.057 | 52.0% | 50 |
| `avg_volume_20d` | +0.0144 | +0.070 | 52.0% | 50 |
| `sector_return_3m` | +0.0141 | +0.051 | 52.0% | 50 |
| `sector_return_1m` | -0.0103 | -0.041 | 48.0% | 50 |
| `return_6m_vs_sector` | +0.0097 | +0.038 | 54.0% | 50 |
| `sma50_vs_sma200` | -0.0089 | -0.034 | 46.0% | 50 |
| `volatility_60d` | +0.0050 | +0.016 | 50.0% | 50 |
| `return_3m` | -0.0015 | -0.006 | 50.0% | 50 |
| `volatility_20d_vs_sector` | -0.0007 | -0.003 | 52.0% | 50 |

## Interpretation Guide

- **rank_by candidates**: Use features with high LS Sharpe + good monotonicity (top of table 2). These are good for `rank_by` in the screen DSL.
- **Filter candidates**: Use features with high |IC mean| + consistent sign (pct positive far from 50%). Positive IC → filter for high values; negative IC → filter for low values.
- **Add-on filters**: Table 3 shows what helps AFTER the core momentum template. These are the most actionable for improving existing screens.
- **Avoid**: Features with IC near 0, low monotonicity, or inconsistent sign (pct positive near 50%) — these are noise.
