# Fill Models

## Overview

Fill models simulate how orders get executed -- at what price, in what quantity, and over what timeframe. They determine whether orders are filled completely, partially, or rejected. Realistic fill modeling prevents backtests from assuming executions that would not occur in live markets.

## Order Fill Types

- **Complete fill:** Entire order quantity filled at once. Typical for small orders in liquid markets.
- **Partial fill:** Only a portion is filled per time step; the remainder stays open or is canceled. Common for large orders or illiquid securities.
- **No fill / rejection:** Order cannot be executed. Limit orders may never reach the limit price; market orders may lack sufficient volume.

## Fill Price Determination

### Market Orders

- Fill at current ask price (for buys) or bid price (for sells)
- Plus any slippage model adjustment on top of the quoted price
- Large orders may gap through multiple price levels in the order book

### Limit Orders

- Fill only when the market price reaches or betters the limit price
- Fill price is the limit price or better (price improvement is possible)
- May result in partial fills if insufficient volume exists at the limit level

### Stop Orders

- Convert to a market order when the stop price is touched or breached
- Fill at the next available price after triggering
- **Gap risk:** the fill may be significantly worse than the stop price, especially overnight or around news events

### Stop-Limit Orders

- Convert to a limit order when the stop price is touched
- May not fill at all if the price gaps through both the stop and the limit
- Provides price protection at the cost of execution certainty

## Fill Timing

- **Immediate (same-bar):** Assumes the order fills on the same bar it was placed. Simple but can introduce look-ahead bias.
- **Next-bar open:** Fills at the open of the next bar. More conservative and avoids peeking at the current bar's close.
- **Intrabar simulation:** Models fill within a bar using OHLC data and volume distribution. Most realistic but complex.

## Spread Modeling

- Fill models should incorporate the bid-ask spread for realistic pricing
- Buy orders fill at or near the ask; sell orders fill at or near the bid
- The spread widens during low liquidity and high volatility periods

## Volume Constraints

Realistic fill models limit the percentage of a bar's volume that a single order can consume. A common constraint is filling no more than 1-5% of the bar's total volume. Orders exceeding this threshold receive a partial fill, with the remainder carried forward.

## Asset-Specific Fill Behavior

| Asset | Fill Characteristics |
|-------|---------------------|
| Equities | Partial fills common; exchange-specific routing and priority rules |
| Forex | Usually complete fills in spot market; dealer/ECN model variations |
| Futures | Exchange-matched; partial fills possible at limit prices |
| Crypto | Partial fills on limit orders; significant slippage on large market orders |
| Options | Lower liquidity; wider spreads; partial fills common; assignment risk |

## Best Practices

- **Use next-bar fills** as a default to avoid look-ahead bias in backtesting
- **Limit volume participation** to a realistic fraction of historical volume
- **Model partial fills** for strategies trading less liquid instruments
- **Incorporate spread costs** even when using trade-price or mid-price data
- **Test with conservative fill assumptions** before deploying capital
- **Track fill rates** in live trading and compare against backtest assumptions

## Common Pitfalls

1. **Assuming immediate fills at mid-price:** Overstates returns by ignoring the spread
2. **Ignoring volume constraints:** Backtests may assume fills in quantities that exceed real market depth
3. **Perfect limit order fills:** Assuming every limit order touching the price gets filled ignores queue priority
4. **No partial fill modeling:** Strategies designed for illiquid markets need partial fill logic to be realistic

---

Source: Generalized from QuantConnect Reality Modeling documentation.
