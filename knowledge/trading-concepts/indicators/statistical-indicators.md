# Statistical Indicators

## Overview

Statistical indicators measure relationships between assets, statistical properties of price series, and risk/return characteristics. They are essential for portfolio analysis, pairs trading, factor modeling, and risk management. Unlike momentum or trend indicators that focus on a single asset, statistical indicators often operate on pairs or portfolios of assets.

## Relationship Indicators

### Beta

Beta measures an asset's sensitivity to market (or benchmark) movements.

- **Formula:** `Beta = Cov(R_asset, R_market) / Var(R_market)`
- **Interpretation:**
  - Beta > 1: More volatile than the market. Beta = 1: Moves with the market.
  - Beta < 1: Less volatile than the market. Beta < 0: Moves inversely.
- **Applications:** Hedging ratios, CAPM-based expected returns, portfolio beta targeting, sector rotation.

### Alpha (Jensen's Alpha)

Alpha measures excess return above the risk-adjusted expected return.

- **Formula:** `Alpha = R_asset - [R_f + Beta * (R_market - R_f)]`
- **Interpretation:** Positive alpha indicates outperformance; negative alpha indicates underperformance; zero means returns are fully explained by market exposure.
- **Applications:** Strategy evaluation, manager selection, performance attribution.

### Correlation

Correlation measures the linear relationship between two return series.

- **Formula:** `Rho = Cov(X, Y) / (Sigma_X * Sigma_Y)`
- **Range:** -1 (perfect inverse) to +1 (perfect positive).
- **Applications:**
  - **Diversification:** Low or negative correlation reduces overall portfolio risk.
  - **Pairs trading:** Correlated assets that temporarily diverge present mean-reversion opportunities.
  - **Regime detection:** Rolling correlation reveals changing market relationships.
- **Caution:** Measures linear relationships only and can be unstable in small samples.

### Covariance

Covariance measures how two assets move together in absolute terms.

- **Formula:** `Cov(X, Y) = Sum((X - Mean_X) * (Y - Mean_Y)) / n`
- **Applications:** Foundation for portfolio optimization (Markowitz mean-variance), covariance matrix construction, input to beta and correlation calculations.
- **Note:** Unlike correlation, covariance is not normalized and depends on the scale of inputs.

## Dispersion Indicators

### Variance / Standard Deviation

Variance and standard deviation measure the dispersion of returns around the mean.

- **Formulas:** `Variance = Sum((x - Mean)^2) / n` and `Std Dev = sqrt(Variance)`
- **Annualization:** `Sigma_annual = Sigma_daily * sqrt(252)` (assuming 252 trading days).
- **Applications:** Core input to Sharpe/Sortino ratios and VaR, position sizing via volatility targeting, Bollinger Band width.
- **Note:** Assumes normally distributed returns, which may underestimate tail risk.

## Smoothing Techniques

### Heikin-Ashi

Heikin-Ashi candles are modified candlesticks that filter noise for clearer trend identification.

- **Formulas:**
  - `HA_Close = (Open + High + Low + Close) / 4`
  - `HA_Open = (HA_Open_prev + HA_Close_prev) / 2`
  - `HA_High = max(High, HA_Open, HA_Close)`
  - `HA_Low = min(Low, HA_Open, HA_Close)`
- **Characteristics:** Green candles with no lower shadow indicate strong uptrend; red candles with no upper shadow indicate strong downtrend; small bodies with both shadows indicate indecision.
- **Caution:** Heikin-Ashi prices are synthetic -- use actual OHLC for order placement.

## Risk-Adjusted Performance Indicators

### Sharpe Ratio (Rolling)

The Sharpe ratio measures return per unit of total risk.

- **Formula:** `Sharpe = (R_p - R_f) / Sigma_p`
- **Benchmarks:** > 1.0 acceptable, > 2.0 very good, > 3.0 outstanding.
- **Annualization:** `Sharpe_annual = Sharpe_daily * sqrt(252)`
- **Rolling application:** Compute over a sliding window (e.g., 60 or 252 days) to track performance evolution.
- **Limitation:** Penalizes upside and downside volatility equally, which may mislead for positively skewed strategies.

### Sortino Ratio

The Sortino ratio improves on Sharpe by penalizing only downside volatility.

- **Formula:** `Sortino = (R_p - R_f) / Sigma_downside`
- **Downside deviation:** Uses only returns below a target threshold (often 0 or the risk-free rate).
- **Advantage:** Better suited for asymmetric return distributions (options, trend-following).
- **Interpretation:** A higher Sortino than Sharpe indicates volatility is skewed to the upside.

### Maximum Drawdown

Maximum drawdown measures the largest peak-to-trough decline in portfolio value.

- **Formula:** `MDD = (Peak - Trough) / Peak`
- **Applications:** Critical risk metric for strategy comparison, input to Calmar ratio (`Annualized Return / MDD`), and drawdown duration analysis.
- **Note:** Historical MDD is a lower bound; future drawdowns may exceed past observations.

### Information Ratio

The information ratio measures active return per unit of active risk.

- **Formula:** `IR = (R_p - R_benchmark) / Tracking Error`
- **Tracking Error:** Standard deviation of the difference between portfolio and benchmark returns.
- **Benchmarks:** > 0.5 is good, > 1.0 is excellent.

## Summary Table

| Indicator | Category | Primary Use | Key Parameters |
|---|---|---|---|
| Beta | Relationship | Market sensitivity, hedging | Lookback period, benchmark |
| Alpha | Relationship | Performance attribution | Lookback period, risk-free rate |
| Correlation | Relationship | Diversification, pairs trading | Lookback window |
| Covariance | Relationship | Portfolio optimization | Lookback window |
| Variance / Std Dev | Dispersion | Risk measurement, sizing | Lookback period |
| Heikin-Ashi | Smoothing | Trend visualization | None (derived from OHLC) |
| Sharpe Ratio | Risk-Adjusted | Return per total risk | Lookback window, risk-free rate |
| Sortino Ratio | Risk-Adjusted | Return per downside risk | Lookback window, target return |
| Max Drawdown | Risk-Adjusted | Worst-case loss measurement | Full period or rolling window |
| Information Ratio | Risk-Adjusted | Active management skill | Lookback window, benchmark |

*Source: Generalized from QuantConnect Indicators documentation.*
