# Portfolio Construction Models

## Overview

Portfolio Construction converts trading signals (commonly called Insights) into concrete position
targets. Each target specifies a symbol and a desired quantity, answering the central question:
**"How many shares or contracts should I hold based on the current signals?"**

Sitting between the alpha/signal generation layer and the execution layer, the portfolio
construction model receives active signals, evaluates them against current portfolio state and
account equity, and emits target positions for the execution layer to fulfill.

## Target Objects

A **PortfolioTarget** is a simple data structure containing:

- **Symbol** — the asset identifier (ticker, contract, etc.)
- **Quantity** — the desired number of shares/contracts to hold

Targets can be specified in two ways:

1. **Direct quantity** — an absolute number of shares or contracts (e.g., hold 500 shares of AAPL).
2. **Portfolio percentage** — a fraction of total portfolio value (e.g., allocate 5% to AAPL). The
   framework converts this to a share count based on current price and account equity.

Percentage-based targets are generally preferred for margin accounts and strategies that scale
with account size. Direct quantity targets suit external models or fixed-lot instruments.

## Available Models

| Model | Description | Best For |
|-------|-------------|----------|
| Null | Produces no targets; signals are analyzed but no positions are taken | Alpha model evaluation and signal research |
| Equal Weighting | Allocates equal capital across all active signals | Universe rotation strategies, simple momentum |
| Mean-Variance Optimization | Minimizes portfolio variance for a given expected return (Markowitz) | Classical portfolio optimization |
| Black-Litterman | Combines market equilibrium weights with signal-derived views | Multi-alpha strategies, blending diverse models |
| Risk Parity | Allocates so each position contributes equal risk to the portfolio | Balanced risk allocation across asset classes |
| Kelly Criterion | Sizes positions to maximize the geometric growth rate of capital | High-confidence signals with known edge |

### Choosing a Model

- **Equal Weighting** is a strong default. It is transparent, easy to debug, and avoids
  concentration risk. Start here unless you have a specific reason not to.
- **Mean-Variance Optimization** is theoretically elegant but sensitive to estimation error in
  expected returns and covariances. Use with regularization or shrinkage estimators.
- **Black-Litterman** is well-suited when multiple alpha models produce different views on the
  same universe. It blends those views with a market prior in a principled way.
- **Risk Parity** is appropriate for multi-asset portfolios where you want volatility-balanced
  exposure rather than capital-balanced exposure.
- **Kelly Criterion** can produce aggressive sizes. In practice, fractional Kelly (e.g.,
  half-Kelly) is used to reduce variance at the cost of slightly lower long-run growth.

## Key Concepts

### Targets Are Aspirational

Do not assume orders fill immediately. A target of 1,000 shares does not mean you hold 1,000 shares
right now — it means the execution layer will work toward that target. The portfolio construction
model should be stateless with respect to fill status and simply emit what the ideal portfolio
looks like given the current signals.

### Handling Universe Changes

Securities may be added to or removed from the trading universe at any time. The construction model
must handle both cases gracefully:

- **Additions**: new signals appear; the model should incorporate them and rebalance if needed.
- **Removals**: signals expire or securities are delisted; the model should emit a zero-quantity
  target to flatten the position.

### Percentage-Based Targets and Margin

When using percentage-based targets in a margin account, ensure the total allocation does not
exceed the available margin. A common safeguard is to cap total allocation at some fraction of
buying power (e.g., 95%) to leave a cash buffer.

### Rebalancing Triggers

Rebalancing can be triggered by several mechanisms:

- **Time-based** — rebalance on a fixed schedule (daily, weekly, monthly).
- **Threshold-based** — rebalance when any position drifts more than X% from its target weight.
- **Signal-based** — rebalance whenever a new signal is generated or an existing one changes.

## Implementation Considerations

- **Position sizing relative to equity**: Always compute position sizes as a function of current
  account equity, not initial capital. This ensures the strategy scales with gains and losses.
- **Cash buffer**: Reserve a portion of equity (e.g., 2-5%) as a cash buffer to absorb margin
  fluctuations, fee deductions, and overnight gap risk.
- **Transaction cost awareness**: Frequent rebalancing incurs transaction costs. Consider minimum
  trade thresholds — skip rebalancing a position if the adjustment is smaller than some dollar
  or percentage threshold.
- **Turnover constraints**: High turnover erodes returns through commissions, slippage, and taxes.
  Impose turnover limits or penalize turnover in the optimization objective to keep trading costs
  in check.

---

*Source: QuantConnect Algorithm Framework documentation.*
