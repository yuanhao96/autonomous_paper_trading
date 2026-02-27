# Leveraged ETFs with Systematic Risk Management

## Overview

Uses a 200-day SMA trend-following signal to rotate between a 2× leveraged S&P 500 ETF (SSO) and short-term Treasuries (SHY). When SSO is above its 200-day SMA, holds leveraged equities. When below, rotates to safety. Aims to capture leveraged upside while avoiding major drawdowns.

## Academic Reference

- **Paper**: "Leverage for the Long Run — A Systematic Approach to Managing Risk and Magnifying Returns in Stocks" — Gayed & Bilello (2016)

## Strategy Logic

### Universe Selection

- Primary: SSO (ProShares Ultra S&P 500, 2× leveraged)
- Alternative: SHY (iShares 1-3 Year Treasury Bond ETF)
- Benchmark: SPY

### Signal Generation

200-day Simple Moving Average (SMA) on SSO closing prices. Extended period reduces trading frequency, lowering "transaction costs and the effects of slippage."

### Entry / Exit Rules

- **Long SSO**: SSO price > 200-day SMA.
- **Rotate to SHY**: SSO price < 200-day SMA.
- **Return to SSO**: SSO price crosses back above 200-day SMA.

### Portfolio Construction

Binary: 100% SSO or 100% SHY. Equal weighting between the two regimes.

### Rebalancing Schedule

Daily SMA evaluation. Transitions infrequent due to 200-day lookback.

## Key Indicators / Metrics

- 200-day Simple Moving Average (SSO)
- SSO price relative to SMA
- Warm-up: 200 days

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jun 2015 – Jun 2020 |
| Strategy Sharpe | 0.555 |
| Buy-and-Hold SPY Sharpe | 0.524 |
| Initial Capital | $100,000 |

## Data Requirements

- **Asset Classes**: Leveraged equity ETF (SSO), Treasury ETF (SHY), benchmark (SPY)
- **Resolution**: Daily
- **Warm-up**: 200 days

## Implementation Notes

- Alpha model generates trend-following signals.
- Manual universe selection (SSO, SHY).
- ImmediateExecutionModel for trade execution.
- EqualWeightingPortfolioConstructionModel.
- Python on QuantConnect LEAN.

## Risk Considerations

- 2× leverage magnifies losses during downturns before SMA crossover triggers rotation.
- SMA crossover lags — may miss the initial phase of a crash.
- Whipsaw risk: frequent SMA crosses during range-bound markets generate false signals.
- Leveraged ETF decay (volatility drag) erodes returns over time — daily resetting of leverage.
- Treasury allocation may underperform during equity rallies missed after false sell signals.
- Binary positioning — no partial allocation or gradual risk adjustment.

## Related Strategies

- [VIX Predicts Stock Index Returns](vix-predicts-stock-index-returns.md)
- [Asset Class Trend Following](../momentum/asset-class-trend-following.md)
- [Volatility Effect in Stocks](volatility-effect-in-stocks.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/leveraged-etfs-with-systematic-risk-management)
