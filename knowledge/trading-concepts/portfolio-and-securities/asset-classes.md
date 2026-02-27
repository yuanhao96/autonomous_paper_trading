# Asset Classes

## Overview

Different asset classes have distinct trading characteristics, data formats, market hours, and risk profiles. Understanding these differences is crucial for multi-asset algorithmic trading.

## US Equities

- **Instruments**: Stocks, ETFs, ADRs
- **Market hours**: 9:30-16:00 ET (pre-market 4:00, after-hours to 20:00)
- **Settlement**: T+1
- **Minimum tick**: $0.01
- **Lot size**: 1 share (fractional shares available at some brokers)
- **Key events**: Earnings, dividends, splits, index rebalancing
- **Data**: OHLCV bars, fundamental data, corporate actions
- **Regulation**: SEC-regulated, pattern day trader rules apply

## Equity Options

- **Instruments**: Calls and puts on underlying equities or ETFs
- **Market hours**: 9:30-16:00 ET (some ETF options until 16:15)
- **Settlement**: T+1
- **Multiplier**: Typically 100 shares per contract
- **Expiration cycles**: Monthly (3rd Friday), weekly, daily (0DTE)
- **Exercise style**: American (can exercise before expiry)
- **Key data**: Strike price, expiry date, Greeks (delta, gamma, theta, vega), implied volatility, open interest
- **Strategies**: Covered calls, spreads, straddles, iron condors, etc.

## Futures

- **Instruments**: Standardized contracts (ES, NQ, CL, GC, ZB, etc.)
- **Market hours**: Nearly 24/5 (exchange-specific, e.g., CME Globex)
- **Settlement**: Daily mark-to-market; physical delivery or cash settlement at expiry
- **Margin**: Initial and maintenance margin requirements (typically 5-12% of notional)
- **Contract specs**: Multiplier, tick size, delivery months vary by product
- **Roll dates**: Positions must be rolled from expiring to next front-month contract
- **Micro contracts**: Smaller-sized contracts for reduced capital requirements (e.g., MES, MNQ)

## Forex

- **Instruments**: Currency pairs (EUR/USD, GBP/USD, USD/JPY, AUD/USD, etc.)
- **Market hours**: 24/5 (Sunday 5:00 PM ET to Friday 5:00 PM ET)
- **Settlement**: T+2 for spot; T+0 available at many retail brokers
- **Lot sizes**: Standard (100,000 units), Mini (10,000), Micro (1,000)
- **Pip**: Smallest standard price increment (4th decimal for most pairs, 2nd for JPY pairs)
- **Leverage**: Up to 50:1 in regulated US markets, higher in some offshore jurisdictions
- **Sessions**: Asian, European, and North American sessions with varying liquidity

## Cryptocurrency

- **Instruments**: BTC, ETH, and thousands of altcoins
- **Market hours**: 24/7/365 — no market closes
- **Settlement**: Typically immediate (on-chain confirmation times vary)
- **Fractional trading**: Standard practice (buy 0.001 BTC)
- **Key differences**: No circuit breakers, higher volatility, exchange fragmentation
- **Fee structure**: Maker/taker model, percentage-based (0.01% to 0.50%)
- **Risks**: Exchange counterparty risk, regulatory uncertainty, liquidity fragmentation

## Fixed Income

- **Instruments**: Treasury bonds, corporate bonds, municipal bonds
- **Market hours**: OTC market, generally 8:00-17:00 ET
- **Settlement**: T+1 or T+2 depending on instrument
- **Key data**: Yield, duration, credit rating, coupon rate
- **Pricing**: Quoted as percentage of par value
- **Risks**: Interest rate risk, credit risk, liquidity risk

## Index

- **Instruments**: S&P 500, NASDAQ 100, Russell 2000, VIX, etc.
- **Not directly tradable**: Use futures, ETFs, or options as proxies
- **Use in trading**: Benchmarking, hedging, market regime detection
- **Index-linked products**: SPY (S&P ETF), QQQ (NASDAQ ETF), ES (S&P futures)

## Asset Class Comparison Table

| Class | Hours | Settlement | Leverage | Typical Data |
|-------|-------|-----------|----------|--------------|
| Equities | 6.5h/day | T+1 | 2-4x | OHLCV, fundamentals |
| Options | 6.5h/day | T+1 | N/A (built-in) | Greeks, IV, chain |
| Futures | ~23h/day | Daily MTM | 10-20x | OHLCV, open interest |
| Forex | 24/5 | T+2 | 20-50x | Quotes, ticks |
| Crypto | 24/7 | Immediate | 1-100x | OHLCV, order book |
| Fixed Income | ~9h/day | T+1 or T+2 | 1-10x | Yield, duration |

## Multi-Asset Trading Considerations

- **Correlation**: Assets across classes may be correlated (e.g., equities and equity futures)
- **Margin netting**: Some brokers allow cross-margining between related products
- **Data alignment**: Different trading hours require careful timestamp synchronization
- **Risk aggregation**: Portfolio risk must account for each asset class's unique risk factors
- **Execution**: Liquidity profiles differ dramatically — equities are generally more liquid than options

Source: Generalized from QuantConnect Securities documentation.
