# Forex Momentum

## Overview

Applies cross-sectional momentum to foreign exchange markets. Ranks 15 currency pairs by 12-month momentum and goes long the top 3 while shorting the bottom 3.

## Academic Reference

- **Paper**: "FX Momentum" — Quantpedia

## Strategy Logic

### Universe Selection

15 forex pairs (all USD-quoted):
USDAUD, USDCAD, USDCHF, USDEUR, USDGBP, USDHKD, USDJPY, USDDKK, USDCZK, USDZAR, USDSEK, USDSAR, USDNOK, USDMXN, USDHUF.

Data source: OANDA.

### Signal Generation

Momentum (MOM) indicator with 12-month lookback (252 trading days). Rank all 15 pairs by momentum.

### Entry / Exit Rules

- **Long**: Top 3 currency pairs by 12-month momentum.
- **Short**: Bottom 3 currency pairs by 12-month momentum.
- **Exit**: Securities no longer in top/bottom 3 are closed at rebalance.

### Portfolio Construction

Equal-weight: 1/3 allocation per position within each leg.

### Rebalancing Schedule

Monthly, at market open (OANDA). USDEUR used as schedule anchor.

## Key Indicators / Metrics

- Momentum (MOM): 252-day lookback
- Warm-up period: 252 trading days

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2006–2018 |
| Initial Capital | $100,000 |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: Forex (15 pairs)
- **Resolution**: Daily
- **Lookback Period**: 252 trading days (12 months)
- **Data Source**: OANDA

## Implementation Notes

- `self.add_forex()` subscribes to currency pairs.
- `self.mom()` computes momentum per pair.
- `self.schedule` for monthly rebalancing triggers.
- State maintained via portfolio holdings dictionary.

## Risk Considerations

- No explicit stop-loss or risk management.
- Transaction costs not detailed — forex spreads matter.
- No hedging or diversification beyond momentum ranking.
- Some pairs (USDHKD, USDSAR) are pegged — limited momentum potential.
- 12-month lookback may be too long for fast-moving FX markets.
- Currency intervention risk in emerging market pairs (USDMXN, USDHUF, USDCZK).

## Related Strategies

- [The Momentum Strategy Based on the Low Frequency Component of Forex Market](momentum-strategy-low-frequency-forex.md)
- [Forex Carry Trade](../forex/forex-carry-trade.md)
- [Risk Premia in Forex Markets](../forex/risk-premia-in-forex-markets.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/forex-momentum)
