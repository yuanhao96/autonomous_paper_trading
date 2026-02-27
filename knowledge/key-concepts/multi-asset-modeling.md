# Multi-Asset Modeling

## Overview

Covers the concepts and challenges of trading across multiple asset classes simultaneously. Includes asset class characteristics, multi-currency handling, portfolio-level aggregation, and practical considerations for multi-asset strategies.

## Supported Asset Classes

Modern trading platforms support a wide range of asset classes:

| Asset Class | Characteristics | Typical Resolution |
|-------------|----------------|-------------------|
| **Equities** | Stocks on exchanges (NYSE, NASDAQ, etc.) | Tick to daily |
| **Equity Options** | Derivatives on stocks; calls and puts with strikes/expirations | Minute to daily |
| **Futures** | Standardized contracts on commodities, indices, rates | Tick to daily |
| **Future Options** | Options on futures contracts | Minute to daily |
| **Forex** | Currency pairs (e.g., EURUSD, USDJPY) | Tick to daily |
| **Crypto** | Digital assets (BTC, ETH, etc.) on crypto exchanges | Tick to daily |
| **Crypto Futures** | Futures contracts on cryptocurrencies | Minute to daily |
| **CFDs** | Contracts for difference; synthetic exposure | Minute to daily |
| **Index** | Broad market indices (S&P 500, VIX) — typically non-tradable | Daily |

## Security Objects

Each instrument in the algorithm is represented as a **Security object** that holds:

- **Price data**: Open, high, low, close, volume
- **Properties**: Symbol, exchange, market hours, tick size, lot size
- **Models**: Fee structure, slippage model, margin requirements, fill behavior
- **Fundamental data**: Earnings, P/E ratios, market cap (for equities)

```python
# Accessing security properties
price = securities["SPY"].price
exchange = securities["SPY"].exchange
is_tradable = securities["SPY"].is_tradable
```

## Multi-Currency Support

When trading instruments denominated in different currencies, the system must:

1. **Track each currency's cash balance** independently
2. **Convert P&L** to the account's base currency for reporting
3. **Subscribe to exchange rate data** for real-time conversion
4. **Handle margin** in the correct currency

### Example: USD-based account trading forex and international equities

```
Account base currency: USD
Holdings:
  - 100 shares AAPL (quoted in USD) → no conversion needed
  - 10,000 EURUSD forex → P&L in EUR, converted to USD
  - 50 shares Toyota (quoted in JPY) → P&L in JPY, converted to USD
```

The portfolio aggregates all positions into the base currency for total equity, margin, and drawdown calculations.

## Portfolio Management

The portfolio object aggregates all positions:

| Property | Description |
|----------|-------------|
| `total_portfolio_value` | Sum of all positions + cash in base currency |
| `total_unrealized_profit` | Open position gains/losses |
| `total_profit` | Realized gains/losses |
| `margin_remaining` | Available buying power |
| `invested` | True if any positions are open |

Each security holding tracks:
- Quantity (long/short)
- Average price and cost basis
- Unrealized and realized P&L
- Margin used

## Cross-Asset Strategies

### Arbitrage

Exploit price discrepancies between related instruments:
- **Cash-futures basis**: Buy spot, sell futures (or vice versa)
- **Cross-exchange arbitrage**: Same asset at different prices on different exchanges
- **ETF arbitrage**: ETF price vs net asset value of underlying basket

### Pairs Trading

Trade relative value between correlated instruments:
- **Equity pairs**: Long undervalued stock, short overvalued
- **Cross-asset pairs**: Equity vs its sector ETF, bond vs equity
- **Statistical arbitrage**: Mean reversion on spread using cointegration

### Risk Parity

Allocate risk equally across asset classes:
- Equities, bonds, commodities, currencies
- Weight by inverse volatility rather than equal capital
- Rebalance periodically to maintain target risk allocation

### Macro / Tactical Asset Allocation

Rotate between asset classes based on economic signals:
- Momentum across asset classes
- Carry (interest rate differentials)
- Valuation (relative P/E, yield spreads)

## Data Considerations

### Different Market Hours

| Asset Class | Typical Trading Hours |
|-------------|----------------------|
| US Equities | 9:30 AM – 4:00 PM ET |
| Forex | 24 hours (Sun 5 PM – Fri 5 PM ET) |
| Crypto | 24/7 |
| US Futures | Nearly 24 hours (with breaks) |
| European Equities | 8:00 AM – 4:30 PM CET |

When trading multiple asset classes, the algorithm must handle:
- Instruments that are open at different times
- Data gaps when a market is closed
- Fill-forward behavior for stale prices

### Different Tick Sizes and Lot Sizes

Each asset class has specific minimum price increments and minimum order sizes:
- US equities: $0.01 tick, 1 share minimum
- Forex: Varies by pair (e.g., 0.0001 pip), standard lot = 100,000 units
- Futures: Contract-specific tick sizes and multipliers

## Financial Application Notes

- Multi-asset strategies benefit from diversification across uncorrelated return streams
- Currency risk is a hidden factor in international portfolios — hedge or account for it
- Different asset classes have different liquidity profiles, transaction costs, and margin requirements
- Market hours mismatch can cause stale data issues — be careful with signals that depend on contemporaneous prices
- Aggregating P&L across currencies requires consistent conversion methodology

## Summary

Multi-asset modeling involves handling different asset classes with varying characteristics (market hours, tick sizes, currencies, margin rules) within a single portfolio. Key challenges include data synchronization across time zones, multi-currency P&L aggregation, and managing the distinct properties of each asset class. Multi-asset strategies (arbitrage, pairs trading, risk parity, tactical allocation) benefit from diversification but require careful handling of cross-asset complexity.

## Source

- Based on [QuantConnect: Key Concepts — Multi-Asset Modeling](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/multi-asset-modeling)
