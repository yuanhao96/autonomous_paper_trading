# Holdings & Cashbook

## Overview

Holdings represent the securities currently owned in the portfolio. The cashbook tracks all cash balances by currency. Together they form the complete picture of portfolio state.

## Holdings

### Holding Properties

| Property | Description |
|----------|-------------|
| Symbol | Security identifier |
| Quantity | Number of shares/contracts held (positive = long, negative = short) |
| Average Price | Cost basis per share |
| Market Price | Current market price |
| Market Value | Quantity x Market Price |
| Unrealized P&L | (Market Price - Average Price) x Quantity |
| Unrealized P&L % | (Market Price - Average Price) / Average Price |

### Position Direction

- **Long**: Quantity > 0, profit when price rises
- **Short**: Quantity < 0, profit when price falls
- **Flat**: Quantity = 0, no position

### Cost Basis Tracking

- **Average cost**: Most common method. Averages all entry prices weighted by quantity.
- **FIFO (First In, First Out)**: Oldest shares are sold first. Used in many jurisdictions for tax reporting.
- **LIFO (Last In, First Out)**: Newest shares are sold first.
- **Specific lot identification**: Trader selects which specific lots to close for tax optimization.

### Updating Holdings on Trades

- **New position**: Set quantity and average price from the fill.
- **Adding to existing position**: Increase quantity, recalculate weighted average price.
- **Partial close**: Reduce quantity, compute realized P&L on the closed portion.
- **Full close**: Quantity goes to zero, all remaining P&L moves to realized.
- **Reversal**: Close long and open short (or vice versa) in a single trade.

### Holding Adjustments (Non-Trade)

- **Stock split**: Multiply quantity by split ratio, divide average price by split ratio.
- **Reverse split**: Divide quantity, multiply average price.
- **Dividend (cash)**: No change to holding; cash added to cashbook.
- **Dividend (stock)**: Increase quantity, adjust cost basis.

## Cashbook

### Cash Properties

| Property | Description |
|----------|-------------|
| Currency | Currency code (USD, EUR, GBP, JPY, etc.) |
| Amount | Current cash balance in that currency |
| Conversion Rate | Exchange rate to the account's base currency |
| Value in Account Currency | Amount x Conversion Rate |

### Cash Flow Sources

- Initial capital deposit
- Trade proceeds (selling a security adds cash)
- Trade costs (buying a security removes cash)
- Dividends received
- Interest earned or paid (margin interest)
- Fee deductions (commissions, exchange fees)
- Currency conversions (forex trades)

### Multi-Currency Cash Management

- A separate cash balance is maintained for each currency
- Forex trades affect two currency balances simultaneously (buy EUR/sell USD)
- Cross-currency equity trades require implicit currency conversion
- Net liquidation value aggregates all currencies into the base currency
- Currency exposure can be hedged explicitly via forex positions

### Cash Settlement Rules
- **Equities (US)**: T+1 settlement — cash available one business day after trade
- **Futures**: Daily mark-to-market, margin posted same day
- **Forex**: T+2 for spot, though many brokers credit immediately
- **Crypto**: Typically immediate settlement

### Cash Management Best Practices
- Maintain a cash buffer to avoid margin calls during drawdowns
- Track unsettled cash separately to avoid overcommitting funds
- Monitor currency exposure to prevent unintended forex risk
- Account for expected cash flows (upcoming dividends, option expiries)

Source: Generalized from QuantConnect Portfolio documentation.
