# Securities — Key Concepts

## Overview

A security object represents a tradeable financial instrument. It encapsulates all the data and properties needed to trade: price data, market hours, symbol, exchange, and reality models.

## Security Properties

### Core Properties

| Property | Description |
|----------|-------------|
| Symbol | Unique identifier for the security |
| Security Type | Equity, Option, Future, Forex, Crypto, etc. |
| Exchange | Primary exchange where it trades |
| Market | Market identifier (USA, Europe, etc.) |
| Price | Current market price |
| Volume | Current trading volume |
| Open | Current bar's open price |
| High | Current bar's high price |
| Low | Current bar's low price |
| Close | Previous bar's close price |

### Data Properties

- **Has data**: Whether the security has received any market data
- **Is tradable**: Whether the security can currently be traded
- **Is delisted**: Whether the security has been removed from trading
- **Local time**: Current time in the security's exchange time zone

### Configuration

- **Data normalization mode**: Raw, adjusted, or total return
- **Leverage**: Maximum leverage allowed for this security
- **Fee model**: How transaction costs are calculated
- **Fill model**: How simulated order fills are determined
- **Slippage model**: How price impact from order execution is estimated

## Security Types

### Common Security Types

| Type | Characteristics |
|------|----------------|
| Equity | Stocks, ETFs. Settlement T+1, dividends, splits |
| Equity Option | Derivative on equity. Strike, expiry, Greeks |
| Future | Standardized contract. Margin, expiry, roll dates |
| Future Option | Option on a futures contract |
| Forex | Currency pair. 24/5, pip-based pricing |
| Crypto | Cryptocurrency. 24/7, fractional quantities |
| Index | Not directly tradable, used as benchmark |
| CFD | Contract for difference. Leveraged, no ownership |

## Security Lifecycle

1. **Subscription**: Security is added to the algorithm (via universe selection or explicit request)
2. **Data reception**: Market data streams in — ticks, bars, or quotes
3. **Tradable state**: Security is available for order placement
4. **Corporate actions**: Splits, dividends, and mergers are applied as they occur
5. **Removal or delisting**: Security is removed from the algorithm's universe or delisted entirely

## Symbol Identification

- **Ticker**: Human-readable label (e.g., "AAPL"), may be reused over time
- **Unique symbol / SID**: Permanent identifier that resolves ticker ambiguity
- **FIGI / ISIN / CUSIP**: Industry-standard identifiers for cross-system matching
- Ticker changes (e.g., rebrands) should map to the same underlying security

## Reality Models

Reality models simulate real-world trading conditions during backtesting:

- **Fee model**: Commissions and exchange fees per trade
- **Fill model**: When and at what price orders get filled
- **Slippage model**: Additional cost from market impact
- **Margin model**: How much collateral is required for leveraged positions
- **Settlement model**: When trade proceeds become available
- **Buying power model**: How much purchasing power is available

## Key Considerations

- Always verify a security is tradable before placing an order
- Handle delisted securities gracefully (liquidate or ignore)
- Normalization mode affects historical price comparisons — use adjusted data for backtesting continuity
- Exchange hours differ by security type — options and futures may have different hours than the underlying
- Leverage settings and margin requirements vary by asset class and broker

Source: Generalized from QuantConnect Securities documentation.
