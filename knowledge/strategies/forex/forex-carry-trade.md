# Forex Carry Trade

## Overview

Classic carry trade strategy that goes long the highest-yielding currency and shorts the lowest-yielding currency based on central bank interest rates. Monthly rebalancing across 9 currency pairs using Nasdaq Data Link interest rate data.

## Academic Reference

- **Paper**: Quantpedia — "FX Carry Trade"

## Strategy Logic

### Universe Selection

9 currency pairs: USDEUR, USDZAR, USDAUD, USDJPY, USDTRY, USDINR, USDCNY, USDMXN, USDCAD. Data from OANDA.

### Signal Generation

Sort currency pairs by central bank interest rate (sourced from Nasdaq Data Link BCB dataset). Identify highest and lowest yielding currencies.

### Entry / Exit Rules

- **Long**: Currency with highest interest rate (50% allocation).
- **Short**: Currency with lowest interest rate (−50% allocation).
- **Exit**: Reconstitute at monthly rebalance.

### Portfolio Construction

Equal-weight opposing positions: 50% long high-rate, 50% short low-rate. Starting capital: $25,000.

### Rebalancing Schedule

Monthly, first trading day.

## Key Indicators / Metrics

- Central bank interest rates (primary signal)
- No technical indicators — purely fundamental

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2008 – Dec 2022 |
| Initial Capital | $25,000 |
| Resolution | Daily (OANDA) |

## Data Requirements

- **Asset Classes**: Forex (9 pairs)
- **Resolution**: Daily (OANDA)
- **External Data**: Central bank interest rates from Nasdaq Data Link

## Implementation Notes

- `AddForex()` for currency pair subscriptions.
- `AddData(NasdaqDataLink)` for interest rate data.
- Scheduled monthly rebalancing.
- Python on QuantConnect LEAN.

## Risk Considerations

- **Critical**: Interest rate dataset discontinued by Nasdaq Data Link in 2016 — live implementation infeasible with original source.
- Carry trades are vulnerable to sudden currency depreciation (carry unwind during risk-off events).
- Emerging market currencies (TRY, ZAR, MXN, INR) have significant political and liquidity risk.
- Interest rate differentials can narrow quickly, eliminating the carry advantage.
- Currency intervention by central banks can cause sharp reversals.
- No hedging or stop-loss mechanisms.

## Related Strategies

- [Risk Premia in Forex Markets](risk-premia-in-forex-markets.md)
- [Forex Momentum](../momentum/forex-momentum.md)
- [Combining Mean Reversion and Momentum in Forex Market](combining-mean-reversion-and-momentum-in-forex.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/forex-carry-trade)
