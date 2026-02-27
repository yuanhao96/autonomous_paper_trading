# Event Handlers

## Overview

Covers the event-driven programming model for trading algorithms: the types of events an algorithm can handle, the order in which events are processed, and best practices for writing event handler code. Understanding event handlers is the key to writing correct, responsive trading algorithms.

## The Event-Driven Model

Trading algorithms are **event-driven**: rather than running in a continuous loop, the algorithm defines **handler functions** that the engine calls when specific events occur.

```
Engine detects event → Calls appropriate handler → Algorithm processes → Returns control
```

This model:
- Ensures the algorithm only runs when there's something to react to
- Prevents busy-waiting and wasted computation
- Mirrors how live trading works (events arrive asynchronously)

## Core Event Handlers

### on_data (Data Event)

The **primary** event handler. Called whenever new market data is available.

```python
def on_data(self, data):
    """Called with each new data timeslice."""
    if data.contains_key("SPY"):
        price = data["SPY"].close
        if self.should_buy(price):
            self.market_order("SPY", 100)
```

**Key behaviors**:
- In backtesting: called for each historical timeslice in sequence
- In live trading: called when new data arrives from the feed
- With fill-forward enabled: called even when no new trades occurred (stale prices forwarded)
- If processing takes longer than the data period, subsequent data queues up

### on_order_event (Order Event)

Called when an order's status changes: submitted, partially filled, filled, or cancelled.

```python
def on_order_event(self, order_event):
    """Called when order status changes."""
    if order_event.status == OrderStatus.Filled:
        self.log(f"Order filled: {order_event.symbol} "
                 f"at {order_event.fill_price} "
                 f"qty {order_event.fill_quantity}")
```

**Key behaviors**:
- In backtesting: triggered synchronously after data events
- In live trading: triggered asynchronously as broker reports status
- **Warning**: Do not place new orders inside on_order_event to avoid infinite loops

### on_end_of_day (End of Day Event)

Called at the end of each trading day for each subscribed instrument.

```python
def on_end_of_day(self, symbol):
    """Called at market close for each security."""
    self.log(f"{symbol} daily P&L: {self.portfolio[symbol].unrealized_profit}")
```

### on_securities_changed (Universe Change Event)

Called when the algorithm's universe of instruments changes (securities added or removed).

```python
def on_securities_changed(self, changes):
    """Called when universe membership changes."""
    for security in changes.added_securities:
        self.log(f"Added: {security.symbol}")
    for security in changes.removed_securities:
        self.log(f"Removed: {security.symbol}")
        if self.portfolio[security.symbol].invested:
            self.liquidate(security.symbol)
```

**Warning**: Do not add or remove securities inside this handler to avoid recursion.

### on_end_of_algorithm (Shutdown Event)

Called once when the algorithm terminates (backtest complete or live session ends).

```python
def on_end_of_algorithm(self):
    """Called when the algorithm finishes."""
    self.log(f"Final portfolio value: {self.portfolio.total_portfolio_value}")
```

## Specialized Event Handlers

| Handler | Trigger | Use Case |
|---------|---------|----------|
| **on_dividends** | Dividend payment detected | Adjust strategy for dividend income |
| **on_splits** | Stock split detected | Log split events, adjust calculations |
| **on_delistings** | Security delisted | Forced liquidation, remove from universe |
| **on_margin_call** | Margin call triggered | Reduce positions to meet margin requirements |
| **on_assignment** | Option assignment | Handle option exercise obligations |
| **on_warmup_finished** | Warmup period ends | Start trading after indicators are ready |

## Scheduled Events

In addition to reactive event handlers, algorithms can create **scheduled events** that fire at specific times:

```python
# Rebalance every Monday at 10:00 AM
self.schedule.on(
    self.date_rules.every(DayOfWeek.Monday),
    self.time_rules.at(10, 0),
    self.rebalance
)

def rebalance(self):
    """Called by scheduled event."""
    # Monthly rebalancing logic
    ...
```

**Backtesting vs Live**:
- Backtesting: Scheduled events fire when the simulated clock passes the trigger time (in the main thread)
- Live trading: Scheduled events fire in a parallel thread at the actual clock time

## Event Processing Order

Within each timeslice, events are processed in a specific order:

1. **Scheduled events** — Any events whose trigger time has passed
2. **Universe changes** — Securities added/removed
3. **Security price updates** — Latest prices applied
4. **Order fills** — Pending orders checked against new prices
5. **Data handler (on_data)** — Algorithm logic executes
6. **New order processing** — Orders submitted by the algorithm
7. **Portfolio update** — Values recalculated

Understanding this order is important for debugging:
- Your on_data handler sees updated prices (step 3 before step 5)
- Orders from on_data don't fill until the next timeslice (step 6 → step 4 next round)

## Best Practices

### Keep Handlers Lightweight

Event handlers should execute quickly — heavy computation delays subsequent events.

```python
# Good: Quick check and act
def on_data(self, data):
    if self.signal_triggered():
        self.set_holdings("SPY", 1.0)

# Bad: Heavy computation blocking the event loop
def on_data(self, data):
    self.train_ml_model(data)  # Takes minutes
    self.optimize_portfolio()   # Takes more minutes
```

### Don't Place Orders in Order Handlers

Placing orders in on_order_event can create infinite loops (order → event → order → ...).

### Use Scheduled Events for Time-Based Logic

Prefer scheduled events over time checks in on_data:

```python
# Good: Scheduled event
self.schedule.on(date_rules.every_day(), time_rules.at(10, 0), self.rebalance)

# Bad: Time check in every on_data call
def on_data(self, data):
    if self.time.hour == 10 and self.time.minute == 0:
        self.rebalance()  # May fire multiple times or miss
```

### Handle Missing Data Gracefully

Always check for data existence before accessing:

```python
def on_data(self, data):
    if not data.contains_key("SPY"):
        return  # No data for SPY in this timeslice
```

## Financial Application Notes

- The on_data handler is where 90% of strategy logic lives
- Order events enable tracking execution quality (slippage, partial fills)
- Universe change events are essential for dynamic stock screening strategies
- Scheduled events are ideal for periodic rebalancing (daily, weekly, monthly)
- The asynchronous nature of live order events requires defensive coding

## Summary

Event handlers are the core interface between the trading engine and algorithm logic. The main handlers (on_data, on_order_event, on_end_of_day, on_securities_changed) react to market data, order status, daily transitions, and universe changes respectively. Scheduled events enable time-based triggers. Events are processed in a specific order within each timeslice, and best practices include keeping handlers lightweight, avoiding order placement in order handlers, and checking for data existence.

## Source

- Based on [QuantConnect: Key Concepts — Event Handlers](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/event-handlers)
