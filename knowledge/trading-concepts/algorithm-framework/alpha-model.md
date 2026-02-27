# Alpha Model (Signal Generation)

## Overview

The Alpha Model generates trading signals — called **Insights** — that predict future
asset behavior. It is the core intelligence of the algorithm framework. While universe
selection decides *what* to watch and portfolio construction decides *how much* to hold,
the alpha model decides *when* and *in which direction* to trade. A well-structured
alpha model produces standardized signal objects that downstream components can consume
without knowledge of the underlying strategy logic.

## Insight Objects

An Insight is the standard signal format emitted by alpha models. It encapsulates a
prediction about a single asset and contains the following fields:

| Field         | Description                                                        |
|---------------|--------------------------------------------------------------------|
| **Symbol**    | The asset being predicted (equity, forex pair, future, etc.).      |
| **Type**      | What is being predicted — typically price movement or volatility.  |
| **Direction** | Up, Down, or Flat — the expected directional bias.                 |
| **Period**    | The timeframe over which the prediction is expected to play out.   |
| **Magnitude** | Predicted percent change (optional). Enables magnitude-aware sizing.|
| **Confidence**| Prediction confidence on a 0 to 1 scale (optional). Allows portfolio construction to scale position size by conviction. |
| **Weight**    | Desired portfolio weighting hint (optional). Gives the alpha model direct influence over allocation. |

Insights are decoupled from execution: the alpha model says *what* should happen, not
*how* to make it happen. This separation allows the same signal to be consumed by
different portfolio construction and execution models.

## Signal Generation Approaches

### Momentum-Based

Trend-following signals that go long when price is rising and short when falling, or
mean-reversion signals that fade extreme moves. Common indicators include moving-average
crossovers, RSI extremes, and breakout detection.

### Factor-Based

Signals derived from well-known return factors: value (low P/E, high book-to-market),
quality (high ROE, low debt), size (small-cap premium), and momentum (relative strength).
Factor models rank the universe and emit long signals for top-ranked assets and short
signals for bottom-ranked ones.

### Statistical

Pairs trading, cointegration-based strategies, and other statistical-arbitrage methods
that identify mispricings between related instruments. These models emit coordinated
signals on multiple assets simultaneously.

### Machine Learning

Classification or regression models trained on historical features to predict direction
or magnitude. Examples include random forests, gradient boosting, and neural networks.
ML models require careful feature engineering, train/test separation, and retraining.

### Composite

Combining multiple independent signal sources into a single alpha model. Each sub-model
generates its own insights, and the composite can average, vote, or weight them. This
reduces reliance on any single signal source and improves robustness.

## Multi-Alpha Support

The framework supports running **multiple alpha models simultaneously**, each producing
its own stream of labeled insights. Every insight carries a source tag identifying
which model generated it. This enables several powerful patterns:

- **Ensemble strategies** — portfolio construction weights insights from each model
  based on historical accuracy or theoretical conviction.
- **Regime-dependent selection** — a meta-model activates or suppresses specific alpha
  models depending on detected market conditions (trending vs. mean-reverting).
- **Independent evaluation** — each model's performance can be tracked and compared
  in isolation, even though all models run together in production.

## Grouped Insights

Some strategies require that multiple signals be acted upon as a coordinated unit —
pairs trades (long A / short B), options spreads, or cross-asset hedges. Grouped
insights share a group identifier so that portfolio construction and execution treat
them atomically: either the full group is executed or none of it is.

## Best Practices

1. **Initialize indicators when securities change.** When the universe adds a new asset,
   create and warm up any required indicators before emitting signals for that asset.
2. **Assign unique model names.** In composite setups, each model should carry a distinct
   name so insights can be traced back to their source.
3. **Do not hardcode securities.** Operate on whatever the universe selection provides,
   not on a fixed list of tickers baked into signal logic.
4. **Account for signal decay.** Insights have a finite period; if the predicted move
   has not occurred by expiry, the signal should lapse rather than persist.
5. **Set meaningful confidence values.** Even rough estimates let portfolio construction
   scale positions by conviction, improving risk-adjusted returns.
6. **Track insight accuracy.** Log predicted vs. actual outcomes to detect degradation.
7. **Update at appropriate frequency.** Match signal cadence to the strategy's expected
   holding period; avoid emitting new insights on every tick.

---
*Source: QuantConnect Algorithm Framework documentation.*
