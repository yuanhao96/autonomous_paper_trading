# Brokerage Models

## Overview

A brokerage model bundles the realistic trading parameters of a specific broker. It
defines which asset classes are supported, what order types are available, default
leverage and margin requirements, fee schedules, settlement rules, and trading hours.
Choosing the right brokerage model is the foundation of an accurate backtest.

## Brokerage Characteristics

### Supported Asset Classes

Each broker supports different markets. Selecting a brokerage model constrains
what your strategy can trade.

| Broker Type | Equities | Options | Futures | Forex | Crypto |
|-------------|----------|---------|---------|-------|--------|
| Full-service (e.g., Interactive Brokers) | Yes | Yes | Yes | Yes | No |
| Forex specialist (e.g., OANDA, FXCM) | No | No | No | Yes | No |
| Crypto exchange (e.g., Coinbase, Binance) | No | No | No | No | Yes |
| Discount broker (e.g., Alpaca, Tradier) | Yes | Yes | No | No | No |

### Account Types

- **Cash account**: Can only trade with settled cash. No shorting allowed.
- **Margin account**: Leverage is available. Short selling is permitted.
- **Pattern Day Trader (PDT)**: US regulation requiring $25K minimum equity for
  accounts making 4+ day trades in 5 business days. Grants 4x intraday buying
  power and 2x overnight.

### Order Type Support

Not all brokers support all order types. Always verify availability before relying
on a specific order type in your strategy.

| Order Type | Availability |
|------------|-------------|
| Market | Universally supported |
| Limit | Universally supported |
| Stop Market | Most brokers |
| Stop Limit | Most brokers |
| Trailing Stop | Many brokers |
| Market on Open / Close | Primarily equity brokers |

### Leverage Defaults

Leverage varies significantly by asset class and jurisdiction.

| Asset Class | Typical Initial Margin | Effective Leverage |
|-------------|----------------------|-------------------|
| US Equities | 50% | 2x |
| US Equities (day trading) | 25% | 4x intraday |
| Forex | 2% | 50x |
| Futures | 5-10% | 10-20x |
| Crypto | Varies by exchange | 1x to 100x |

Higher leverage amplifies both gains and losses. Many strategies intentionally
use less than the maximum leverage available.

### Extended / Pre-Market Hours

- Some brokers allow pre-market (4:00-9:30 ET) and after-hours (16:00-20:00 ET) trading.
- Liquidity is typically much lower outside regular session hours.
- Wider spreads and higher slippage should be expected in extended hours.
- Not all order types are available during extended sessions (limit orders only is common).

## Selecting a Brokerage Model

When choosing a brokerage model for backtesting or live trading, consider:

1. **Asset classes needed** — Does the broker support every market your strategy trades?
2. **Fee structure** — Per-share, per-trade, or percentage-based? Which is cheapest
   for your typical order size?
3. **Margin / leverage requirements** — Does the broker provide the leverage you need
   without excessive risk?
4. **Order types needed** — If your strategy depends on trailing stops or MOC orders,
   confirm the broker supports them.
5. **API quality for live trading** — Reliable execution, low latency, and good
   documentation matter for automated strategies.
6. **Regulatory jurisdiction** — US, EU, and other jurisdictions impose different
   rules on leverage limits, PDT requirements, and reporting.

## Impact on Backtesting

The brokerage model you select sets the boundary conditions for every other reality
model component. Fees, fills, slippage, and settlement all derive from or interact
with the brokerage model. Using the wrong brokerage model can invalidate an entire
backtest — for example, simulating 50x forex leverage on a broker that only allows 30x.

Always match your backtest brokerage model to the broker you intend to trade with live.

---

Source: Generalized from QuantConnect Reality Modeling documentation.
