# Order Types & Trading — Key Concepts

## Overview

Orders are instructions to buy or sell securities. Understanding order types, lifecycle, and management is critical for algorithmic trading. The right order type balances execution certainty against price control. Every trading algorithm, regardless of strategy, must correctly construct, submit, monitor, and manage orders to operate reliably.

## Order Lifecycle

1. **Created**: Algorithm generates an order object with all required parameters (symbol, quantity, type, price constraints).
2. **Submitted**: Order is transmitted to the broker or exchange for processing.
3. **Working**: Order is live on the exchange order book, waiting to be matched and filled.
4. **Partially Filled**: Some of the requested quantity has been executed; the remainder is still working on the book.
5. **Filled**: The complete order quantity has been executed. The order is now terminal.
6. **Cancelled**: The order was withdrawn by the algorithm or broker before a complete fill.
7. **Invalid/Rejected**: The order failed validation — insufficient funds, invalid parameters, market closed, or compliance violation.

Understanding the lifecycle is essential for state management. Algorithms should track each order through these states and react appropriately to transitions (e.g., updating position tracking on partial fills).

## Order Properties

| Property       | Description                                                    |
|----------------|----------------------------------------------------------------|
| Symbol         | The security identifier to trade (ticker, ISIN, or internal ID) |
| Quantity       | Number of shares/contracts (positive = buy, negative = sell)   |
| Type           | Market, Limit, Stop Market, Stop Limit, Trailing Stop, etc.   |
| Direction      | Buy or Sell (derived from quantity sign in many systems)       |
| Time in Force  | GTC, Day, IOC, FOK, GTD — controls order expiration behavior  |
| Tag            | Optional string label for tracking, grouping, or debugging    |
| Limit Price    | Maximum buy price or minimum sell price (limit and stop-limit orders) |
| Stop Price     | Trigger price that activates a stop or stop-limit order        |

## Time in Force

| TIF                       | Description                                                         |
|---------------------------|---------------------------------------------------------------------|
| Day                       | Expires at the end of the current trading session                   |
| GTC (Good Til Canceled)   | Remains active until explicitly filled or canceled                  |
| IOC (Immediate or Cancel) | Fill whatever quantity is available immediately; cancel the rest     |
| FOK (Fill or Kill)        | Fill the entire quantity immediately or cancel the whole order       |
| GTD (Good Til Date)       | Remains active until a specified expiration date                    |

Choosing the correct time-in-force prevents stale orders from lingering and executing at undesirable times. Day orders are the safest default; GTC orders require active monitoring.

## Order Events

Algorithms should subscribe to and handle all of these event types:

- **OrderSubmitted**: Confirmation that the broker has accepted the order for processing.
- **OrderFilled**: A partial or complete fill has occurred. Contains fill price, fill quantity, and fees.
- **OrderCanceled**: The order has been successfully canceled. No further fills will occur.
- **OrderUpdated**: The order's parameters (price, quantity) have been modified in-place.
- **OrderInvalid**: The order was rejected. The event typically contains a reason string for diagnostics.

## Order Management

- **Update**: Modify a working order's limit price, stop price, or quantity without canceling it. This preserves queue priority on some exchanges.
- **Cancel**: Withdraw a working order entirely. Always confirm cancellation via event before assuming the order is dead.
- **Replace**: Cancel the existing order and resubmit with new parameters. This is a two-step operation and may lose queue priority.

## Fees and Costs

Each order execution incurs costs that erode returns:

- **Brokerage commission**: Per-share or per-trade fee charged by the broker.
- **Exchange fees**: Charges from the exchange for matching and clearing.
- **Regulatory fees**: SEC fees, FINRA TAF (US), stamp duty (UK), etc.
- **Slippage**: The implicit cost when the execution price differs from the expected price. This is especially significant for market orders in fast or illiquid markets.

Algorithms should account for estimated fees when calculating expected profit from a trade and when sizing positions.

## Best Practices

- Use limit orders for illiquid securities to avoid excessive slippage.
- Set appropriate time-in-force values to prevent stale orders from executing unexpectedly.
- Monitor partial fills and decide whether to let the remainder work or cancel it.
- Log all order events with timestamps for debugging, audit trails, and performance analysis.
- Handle rejected orders gracefully — implement retry logic with exponential backoff or fallback order types.
- Validate order parameters before submission to minimize rejections.
- Track net position in real time as fills arrive to avoid unintended exposure.
- Use order tags or IDs to correlate orders with the strategy or signal that generated them.

---

*Source: Generalized from QuantConnect Trading and Orders documentation.*
