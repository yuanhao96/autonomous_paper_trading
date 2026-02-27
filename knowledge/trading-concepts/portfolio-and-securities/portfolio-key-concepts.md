# Portfolio — Key Concepts

## Overview

The portfolio represents the algorithm's current financial state — all holdings, cash, and open orders. Understanding portfolio management is essential for position sizing, risk management, and performance tracking.

## Portfolio State

### Key Metrics

| Metric | Description |
|--------|-------------|
| Total Portfolio Value | Cash + market value of all holdings |
| Cash | Available cash (settled) for new trades |
| Unsettled Cash | Cash from recent trades not yet settled |
| Total Unrealized Profit | Sum of unrealized P&L across all positions |
| Total Realized Profit | Sum of closed position P&L |
| Margin Used | Total margin consumed by open positions |
| Margin Remaining | Available margin for new positions |
| Total Fees Paid | Cumulative transaction costs |

### Portfolio Value Calculation

- **Total Value** = Cash + Sum(Holdings Market Value) + Unsettled Cash
- **Holdings Market Value** = Quantity x Current Price
- For margin accounts: total value includes the effect of leverage
- Equity = Total Value - Total Borrowed (in margin accounts)

### Cash vs. Margin Accounts

- **Cash account**: Can only buy with settled cash. No short selling.
- **Margin account**: Can borrow to increase buying power. Short selling allowed.
- **Pattern day trader rules**: Minimum $25K equity for frequent intraday trading (US regulation).

## Position Management

- **Invested**: Whether the portfolio holds any positions
- **Holdings count**: Number of distinct positions
- **Concentration**: Largest position as a percentage of total portfolio value
- **Sector exposure**: Allocation broken down by sector or industry
- **Net exposure**: Long value minus short value (indicates directional bias)
- **Gross exposure**: Long value plus absolute short value (indicates total market risk)

## Multi-Currency Support

- Portfolio tracks holdings denominated in multiple currencies
- Cash book maintains a separate balance for each currency
- Currency conversion uses real-time (or delayed) exchange rates
- Base currency (account currency) used for unified P&L reporting
- Forex positions may be held to hedge currency exposure

## Performance Tracking

### Return Metrics

- **Daily returns**: Percentage change in portfolio value day-over-day
- **Cumulative return**: Total return since inception
- **Annualized return**: Geometric average of daily returns, annualized
- **Equity curve**: Time series of portfolio value (visualize growth)

### Risk Metrics

- **Max drawdown**: Largest peak-to-trough decline in portfolio value
- **Sharpe ratio**: Risk-adjusted return (excess return / standard deviation)
- **Sortino ratio**: Like Sharpe but only penalizes downside volatility
- **Calmar ratio**: Annualized return / max drawdown

### Benchmark Comparison

- **Alpha**: Excess return relative to a benchmark (e.g., S&P 500)
- **Beta**: Sensitivity to benchmark movements
- **Tracking error**: Standard deviation of return differences vs. benchmark
- **Information ratio**: Alpha / tracking error

## Common Portfolio Management Patterns

1. **Equal weight**: Allocate the same dollar amount to each position
2. **Risk parity**: Allocate so each position contributes equal risk
3. **Kelly criterion**: Size positions based on edge and variance
4. **Volatility targeting**: Scale total exposure to maintain a target volatility
5. **Max position size**: Cap any single holding to a percentage of portfolio

## Key Considerations
- Always account for transaction costs when evaluating net performance
- Slippage (difference between expected and actual fill price) erodes returns
- Settlement delays (T+1, T+2) affect available cash for subsequent trades
- Margin calls occur when equity drops below maintenance margin requirements
- Reinvestment of dividends and interest can compound returns over time

Source: Generalized from QuantConnect Portfolio documentation.
