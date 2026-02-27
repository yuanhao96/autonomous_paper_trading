# Algorithm Framework Overview

The Algorithm Framework is a modular architecture for building algorithmic trading strategies. Instead of writing monolithic code where signal generation, position sizing, risk management, and order execution are interleaved, the framework separates these concerns into five distinct modules that communicate through well-defined interfaces. Each module has a single responsibility, making strategies easier to develop, test, and maintain.

## Core Modules

The framework is composed of five pluggable modules, each handling one stage of the trading pipeline.

| Module | Responsibility | Input | Output |
|---|---|---|---|
| **Universe Selection** | Decide *what* to trade | Market data, filters | Active asset universe |
| **Alpha Model** | Decide *when and which direction* to trade | Price/data for universe | Insight objects |
| **Portfolio Construction** | Decide *how much* to trade | Insights | Portfolio targets |
| **Risk Management** | Decide *what to constrain* | Portfolio targets | Adjusted targets |
| **Execution Model** | Decide *how* to trade | Final targets | Orders |

## Data Flow

Data flows through the modules in a strict, linear pipeline on each trading iteration:

```
Universe Selection ──▶ Alpha Model ──▶ Portfolio Construction ──▶ Risk Management ──▶ Execution
      │                     │                    │                       │                 │
  Asset universe        Insights          Raw targets            Adjusted targets       Orders
```

1. **Universe Selection** filters the full market down to a working set of assets based on fundamental screens, liquidity thresholds, or custom criteria. The selected universe is passed to subsequent modules.
2. **Alpha Model** receives market data for the active universe and generates **Insight** objects representing directional forecasts.
3. **Portfolio Construction** consumes Insights and translates them into **PortfolioTarget** objects — concrete position sizes expressed as quantities or portfolio weights.
4. **Risk Management** reviews the proposed targets and may reduce, eliminate, or otherwise adjust them to enforce drawdown limits, concentration caps, or volatility constraints.
5. **Execution Model** receives the final adjusted targets and determines how to execute them, choosing order types, timing, and splitting logic.

## Key Objects

### Insight

An Insight is the fundamental output of the Alpha Model. It represents a directional view on a specific asset over a defined time horizon.

| Field | Description |
|---|---|
| **Symbol** | The asset the insight pertains to |
| **Direction** | Up, Down, or Flat |
| **Magnitude** | Expected percentage move (optional) |
| **Confidence** | Probability estimate from 0.0 to 1.0 (optional) |
| **Period** | Time horizon over which the insight is valid |
| **Weight** | Relative importance when multiple insights compete (optional) |

Insights decouple signal generation from position sizing. The Alpha Model does not need to know anything about account size, leverage, or risk limits — it simply expresses a view. Downstream modules interpret that view according to their own logic.

### PortfolioTarget

A PortfolioTarget is the output of the Portfolio Construction module and the input to Risk Management.

| Field | Description |
|---|---|
| **Symbol** | The asset to hold |
| **Quantity** | Target number of shares/contracts/units to hold |

Targets are expressed as absolute desired holdings, not as deltas. The execution layer computes the difference between current and target positions to determine the orders needed.

## Module Communication

Modules communicate exclusively through the objects described above — there is no shared mutable state or back-channel. This contract-based design means:

- **Universe Selection** publishes a set of symbols.
- **Alpha Model** publishes a list of Insights keyed by symbol.
- **Portfolio Construction** consumes Insights and publishes a list of PortfolioTargets.
- **Risk Management** consumes PortfolioTargets and publishes an adjusted list of PortfolioTargets.
- **Execution Model** consumes the final PortfolioTargets and submits orders.

Because each boundary is a well-typed collection of simple objects, modules can be developed and unit-tested in isolation.

## Advantages of Modular Design

- **Swappable components.** Replace an equal-weight portfolio construction model with a mean-variance optimizer without touching the Alpha Model or risk layer.
- **Independent testability.** Unit-test an Alpha Model by feeding it historical data and asserting on the Insights it produces, with no need for a full backtest environment.
- **Reusable building blocks.** A momentum Alpha Model can be paired with different risk management modules across multiple strategies.
- **Clear separation of concerns.** Researchers focus on signal generation; engineers focus on execution; risk managers define constraints — all within their own module.
- **Composability.** Multiple Alpha Models can run simultaneously, with the Portfolio Construction module merging their Insights into a unified portfolio.

## Framework vs. Monolithic Approach

Not every strategy benefits from a full modular framework. The table below provides guidance on when each approach is most appropriate.

| Consideration | Framework Approach | Monolithic Approach |
|---|---|---|
| **Portfolio rebalancing strategies** | Excellent fit — construction and risk modules handle periodic rebalancing naturally | Requires manual rebalancing logic |
| **Multi-factor / multi-alpha strategies** | Designed for this — each alpha is a separate module whose insights are merged | Factors become entangled in a single code path |
| **Ranking-based strategies** | Alpha Model ranks assets; construction model allocates by rank | Workable but less organized |
| **Simple event-driven strategies** | Over-engineered — the pipeline adds overhead for a single trigger-and-trade pattern | Better fit — direct event handling is clearer |
| **Highly stateful strategies** | May need shared state that breaks module boundaries | Easier to manage internal state in one place |
| **Rapid prototyping** | Slower initial setup due to boilerplate | Faster to get a first version running |

As a rule of thumb, if a strategy involves selecting from a universe, scoring assets, sizing positions, and managing risk as logically distinct steps, the framework approach will pay dividends in clarity and maintainability. If the strategy is a single-asset, single-signal system with bespoke execution logic, a monolithic design may be simpler and sufficient.

---

*Content generalized from [QuantConnect / LEAN documentation](https://www.quantconnect.com/docs) for use in any algorithmic trading research or agent development context.*
