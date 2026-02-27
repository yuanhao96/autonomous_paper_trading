# Options Models

## Overview
Options models handle the unique complexities of options trading: pricing theoretical values, calculating risk sensitivities (Greeks), modeling exercise and assignment, and estimating implied volatility.

## Options Pricing Models

### Black-Scholes Model
- For European-style options (exercise only at expiration)
- Call: C = S * N(d1) - K * e^(-rT) * N(d2)
- Put: P = K * e^(-rT) * N(-d2) - S * N(-d1)
- Where:
  - d1 = [ln(S/K) + (r + sigma^2/2)T] / (sigma * sqrt(T))
  - d2 = d1 - sigma * sqrt(T)
  - S = underlying price, K = strike, r = risk-free rate, T = time to expiry, sigma = volatility
- Assumes constant volatility and no dividends (extensions exist for both)

### Binomial Model
- For American-style options (early exercise allowed)
- Creates a price tree with up/down movements at each step
- Works backward from expiration to determine option value
- More flexible than Black-Scholes but computationally heavier
- Naturally handles dividends and early exercise

### Monte Carlo Simulation
- For complex/exotic options
- Simulates thousands of price paths for the underlying
- Averages discounted payoffs across all paths
- Most flexible but slowest method
- Well-suited for path-dependent options (Asian, barrier, lookback)

## The Greeks (Risk Sensitivities)

| Greek | Symbol | Measures | Typical Range |
|-------|--------|----------|---------------|
| Delta | D | Price sensitivity to underlying | 0 to +/-1 |
| Gamma | G | Rate of change of delta | >= 0 |
| Theta | Th | Time decay per day | Usually negative |
| Vega | V | Sensitivity to volatility | >= 0 |
| Rho | R | Sensitivity to interest rates | Varies |

### Delta
- Call delta: 0 to +1 (ATM approximately 0.5)
- Put delta: -1 to 0 (ATM approximately -0.5)
- Delta hedging: offsetting directional risk by trading the underlying
- Portfolio delta measures aggregate directional exposure

### Gamma
- Highest at-the-money, near expiration
- Measures convexity of option payoff
- Long options = positive gamma (benefits from large moves)
- Short options = negative gamma (harmed by large moves)

### Theta
- Options lose value over time (time decay)
- Accelerates as expiration approaches
- Sellers collect theta, buyers pay it
- Theta is the "cost" of holding optionality

### Vega
- Higher for longer-dated options
- Highest at-the-money
- Volatility trading strategies exploit vega exposure
- Not a Greek letter, but universally used as a Greek

## Implied Volatility
- Market's expectation of future volatility
- Derived by inverting Black-Scholes (given market price, solve for sigma)
- IV Smile/Skew: OTM puts often have higher IV than ATM options
- VIX index measures S&P 500 implied volatility
- IV rank and IV percentile help contextualize current IV levels

## Exercise and Assignment
- **American options**: Can be exercised any time before expiration
- **European options**: Can only be exercised at expiration
- **Auto-exercise**: Options ITM by a certain threshold at expiration are auto-exercised
- **Assignment risk**: Short American options can be assigned at any time
- **Early exercise considerations**: Dividends, deep ITM, interest rate environment

## Volatility Models
- **Historical volatility**: Standard deviation of past log returns
- **Realized volatility**: Actual volatility measured over a specific period
- **Implied volatility**: Market-derived expectation from option prices
- **GARCH models**: Time-varying volatility estimation with clustering effects
- **Stochastic volatility**: Heston, SABR models allow volatility itself to be random

## Implications for Algorithmic Trading
- Greeks enable real-time risk management and dynamic hedging
- Pricing models allow detection of mispriced options for mean-reversion strategies
- IV surfaces can be modeled to find relative value across strikes and expirations
- Exercise and assignment logic must be handled to avoid unexpected position changes
- Volatility forecasting is central to options-based strategy profitability
- Backtesting options strategies requires realistic IV and Greeks modeling

## Key Takeaways
- Black-Scholes is the foundation, but real markets exhibit skew and smile
- Greeks decompose option risk into manageable, hedgeable components
- Theta and vega are the primary drivers for income and volatility strategies
- Implied volatility is forward-looking and often diverges from historical volatility
- Algorithmic options trading demands accurate pricing, Greeks, and exercise modeling

---

Source: Generalized from QuantConnect Reality Modeling documentation.
