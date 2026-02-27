# Intraday Dynamic Pairs Trading Using Correlation and Cointegration Approach

## Overview

High-frequency pairs trading strategy using a two-stage selection process: first filters pairs by correlation (≥ 0.9), then validates with Engle-Granger cointegration testing. Trades intraday on 10-minute bars with 2.32σ entry thresholds and 0.5σ exit thresholds, targeting bank sector stocks. Achieves low beta (0.232) through market-neutral construction.

## Academic Reference

- **Paper**: "High Frequency and Dynamic Pairs Trading Based on Statistical Arbitrage Using a Two-Stage Correlation and Cointegration Approach" — George J. Miao

## Strategy Logic

### Universe Selection

20 US bank sector stocks generating 190 potential pairs. Sector-specific selection increases correlation likelihood among "close substitutes."

### Signal Generation

**Stage 1 — Correlation filter**:
Pearson correlation ≥ 0.9 over 3-month rolling window.

**Stage 2 — Cointegration validation**:
Engle-Granger methodology: test if z_t = y_t − γx_t is stationary via Augmented Dickey-Fuller (ADF) test with p-value ≤ 0.05.

**Trade signal**: OLS regression residuals (ε) relative to mean and standard deviation.

### Entry / Exit Rules

- **Long pair**: ε < mean − 2.32σ → Long stock B, short stock A.
- **Short pair**: ε > mean + 2.32σ → Long stock A, short stock B.
- **Exit**: Residual reverts within 0.5σ of mean.
- **Stop-loss**: ±6σ from mean (protective mechanism).
- **Pair invalidation**: Close positions if pair loses correlation/cointegration status.

### Portfolio Construction

Equal leverage allocation across selected pairs. Maximum 10 pairs simultaneously. 1× leverage. Market-neutral (backtested beta: 0.232).

### Rebalancing Schedule

3-month training period → 3-month trading period. Weekly correlation/cointegration verification with dynamic pair replacement.

## Key Indicators / Metrics

- Pearson correlation coefficient (threshold: 0.9)
- ADF test statistic (p-value ≤ 0.05)
- OLS regression residuals (mean, σ)
- Entry threshold: 2.32σ (95% confidence)
- Exit threshold: 0.5σ
- Stop-loss: 6σ

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | September 2013 (sample) |
| Annualized Return | 26.924% |
| Sharpe Ratio | 3.011 |
| Beta | 0.232 |
| Strategy Type | Market-neutral stat arb |

## Data Requirements

- **Asset Classes**: US equities (bank sector)
- **Resolution**: 10-minute bars (minimum 1-minute available)
- **Lookback Period**: 3 months for training
- **Data Quality**: Requires NaN volume handling; delisted tickers must be removed

## Implementation Notes

- `SymbolData` class: maintains rolling price windows, consolidates minute data.
- `Pairs` class: stores cointegration parameters (model, residual statistics, correlation).
- `TradingPair` class: tracks active positions with model coefficients.
- `TradeBarConsolidator` aggregates minute bars to 10-minute intervals.
- Parameters: opening threshold (2.32σ), closing threshold (0.5σ), stop-loss (6σ), data interval (10 min).
- Python on QuantConnect LEAN.

## Risk Considerations

- Single-month backtest (Sep 2013) is far too short for reliable conclusions.
- Bank sector concentration increases exposure to financial systemic risk.
- High-frequency execution requires low-latency infrastructure — slippage on 190+ pairs.
- Pair relationships unstable over time — rolling windows mitigate but cannot eliminate decay.
- Stop-loss at 6σ is extremely wide — may allow significant losses before triggering.
- Parameter sensitivity: strategy depends heavily on threshold selection.
- Delisted tickers (e.g., SCNB) and NaN volume data require careful handling.
- Statistical artifacts from single-sector, single-period testing.

## Related Strategies

- [Pairs Trading - Copula vs Cointegration](pairs-trading-copula-vs-cointegration.md)
- [Pairs Trading with Stocks](pairs-trading-with-stocks.md)
- [Mean-Reversion Statistical Arbitrage Strategy in Stocks](mean-reversion-statistical-arbitrage-in-stocks.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/intraday-dynamic-pairs-trading-using-correlation-and-cointegration-approach)
