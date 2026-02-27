# Basic Order Types

## Overview

These are the foundational order types supported by virtually all brokers and exchanges. They form the building blocks for all trading strategies. Mastering when and how to use each type is essential before moving on to advanced order types or complex execution logic.

## Market Order

- **Description**: Buy or sell at the best available price immediately.
- **Execution**: Guaranteed fill in liquid markets; execution price is not guaranteed.
- **Use case**: When speed of execution matters more than the exact price — e.g., responding to a time-sensitive signal or liquidating a position urgently.
- **Risk**: Can slip significantly in illiquid or volatile markets. Large market orders may walk through multiple price levels on the order book.
- **Parameters**: Symbol, Quantity.

**Algo trading example**: A momentum strategy detects a breakout signal and needs to enter a position immediately. A market order ensures the position is opened without delay, accepting the current ask price.

## Limit Order

- **Description**: Buy or sell at a specified price or better.
- **Execution**: Fills only at the limit price or better. Fill is not guaranteed — the market must trade at or through the limit price.
- **Buy limit**: Fills at the limit price or lower.
- **Sell limit**: Fills at the limit price or higher.
- **Use case**: When price control is more important than execution certainty — e.g., entering a position at a specific support level.
- **Risk**: The order may never fill if the market does not reach the limit price. The algorithm must handle unfilled limit orders and decide whether to re-price or cancel.
- **Parameters**: Symbol, Quantity, Limit Price.

**Algo trading example**: A mean-reversion strategy wants to buy a stock that is currently at $52, but only if it pulls back to $50. A buy limit order at $50 waits passively until the price dips to that level.

## Stop Market Order (Stop Loss)

- **Description**: A dormant order that becomes a market order when the stop price is reached.
- **Trigger behavior**:
  - **Buy stop**: Triggers when the market price rises to or above the stop price.
  - **Sell stop**: Triggers when the market price falls to or below the stop price.
- **Use case**: Protect profits or limit losses on an existing position. Also used for breakout entries — placing a buy stop above resistance.
- **Risk**: Gap risk. If the market gaps through the stop price (e.g., overnight or on news), the resulting market order may fill at a price far worse than the stop level.
- **Parameters**: Symbol, Quantity, Stop Price.

**Algo trading example**: An algorithm buys a stock at $100 and immediately places a sell stop at $95 to limit the downside to 5%. If the stock drops to $95, the stop triggers and a market sell order executes at the best available price.

## Stop Limit Order

- **Description**: A dormant order that becomes a limit order (not a market order) when the stop price is reached.
- **Trigger behavior**: Same trigger conditions as a stop market order, but the resulting order has a limit price constraint.
- **Use case**: Combines stop-loss protection with price control. Useful when you want to exit a losing position but refuse to accept a price worse than a defined limit.
- **Risk**: The order may not fill at all if the market gaps through both the stop price and the limit price. This can leave a losing position unprotected.
- **Parameters**: Symbol, Quantity, Stop Price, Limit Price.

**Algo trading example**: An algorithm holds a stock bought at $100 and places a sell stop-limit with a stop at $95 and a limit at $94. If the price falls to $95, a limit sell at $94 is placed. If the price gaps below $94, the order will not fill and the position remains open — the algorithm must detect this and take corrective action.

## Order Type Comparison Table

| Type         | Execution Certainty | Price Control          | Best For                        |
|--------------|---------------------|------------------------|---------------------------------|
| Market       | Highest             | None                   | Immediate entry/exit            |
| Limit        | Lowest              | Highest                | Precise entries, illiquid assets |
| Stop Market  | Medium              | None (after trigger)   | Stop losses, breakout entries   |
| Stop Limit   | Lowest              | High (after trigger)   | Controlled stop exits           |

## Choosing the Right Order Type

- **Liquid, stable markets**: Market orders are generally safe and provide fast execution.
- **Illiquid or wide-spread markets**: Limit orders avoid crossing a wide bid-ask spread.
- **Risk management exits**: Stop market orders provide reliable (though not price-guaranteed) protection.
- **Volatile markets with gap risk**: Stop limit orders give more control but require fallback logic if unfilled.

In practice, most algorithmic strategies use a combination: limit orders for entries (to control cost) and stop market orders for risk management (to ensure exits execute).

## Common Pitfalls

- **Chasing with market orders**: Repeatedly sending market orders after missed limit fills can result in buying at the worst prices. Build re-pricing logic instead.
- **Stale stop orders**: A stop placed days ago may no longer reflect current market conditions. Reassess stop levels regularly based on volatility and position sizing.
- **Ignoring partial fills**: A limit order may fill only a fraction of the desired quantity. The algorithm must track the open remainder and decide whether to adjust the price, wait, or cancel.
- **Assuming instant fills**: Even market orders take time. In fast markets, the fill price may differ from the price at the time of order submission.

---

*Source: Generalized from QuantConnect Trading and Orders documentation.*
