# Risk Management Models

## Overview

Risk Management sits between the Portfolio Construction layer and the Execution layer. It reviews
portfolio targets against predefined risk limits and adjusts or vetoes them before any orders are
placed. Think of it as a **circuit breaker and guardrail system** that protects the portfolio from
excessive exposure, concentration, or drawdown. It does not generate alpha — it preserves capital.

## Available Models

| Model | Description | Parameters |
|-------|-------------|------------|
| Maximum Drawdown | Liquidates all positions when portfolio drawdown exceeds a threshold | Max drawdown % (e.g., 10%) |
| Trailing Stop | Applies an automatic trailing stop-loss to every open position | Trail % (e.g., 5%) |
| Sector Exposure | Caps the portfolio's exposure to any single sector | Max sector % (e.g., 25%) |
| Maximum Unrealized Profit | Takes profits when unrealized gain exceeds a threshold | Profit % (e.g., 20%) |
| Null | No risk management; all targets pass through unchanged | -- |

### Choosing a Model

- **Maximum Drawdown** is a hard safety net. Once losses exceed the threshold from peak equity,
  all positions are liquidated. Set it wide enough to avoid triggering on normal volatility.
- **Trailing Stop** protects individual positions by moving the stop-loss up as the position
  appreciates. The trail percentage should be wide enough to avoid whipsaws.
- **Sector Exposure** limits prevent concentration risk, ensuring the portfolio does not become
  a single-sector fund even when the alpha model is bullish on many names in one sector.
- **Maximum Unrealized Profit** enforces profit-taking discipline for strategies that tend to
  give back gains by holding too long.
- **Null** is appropriate only during development/testing or when risk is managed externally.

Multiple risk models can be composed in a layered fashion — for example, combining a trailing stop
with a maximum drawdown limit and a sector exposure cap.

## Risk Metrics

Effective risk management requires monitoring a range of quantitative metrics:

- **Portfolio drawdown** — the peak-to-trough decline in portfolio equity. A drawdown of 20%
  means the portfolio has fallen 20% from its highest recorded value.
- **Value at Risk (VaR)** — the maximum expected loss over a given horizon at a specified
  confidence level (e.g., "95% VaR of $50K" means 5% chance of losing more than $50K).
- **Position concentration** — the weight of any single position as a percentage of total
  portfolio value. High concentration amplifies idiosyncratic risk.
- **Sector and factor exposure** — aggregate exposure to sectors or risk factors (momentum,
  value, volatility). Unintended factor bets can dominate returns.
- **Beta exposure** — the portfolio's sensitivity to broad market movements. A beta of 1.5 means
  the portfolio moves 1.5x the market. High beta amplifies both gains and losses.
- **Correlation risk** — the degree to which positions move together. High correlation across
  holdings means diversification is illusory and drawdowns will be deeper than expected.

## Advanced Strategies

### Options Hedging

For large equity exposures, purchasing protective puts or put spreads can cap downside risk,
particularly during earnings season or ahead of macro events. The cost of the hedge (premium)
must be weighed against the protection it provides.

### Dynamic Position Sizing

Scale exposure inversely with recent realized volatility — reduce positions when volatility is
high, increase when low. This keeps dollar risk per position approximately constant over time.

### Flash Crash Detection

Monitor for abnormal price movements (e.g., a 5% drop in under a minute). When detected, pause
new order submission and tighten stops on existing positions. Resume normal operation only after
conditions stabilize.

### Correlation-Based Diversification Checks

Before adding a new position, check its rolling correlation with existing holdings. If highly
correlated with current exposure, reduce its target size or skip it. Use a rolling window
(e.g., 60-day) rather than a static estimate.

### Regime Detection and Adaptive Limits

Market regimes (trending, mean-reverting, high-vol, low-vol) can shift abruptly. Use regime
detection (e.g., hidden Markov models or volatility thresholds) to dynamically adjust risk
limits — tighten drawdown limits and reduce gross exposure in high-volatility regimes.

## Best Practices

- **Set hard limits and enforce them mechanically.** Maximum drawdown, maximum position size, and
  maximum gross exposure should be non-negotiable. Do not override them based on conviction.
- **Monitor correlation changes.** Correlations spike during market stress — precisely when
  diversification is needed most. Stress-test the portfolio under elevated correlation assumptions.
- **Use multiple risk layers.** No single risk model catches everything. Combine position-level
  controls (trailing stops) with portfolio-level controls (drawdown limits) and exposure controls
  (sector caps).
- **Log all risk events for analysis.** Every time a risk model adjusts or vetoes a target, log
  the event with full context. This data is invaluable for tuning parameters and understanding
  strategy behavior during drawdowns.
- **Review and recalibrate periodically.** Risk parameters appropriate for one market environment
  may be too tight or too loose in another. Schedule regular reviews of all risk limits.

---

*Source: QuantConnect Algorithm Framework documentation.*
