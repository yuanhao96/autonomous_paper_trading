# Fama-French Multi-Factor Models

## Overview

Fourteenth and final article in the Introduction to Financial Python series by QuantConnect. Covers the progression from CAPM to multi-factor models: the Fama-French 3-factor model (market, size, value), the 5-factor extension (adding profitability and investment), and a practical implementation combining value, quality, and momentum factors following AQR Capital Management's framework.

## Key Concepts

### General Multi-Factor Model

```
R = α + β₁f₁ + β₂f₂ + ... + βₙfₙ + ε
```

Each `fᵢ` represents a different factor (systematic risk source) influencing asset returns. Alpha (α) represents the return unexplained by the factors.

### Fama-French Three-Factor Model

```
R = α + βₘ × MKT + βₛ × SMB + βₕ × HML + ε
```

#### Factor Definitions

| Factor | Full Name | Description |
|--------|-----------|-------------|
| **MKT** | Market | Excess return of value-weighted CRSP US firms (NYSE, AMEX, NASDAQ) minus 1-month T-Bill rate |
| **SMB** | Small Minus Big | Return spread between small-cap and large-cap stocks |
| **HML** | High Minus Low | Return spread between value stocks (high book-to-price) and growth stocks (low book-to-price) |

#### Empirical Results

Testing on NASDAQ indices with 6 years of daily returns:

**Small-Cap Index**:
- Positive SMB coefficient → small-cap outperformance drives index returns
- MKT and SMB showed strongest statistical significance (highest t-statistics)

**Large-Cap Index**:
- Negative SMB coefficient → large-cap stocks dominate
- Low HML coefficient → balanced between value and growth

### Fama-French Five-Factor Model

Adds two additional factors to the three-factor model:

| Factor | Full Name | Description |
|--------|-----------|-------------|
| **RMW** | Robust Minus Weak | Return spread between firms with high vs low operating profit margins |
| **CMA** | Conservative Minus Aggressive | Return spread between firms with conservative vs aggressive capital investment |

The five-factor model:
```
R = α + βₘMKT + βₛSMB + βₕHML + βᵣRMW + βcCMA + ε
```

### Momentum Factor

An additional factor not in the original Fama-French framework:

**Momentum (MOM)**: Return spread between highest-performing and lowest-performing stocks over the past 12 months (excluding the most recent month).

### Practical Implementation

Following AQR Capital Management's 2013 framework, a strategy combining:

- **Value**: Measured by book value per share
- **Quality**: Measured by operating profit margin (related to RMW)
- **Momentum**: 1-month momentum signal

**Rebalancing**: Monthly portfolio adjustments based on factor scores.

### Factor Data Sources

Factor return data is available from Kenneth French's Data Library, providing daily and monthly factor returns for the US and international markets.

## Financial Application Notes

- The Fama-French models are the most empirically successful multi-factor asset pricing models
- They are widely used in both academic research and professional portfolio management
- A positive alpha (α > 0) after controlling for all factors indicates genuine skill or market inefficiency
- Factor investing (smart beta) strategies directly target these return premiums
- Factor exposures explain most of the cross-section of expected stock returns
- The 5-factor model subsumes many previously documented anomalies
- Momentum is notable for its absence from the Fama-French framework despite strong empirical support

## Summary

Covers the evolution of asset pricing models from single-factor (CAPM) to multi-factor (Fama-French 3-factor and 5-factor). The three-factor model adds size (SMB) and value (HML) to market risk; the five-factor model adds profitability (RMW) and investment (CMA). A practical implementation following AQR's framework combines value, quality, and momentum factors. These models represent the empirical foundation of modern factor investing.

## Source

- [QuantConnect: Fama-French Multi-Factor Models](https://www.quantconnect.com/learning/articles/introduction-to-financial-python/fama-french-multi-factor-models)
