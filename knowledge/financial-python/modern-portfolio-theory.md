# Modern Portfolio Theory

## Overview

Twelfth article in the Introduction to Financial Python series by QuantConnect. Covers Modern Portfolio Theory (MPT) by Harry Markowitz: risk aversion, portfolio construction with weights, expected return and variance formulas, covariance and correlation, diversification benefits, the efficient frontier, and the Capital Market Line (CML).

## Key Concepts

### Risk Aversion

MPT assumes investors are risk-averse: given two assets with the same expected return, they prefer the one with lower risk (variance).

**Example**: Asset A pays $100 ± $100, Asset B pays $100 ± $300. Both have the same expected value ($100), but rational investors prefer Asset A (lower standard deviation).

### Portfolio Construction

#### Portfolio Weights

Weights must sum to 1:

```
w₀ + w₁ + w₂ + ... + wₙ = 1
```

#### Expected Portfolio Return

```
E(Rₚ) = w₀R₀ + w₁E(R₁) + ... + wₙE(Rₙ)
```

Where `R₀` is the risk-free rate and `wᵢ` is the weight of asset i.

### Covariance and Correlation

**Covariance** measures the linear relationship between two asset returns:

```
Cov(X, Y) = E[(X - μₓ)(Y - μᵧ)]
```

**Correlation** standardizes covariance to the range [-1, 1]:

```
ρ(X, Y) = Cov(X, Y) / (σₓ × σᵧ)
```

| ρ | Meaning |
|---|---------|
| +1 | Perfect positive correlation |
| 0 | No linear relationship |
| -1 | Perfect negative correlation |

### Portfolio Variance

For a portfolio of n assets:

```
Var(Rₚ) = w^T Σ w
```

Where `w` is the weight vector and `Σ` is the covariance matrix of asset returns.

### Diversification

Portfolio risk can be reduced by combining assets that are negatively correlated. This is the diversification benefit — often called the "free lunch" of investing.

- **Systematic risk**: Market-wide risk that cannot be diversified away
- **Unsystematic risk**: Asset-specific risk that can be eliminated through diversification

### Mean-Variance Analysis

#### Efficient Frontier

The efficient frontier represents the set of portfolios that offer:
- Maximum expected return for a given level of risk, or
- Minimum risk for a given level of expected return

Portfolios below the efficient frontier are suboptimal — they offer less return for the same risk.

#### Capital Market Line (CML)

The CML is the line tangent to the efficient frontier, starting from the risk-free rate:

```
E(Rₚ) = R₀ + [(E(Rₘ) - R₀) / σₘ] × σₚ
```

Where:
- `R₀` = risk-free rate
- `E(Rₘ)` = expected return of the market portfolio
- `σₘ` = standard deviation of the market portfolio
- `σₚ` = standard deviation of the portfolio

### Key Insight: Separation Theorem

All investors should hold the same risky portfolio (the market portfolio) and adjust risk by combining it with risk-free assets. The optimal risky portfolio does not depend on individual risk preferences — only the allocation between risky and risk-free assets changes.

## Financial Application Notes

- MPT is the theoretical foundation of passive index investing
- The covariance matrix Σ is the central input — estimation errors propagate into portfolio weights
- In practice, the efficient frontier is estimated from historical data and is subject to estimation error
- Extensions include Black-Litterman (incorporating views) and robust optimization
- Risk parity strategies distribute risk equally rather than capital equally
- MPT assumes normal distribution of returns — fails to capture tail risks and fat tails

## Summary

Covers the core of Modern Portfolio Theory: risk aversion, portfolio weights and expected returns, covariance/correlation between assets, portfolio variance via matrix notation (w^T Σ w), diversification benefits, the efficient frontier, and the Capital Market Line. The key insight is that all investors should hold the market portfolio and adjust risk via leverage or risk-free assets (separation theorem).

## Source

- [QuantConnect: Modern Portfolio Theory](https://www.quantconnect.com/learning/articles/introduction-to-financial-python/modern-portfolio-theory)
