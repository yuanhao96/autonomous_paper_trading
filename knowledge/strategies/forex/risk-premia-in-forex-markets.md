# Risk Premia in Forex Markets

## Overview

Trades forex pairs based on return distribution skewness as a risk premium signal. Goes long pairs with negative skewness (< −0.6) and shorts pairs with positive skewness (> 0.6) over a 30-day lookback. Weekly rebalancing across 4 major currency pairs.

## Academic Reference

- **Paper**: "Risk Premia: Asymmetric Tail Risks and Excess Returns" — Lemperiere, Deremble, Nguyen, Seager, Potters & Bouchaud
- Finding: "Risk premium is indeed strongly correlated with the skewness of a strategy."

## Strategy Logic

### Universe Selection

4 currency pairs: EURUSD, AUDUSD, USDCAD, USDJPY. Data from FXCM.

### Signal Generation

Compute 30-day historical skewness of closing prices:
Skewness = Σ(price − mean)³ / (n × σ³)

### Entry / Exit Rules

- **Long**: Skewness < −0.6 (negatively skewed — risk premium opportunity).
- **Short**: Skewness > +0.6 (positively skewed).
- **Exit**: Pairs not meeting criteria at weekly rebalance are liquidated.

### Portfolio Construction

Equal-weight across all active positions. Position sizing: 1/count for longs, −1/count for shorts.

### Rebalancing Schedule

Weekly (7-day intervals).

## Key Indicators / Metrics

- Skewness of price distribution (30-day lookback)
- Thresholds: −0.6 / +0.6
- Historical volatility (standard deviation component)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2009 – 2019 |
| Annual Return | −0.330% |
| Initial Capital | $100,000 |

## Data Requirements

- **Asset Classes**: Forex (4 pairs)
- **Resolution**: Hourly subscription, daily lookback
- **Lookback**: 30 days of daily closes

## Implementation Notes

- `add_forex()` for subscriptions.
- `history()` for 30-day lookback retrieval.
- `set_holdings()` for position management.
- Duplicate-free price series handling.
- Python on QuantConnect LEAN.

## Risk Considerations

- Negative annual return (−0.330%) — strategy does not work as implemented.
- Only 4 currency pairs — severe concentration risk.
- Fixed thresholds (−0.6/+0.6) may not adapt to changing market regimes.
- 30-day skewness window may be too short for reliable estimation.
- Skewness is inherently unstable and noisy in small samples.
- Tail risk paradox: targeting negative skewness while generating negative returns.
- Authors recommend testing alternative symbols, thresholds, and longer lookbacks.

## Related Strategies

- [Forex Carry Trade](forex-carry-trade.md)
- [Combining Mean Reversion and Momentum in Forex Market](combining-mean-reversion-and-momentum-in-forex.md)
- [Forex Momentum](../momentum/forex-momentum.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/risk-premia-in-forex-markets)
