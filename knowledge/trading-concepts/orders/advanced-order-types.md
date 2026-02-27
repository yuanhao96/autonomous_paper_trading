# Advanced Order Types

## Overview

Advanced order types provide more sophisticated execution capabilities beyond basic market and limit orders. They enable trailing protection, time-specific execution, conditional triggers, and multi-leg strategies. Not all brokers or exchanges support every advanced order type — always verify availability before relying on them in production algorithms.

## Trailing Stop Order

- **Description**: A stop order whose trigger price automatically adjusts as the market moves favorably, trailing by a fixed dollar amount or percentage.
- **Long position**: The trailing stop sits a fixed distance below the highest price reached since the order was placed. It only moves up, never down.
- **Short position**: The trailing stop sits a fixed distance above the lowest price reached since the order was placed. It only moves down, never up.
- **Use case**: Lock in profits on a winning trade while still allowing further upside. Ideal for trend-following strategies.
- **Parameters**: Symbol, Quantity, Trail Amount (absolute $ or %).
- **Example**: Buy stock at $100 with a trailing stop of $5. The initial stop is at $95. If the price rises to $110, the stop rises to $105. If the price then falls from $110 to $105, the stop triggers and a market sell executes.
- **Risk**: In choppy markets, the trailing stop may trigger on a temporary dip before the price resumes its trend. Does not protect against gap risk.

## Market On Open (MOO)

- **Description**: An order that executes at the official opening auction price of the trading session.
- **Timing**: Must be submitted before the market opens. Orders submitted after the open are typically rejected.
- **Use case**: Overnight signal strategies that compute trades after the close and need execution at the next open. Also used for daily rebalancing.
- **Risk**: The opening price can gap significantly from the previous close, especially after overnight news events.
- **Parameters**: Symbol, Quantity.

## Market On Close (MOC)

- **Description**: An order that executes at the official closing auction price.
- **Timing**: Must be submitted before the exchange's MOC cutoff time (e.g., 15:50 ET for NYSE). Late submissions are rejected.
- **Use case**: End-of-day rebalancing, index tracking strategies that benchmark to closing prices, and portfolio adjustments that should reflect end-of-day valuations.
- **Risk**: May be rejected if submitted too close to market close. Closing auctions can be volatile, especially on index rebalance days.
- **Parameters**: Symbol, Quantity.

## Limit if Touched (LIT)

- **Description**: A dormant order that becomes a limit order when a specified trigger price is touched. Unlike a stop-limit, this is used for entries at favorable prices.
- **Buy LIT**: Trigger price is set below the current market price. When the market dips to the trigger, a buy limit order is placed at the trigger price or better.
- **Sell LIT**: Trigger price is set above the current market price. When the market rises to the trigger, a sell limit order is placed at the trigger price or better.
- **Use case**: Enter positions at better prices without the immediacy of a market order. Useful for algorithms that want to buy dips or sell rallies with price protection.
- **Parameters**: Symbol, Quantity, Trigger Price, Limit Price.

## Combo Orders (Multi-Leg)

Multi-leg orders allow simultaneous execution of related trades as a single atomic unit:

- **Combo Market**: All legs execute at market prices simultaneously. Simplest but least price control.
- **Combo Limit**: A net debit or credit constraint applies across all legs combined. The total cost or proceeds must meet the limit.
- **Combo Leg Limit**: Individual limit prices are specified for each leg independently.
- **Use case**: Options spreads (verticals, iron condors, butterflies), pairs trades, hedged equity entries, and basis trades.
- **Risk**: Partial fills on individual legs can create unwanted exposure. Ensure the broker supports atomic execution or have logic to manage leg risk.

## Option Exercise Orders

- **Description**: Explicitly exercise a long options contract before its expiration date (early exercise).
- **Use case**: Capture a pending dividend on deep in-the-money calls, manage assignment risk, or close out a position by taking delivery of the underlying.
- **Risk**: Forfeiting any remaining time value in the option. Early exercise is generally suboptimal unless specific conditions (dividend capture, deep ITM with no time value) are met.
- **Parameters**: Symbol (option contract), Quantity.

## Iceberg / Hidden Orders

- **Description**: Only a portion of the total order quantity is displayed to the market at any time. As the visible portion fills, the next tranche is automatically revealed.
- **Use case**: Executing large institutional orders without signaling intent to the broader market, reducing market impact.
- **Risk**: Slower execution since only a fraction of the order is visible. Other participants may detect iceberg patterns through order flow analysis.
- **Parameters**: Symbol, Quantity, Display Quantity (visible portion).

## Comparison Table

| Type             | Trigger   | Price Control | Complexity | Best For                        |
|------------------|-----------|---------------|------------|---------------------------------|
| Trailing Stop    | Dynamic   | None          | Medium     | Trend-following profit protection |
| MOO              | Time (open)  | None       | Low        | Opening price execution         |
| MOC              | Time (close) | None       | Low        | Closing price execution         |
| Limit if Touched | Price     | High          | Medium     | Better entry prices             |
| Combo            | Simultaneous | Varies     | High       | Multi-leg and hedged strategies |
| Iceberg          | Continuous | Varies       | Medium     | Large orders with low impact    |

## Choosing Advanced Order Types

- Use **trailing stops** when riding a trend and you want automatic profit protection without constant re-pricing.
- Use **MOO/MOC** when your strategy logic aligns with session boundaries and you want official auction prices.
- Use **LIT orders** when you want to enter at a better price but only if the market actually reaches that level.
- Use **combo orders** for any strategy involving multiple correlated legs that must execute together.
- Use **iceberg orders** when order size is large relative to average volume and market impact is a concern.

---

*Source: Generalized from QuantConnect Trading and Orders documentation.*
