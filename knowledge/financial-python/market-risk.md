# Market Risk

## Overview

Thirteenth article in the Introduction to Financial Python series by QuantConnect. Covers the Capital Asset Pricing Model (CAPM), beta estimation and its practical challenges, rolling beta analysis, and market-neutral portfolio construction. Demonstrates with GE, PG, and KO stock data.

## Key Concepts

### Capital Asset Pricing Model (CAPM)

CAPM describes the expected return of an asset as a function of its market risk:

```
E(R) - R₀ = β × (E(Rₘ) - R₀)
```

Where:
- `E(R)` = expected return of the asset
- `R₀` = risk-free rate
- `E(Rₘ)` = expected return of the market
- `β` = beta (sensitivity to market movements)

The left side is the asset's **risk premium**; the right side is the market risk premium scaled by beta.

### Beta

Beta measures the sensitivity of an asset's return to market movements:

```
β = Cov(R, Rₘ) / Var(Rₘ)
```

| β Value | Interpretation |
|---------|---------------|
| β > 1 | More volatile than the market |
| β = 1 | Moves with the market |
| 0 < β < 1 | Less volatile than the market |
| β = 0 | No market sensitivity |
| β < 0 | Moves opposite to the market |

Beta is derived from allocating a fraction `w` to the market portfolio and `(1-w)` to risk-free assets.

### Computing Beta in Practice

#### Practical Challenges

- **Timeframe selection**: Daily, weekly, or monthly returns produce different betas
- **Data requirements**: Need sufficient data points for reliable regression
- **Temporal instability**: Beta changes over time

#### Rolling Beta Analysis

Using GE stock with 6-month rolling windows:

**Key finding**: GE's beta ranged from approximately 0.1 to 0.5 across different windows, demonstrating significant temporal instability. P-values also fluctuated, sometimes reaching 0.1 (weak significance).

**Important**: It makes no sense to discuss beta without specifying a timeframe.

### Market-Neutral Strategies

#### Definition

A portfolio is **market-neutral** if its beta equals zero — it has no exposure to overall market movements.

#### Two-Stock Portfolio Construction

For stocks A and B with weights w and (1-w):

```
β_portfolio = w × β_A + (1-w) × β_B = 0
```

Solving for w:

```
w = β_B / (β_B - β_A)
```

#### Linear Relationship Between Betas

When β_A = m × β_B + c (with c ≈ 0):

```
w ≈ 1 / (1 - m)
```

#### Practical Example: PG and KO

Regression of rolling betas: `β_KO = -0.0097 + 0.969 × β_PG`

Resulting weights:
- w_KO = 32.3
- w_PG = -31.3

Results:
- **In-sample beta**: 0.01 (near zero)
- **Out-of-sample beta**: -0.004 (maintained near zero)

This demonstrates that market-neutral construction works when stock betas have a stable linear relationship.

## Financial Application Notes

- CAPM is the simplest asset pricing model — extended by Fama-French multi-factor models
- Beta estimation is sensitive to the lookback window and return frequency
- Market-neutral strategies hedge out systematic risk, profiting only from stock-specific movements
- Pairs trading and statistical arbitrage strategies often use beta-hedging
- Long-short equity funds target zero (or low) beta to isolate alpha
- Beta instability is a practical challenge — strategies must periodically recalibrate

## Summary

Covers CAPM (relating expected returns to market risk via beta), beta estimation and its practical challenges (timeframe dependence, temporal instability), rolling beta analysis, and market-neutral portfolio construction by solving for weights that zero out market exposure. The PG/KO example demonstrates a practical beta-hedging approach that maintains near-zero market sensitivity both in-sample and out-of-sample.

## Source

- [QuantConnect: Market Risk](https://www.quantconnect.com/learning/articles/introduction-to-financial-python/market-risk)
