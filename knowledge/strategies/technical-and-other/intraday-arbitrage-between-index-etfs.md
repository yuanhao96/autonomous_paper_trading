# Intraday Arbitrage Between Index ETFs

## Overview

Statistical arbitrage between SPY and IVV (both S&P 500 ETFs with >0.99 correlation) using second-level bid/ask data. Enters when the adjusted price ratio diverges beyond a profit threshold, exits when it reverts. Detrends the spread using a 400-period trailing mean to enable multiple trade cycles.

## Academic Reference

- **Papers**: Kakushadze & Serur (2018); Marshall, Nguyen & Visaltanachoti (2010)
- Arbitrage: "When the bid price of ETF A diverts high enough away from the ask price of ETF B such that their quotient reaches a threshold."

## Strategy Logic

### Universe Selection

2 S&P 500 index ETFs: SPY and IVV. Daily return correlation > 0.99.

### Signal Generation

1. Monitor intraday bid/ask spreads at second-level resolution.
2. Detrend spread using 400-period trailing mean.
3. Calculate adjusted ratio: (bid_A / ask_B) − trailing_mean.

### Entry / Exit Rules

- **Enter**: When adjusted ratio exceeds profit threshold (default 2%) AND persists for order_delay timesteps (default 3).
- **Exit**: When spread reverts (bid_B ≥ ask_A) for the same delay duration.
- **Position**: Long one ETF, short the other simultaneously.
- **Excluded**: Within 5 minutes of market open/close.

### Portfolio Construction

EqualWeightingPortfolioConstructionModel. Long/short pair. $50,000 initial capital.

### Rebalancing Schedule

No explicit rebalancing. Continuous monitoring at second resolution.

## Key Indicators / Metrics

- Bid/ask price ratios
- 400-period trailing mean (detrending)
- Profit threshold: 2%
- Order delay: 3 timesteps
- QuoteBarConsolidator for L1 data

## Backtest Performance

| Period | Strategy Sharpe | SPY Sharpe |
|--------|----------------|------------|
| Full (2015–2020) | -0.447 | 0.732 |
| Fall 2015 crisis | 2.837 | — |
| 2020 crash | -4.196 | — |
| 2020 recovery | -3.443 | — |

## Data Requirements

- **Asset Classes**: US equity ETFs (SPY, IVV)
- **Resolution**: Second-level quote bars (bid/ask)
- **Lookback**: 400-period window
- **Data Type**: L1 bid/ask quotes

## Implementation Notes

- ArbitrageAlphaModel with QuoteBarConsolidator.
- Real-time spread updates at second resolution.
- Configurable parameters: order_delay, profit_pct_threshold, window_size.
- Python on QuantConnect LEAN.

## Risk Considerations

- Negative overall Sharpe (−0.447) — strategy loses money over full period.
- SPY-IVV spread is extremely tight — 2% threshold may rarely be hit in practice.
- Second-resolution data creates massive computational overhead.
- Market microstructure risks during volatile conditions.
- Parameter sensitivity: order_delay and threshold critically affect performance.
- Severe drawdowns during 2020 crash (Sharpe −4.196).
- Execution at quoted bid/ask may not be achievable in practice.

## Related Strategies

- [Pairs Trading with Stocks](../mean-reversion-and-pairs-trading/pairs-trading-with-stocks.md)
- [Optimal Pairs Trading](../mean-reversion-and-pairs-trading/optimal-pairs-trading.md)
- [Paired Switching](paired-switching.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/intraday-arbitrage-between-index-etfs)
