# Execution Models

## Overview

The Execution Model receives portfolio targets from the portfolio construction layer and places
orders to reach those targets. Its primary objective is to **minimize market impact** and achieve
**optimal fill prices** while completing trades within an acceptable timeframe. A well-designed
execution model can meaningfully improve strategy performance, especially for strategies that
trade frequently or in less liquid instruments.

## Available Models

| Model | Description | Best For |
|-------|-------------|----------|
| Immediate Execution | Places market orders to fill targets instantly | Simple strategies, highly liquid markets |
| VWAP | Targets the volume-weighted average price over a time window | Large orders, minimizing market impact |
| TWAP | Distributes execution evenly over a fixed time window | Even distribution, reducing timing risk |
| Standard Deviation | Fills when price is N standard deviations below its recent mean | Mean reversion, dip buying |
| Implementation Shortfall | Minimizes the difference between the decision price and the actual fill | Optimal execution benchmarking |

### Choosing a Model

- **Immediate Execution** is simplest — appropriate for liquid instruments in small size relative
  to average volume. The downside is that market orders accept whatever price is available.
- **VWAP** and **TWAP** are workhorses of institutional execution. They slice large orders into
  smaller child orders over time. VWAP weights slices by expected volume; TWAP distributes evenly.
- **Standard Deviation** execution waits for a dip before filling, trading urgency for a better
  entry price. Useful for mean-reversion strategies.
- **Implementation Shortfall** dynamically balances urgency against market impact, trading more
  aggressively when the price moves away and more passively when it is favorable.

## Key Concepts

### Calculating Order Quantity

The core calculation is straightforward:

```
Order Quantity = Target Quantity - Current Holdings - Pending Order Quantity
```

Always account for open or pending orders when computing the next order. Failing to do so can
result in double-ordering — submitting a second buy before the first has filled, leading to an
oversized position.

### Market Orders vs Limit Orders

- **Market orders** guarantee a fill but not the price. Use when certainty of execution matters.
- **Limit orders** guarantee the price but not a fill. Use when price discipline is paramount.

A common hybrid approach is to start with limit orders and escalate to market orders if the
limit has not filled within a tolerance window.

### Urgency vs Market Impact

Every execution decision involves a fundamental tradeoff: **high urgency** increases market
impact as large orders consume liquidity, while **low urgency** reduces impact but exposes the
order to adverse price movement and information leakage. The optimal balance depends on signal
decay rate, market conditions, and order size relative to available liquidity.

### Order Slicing

For large orders, splitting the parent into smaller child orders reduces the information signal
to other participants, allows the order book to replenish between slices, and lets the algorithm
adapt to changing conditions mid-execution. Slice sizes are typically calibrated as a fraction
of the average volume in each time interval.

## Execution Quality Metrics

Measuring execution quality is critical for continuous improvement. Key metrics include:

- **Slippage** — the difference between the expected fill price (e.g., the mid-quote at decision
  time) and the actual fill price. Positive slippage means you paid more than expected.
- **Market impact** — the price movement attributable to the order itself, measured by comparing
  the price trajectory during execution to a no-trade counterfactual.
- **Implementation shortfall** — total execution cost, defined as the performance difference
  between the actual portfolio and a paper portfolio that filled at the decision price.
- **Fill rate** — the percentage of target quantity actually filled. Relevant for limit-order
  strategies where partial fills are expected.
- **Time to fill** — how long it took to complete the order. Faster is not always better if it
  comes at the cost of higher slippage.

Track these metrics over time and across instruments. Look for patterns: instruments that are
consistently expensive to trade, times of day with worse slippage, or limit orders that fill
too infrequently. Use these observations to refine execution parameters.

---

*Source: QuantConnect Algorithm Framework documentation.*
