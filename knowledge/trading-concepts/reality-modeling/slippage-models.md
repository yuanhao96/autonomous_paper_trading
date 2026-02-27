# Slippage Models

## Overview

Slippage is the difference between the expected fill price and the actual execution price. It occurs because markets move between the time you decide to trade and when the order actually fills. In backtesting, slippage models approximate this cost to produce more realistic performance estimates.

## Sources of Slippage

1. **Market impact:** Your order moves the price, especially for large orders relative to available volume at the current price level.
2. **Latency:** Time delay between signal generation and order reaching the exchange. Even milliseconds matter for fast-moving markets.
3. **Bid-ask spread:** Crossing the spread to get an immediate fill costs half the spread on each side of a round-trip trade.
4. **Volatile markets:** Prices move more between the decision point and execution, widening the gap between expected and actual fill prices.
5. **Low liquidity:** Fewer participants mean wider spreads, larger price gaps between levels, and greater market impact per share.

## Common Slippage Models

### Null (Zero) Slippage

- Assumes perfect fills at the quoted price
- Unrealistic but useful as an optimistic baseline
- Helps isolate the effect of slippage when compared against other models

### Constant Slippage

- Fixed percentage or dollar amount added to every trade
- Simple to implement but does not adapt to market conditions
- Example: assume 1 basis point of slippage on every trade regardless of size

### Volume-Share Slippage

- Slippage increases with order size relative to average volume
- More realistic for equity trading where large orders eat through the order book
- General formula: `Slippage = Price * f(OrderSize / AvgVolume)`
- The function f is typically linear or concave (e.g., square root)

### Market Impact Models

- **Square Root Model (Almgren-Chriss):** `Impact = sigma * sqrt(Q / V)`
  - sigma = daily volatility, Q = order quantity, V = average daily volume
  - Widely used in professional execution analysis and transaction cost analysis (TCA)
- **Linear Model:** `Impact = k * (Q / V)` where k is a calibrated constant
  - Simpler but overestimates impact for large orders
- These models separate temporary impact (reverts after trade) from permanent impact (shifts the equilibrium price)

### Spread-Based Slippage

- Assumes you pay half the bid-ask spread on each trade
- More accurate for forex and crypto where spreads are the primary transaction cost
- Can be combined with market impact models for a comprehensive estimate

## Estimating Slippage by Asset Class

| Asset Class | Typical Slippage |
|------------|-----------------|
| Large-cap equities | 1-5 bps |
| Small-cap equities | 5-20 bps |
| Forex majors | 0.5-2 bps |
| Crypto (major pairs) | 2-10 bps |
| Futures | 0.5-2 ticks |
| Options | 5-50 bps (highly variable) |

These are rough estimates. Actual slippage depends on order size, time of day, market conditions, and execution method.

## Sensitivity Analysis

Testing your strategy at multiple slippage levels reveals how robust it is:

- Run backtests at 0x, 1x, 2x, and 3x your estimated slippage
- Identify the **breakeven slippage**: the level at which the strategy becomes unprofitable
- A strategy that breaks even at 2x estimated slippage has a reasonable safety margin
- A strategy that breaks even at only 1.1x is fragile and likely to underperform live

## Best Practices

- **Model slippage conservatively** (overestimate rather than underestimate)
- **Scale slippage with order size** relative to typical volume for the security
- **Account for time-of-day liquidity patterns** (e.g., wider spreads at market open and close)
- **Use different slippage assumptions for different asset classes** within the same portfolio
- **Validate against live execution data** when transitioning from backtest to production
## Common Pitfalls

1. **Zero slippage assumption:** The most dangerous backtest error; overstates returns significantly for active strategies
2. **Constant slippage for all assets:** A 1 bps assumption is fine for SPY but wildly optimistic for a micro-cap stock
3. **Ignoring position sizing effects:** Slippage is nonlinear; doubling order size more than doubles slippage
4. **Backtesting with unrealistic volume participation:** Assuming you can trade 50% of daily volume without impact is unrealistic

---

Source: Generalized from QuantConnect Reality Modeling documentation.
