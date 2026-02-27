# Volatility Risk Premium Effect

## Overview

Harvests the volatility risk premium by selling at-the-money (ATM) straddles on SPY and buying a protective 15% out-of-the-money (OTM) put. The premium collected from selling options exceeds the cost of protection, capturing the spread between implied and realized volatility. Monthly rebalancing with hold-to-expiration.

## Academic Reference

- **Paper**: Quantpedia — "Volatility Risk Premium Effect"

## Strategy Logic

### Universe Selection

Single underlying: SPY (S&P 500 ETF). Options with 0–31 days to maturity, strikes -20 to +20 from current price.

### Signal Generation

No directional signal — systematically sells ATM volatility premium each month.

### Entry / Exit Rules

- **Sell**: 1 ATM call + 1 ATM put (ATM straddle).
- **Buy**: 1 OTM put at 85% of underlying price (downside protection).
- **Exit**: Hold until expiration. Sell underlying after option exercise/assignment.
- Monthly rebalancing cycle.

### Portfolio Construction

Three-leg option position: short ATM call, short ATM put, long OTM put. Uses `OptionStrategies.STRADDLE` for multi-leg ordering.

### Rebalancing Schedule

Monthly.

## Key Indicators / Metrics

- Underlying price (strike selection)
- Time to expiration (1-month target)
- Implied volatility (embedded in premium)
- ATM strike and 85% OTM strike

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Feb 2017 – Mar 2017 |
| Initial Capital | $500,000 |
| Resolution | Minute |

## Data Requirements

- **Asset Classes**: US equity ETF (SPY) + options
- **Resolution**: Minute-level option chain data
- **Data**: Strike prices, expiration dates, option greeks

## Implementation Notes

- Option universe filtered: strikes -20 to +20, 0–31 days to expiration, includes weeklies.
- `sorted()` function locates closest matching contracts when exact specs unavailable.
- `OptionStrategies.STRADDLE` for multi-leg execution.
- Python on QuantConnect LEAN.

## Risk Considerations

- Unlimited upside loss exposure on short calls if market rallies sharply.
- Downside protection capped by OTM put (15% gap between ATM and protection).
- Gap risk between monthly rebalancing periods.
- Very short backtest (1 month) — statistically meaningless.
- Liquidity constraints in weekly options during market stress.
- Assignment risk on short options near expiration.
- Volatility premium may disappear during low-vol regimes.

## Related Strategies

- [VIX Predicts Stock Index Returns](vix-predicts-stock-index-returns.md)
- [Exploiting Term Structure of VIX Futures](exploiting-term-structure-of-vix-futures.md)
- [Volatility Effect in Stocks](volatility-effect-in-stocks.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/volatility-risk-premium-effect)
