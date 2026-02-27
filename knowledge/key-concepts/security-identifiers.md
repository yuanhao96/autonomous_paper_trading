# Security Identifiers

## Overview

Covers how financial instruments are identified, the challenges of ticker symbology, industry-standard identifiers (CUSIP, ISIN, FIGI, SEDOL), and the importance of robust security identification for algorithmic trading. Proper instrument identification prevents errors from ticker changes, delistings, and symbol reuse.

## The Problem with Tickers

Ticker symbols are the most visible instrument identifiers, but they have serious limitations:

### Ticker Changes
Companies change their ticker symbols:
- **Facebook → Meta**: FB → META (October 2021)
- **Google → Alphabet**: GOOG restructured under GOOGL
- **Chase Manhattan → JPMorgan**: Symbol mapping changed

### Ticker Reuse
Tickers are recycled after companies delist:
- A delisted company's ticker may be assigned to a completely different company
- Historical data queries using only ticker symbols may return wrong data

### Ticker Ambiguity
The same ticker can refer to different instruments:
- "AAPL" on NYSE vs "AAPL" on another exchange
- Futures contracts have specific expiration dates but similar root symbols
- Options have strike prices and expiration dates encoded in symbology

## Industry-Standard Identifiers

To overcome ticker limitations, the financial industry uses persistent identifiers:

| Identifier | Full Name | Scope | Format | Example |
|-----------|-----------|-------|--------|---------|
| **CUSIP** | Committee on Uniform Securities Identification Procedures | US & Canada | 9-character alphanumeric | 037833100 (Apple) |
| **ISIN** | International Securities Identification Number | Global | 12-character (country + CUSIP/SEDOL + check digit) | US0378331005 (Apple) |
| **FIGI** | Financial Instrument Global Identifier (OpenFIGI) | Global | 12-character | BBG000B9XRY4 (Apple) |
| **SEDOL** | Stock Exchange Daily Official List | UK & Ireland | 7-character | 2046251 (Apple on LSE) |
| **RIC** | Reuters Instrument Code | Global (Refinitiv) | Variable | AAPL.OQ |
| **Bloomberg Ticker** | Bloomberg Terminal | Global (Bloomberg) | Variable | AAPL US Equity |

### Choosing an Identifier

- **CUSIP/ISIN**: Standard for institutional trading, regulatory reporting
- **FIGI**: Free, open standard; good for cross-referencing
- **SEDOL**: Required for UK/European instruments
- **Ticker + Exchange**: Sufficient for simple strategies on a single exchange

## Symbol Objects

In algorithmic trading systems, instruments are typically represented by a **Symbol object** that encapsulates:

```python
class Symbol:
    ticker: str          # Current ticker (e.g., "AAPL")
    security_type: str   # Equity, Option, Future, Forex, Crypto
    market: str          # Exchange or market (e.g., "NYSE", "NASDAQ")
    cusip: str           # CUSIP identifier (if available)
    isin: str            # ISIN identifier (if available)
```

### Why Symbol Objects Matter

- They persist across ticker changes (the underlying ID doesn't change when the ticker does)
- They disambiguate instruments with the same ticker on different exchanges
- They handle complex instruments (options with strike/expiry, futures with expiration)

## Derivative Symbology

### Options

Option identifiers typically encode:
- Underlying symbol
- Expiration date
- Strike price
- Option type (call/put)

**OCC Standard**: `AAPL  230120C00150000` → AAPL, Jan 20 2023, Call, $150 strike

### Futures

Futures identifiers encode:
- Root symbol (e.g., ES for S&P 500 E-mini)
- Expiration month and year
- Contract specifications

**CME Standard**: `ESH24` → E-mini S&P 500, March 2024

## Mapping and Resolution

### Ticker-to-Identifier Mapping

Trading systems must maintain a mapping database that resolves:
- Current ticker → persistent identifier
- Historical ticker → current identifier
- Cross-reference between identifier types (CUSIP ↔ ISIN ↔ FIGI)

### Point-in-Time Accuracy

Historical backtests must use the correct ticker as of the simulation date, not the current ticker. This prevents:
- **Survivorship bias**: Using current S&P 500 members for a historical backtest
- **Look-ahead bias**: Using a ticker that didn't exist yet at the simulation time

## Financial Application Notes

- Always use persistent identifiers (CUSIP, ISIN, FIGI) for research databases and long-term data storage
- Tickers are fine for human-readable display and simple single-exchange strategies
- Options and futures require structured symbology that encodes expiration and strike
- Cross-reference databases (OpenFIGI API is free) are essential for multi-source data integration
- Point-in-time ticker mapping is critical for accurate historical backtests

## Summary

Ticker symbols are convenient but unreliable for persistent identification due to changes, reuse, and ambiguity. Industry-standard identifiers (CUSIP, ISIN, FIGI, SEDOL) provide stable, unique identification across time and systems. Trading algorithms should use Symbol objects that encapsulate both the human-readable ticker and the persistent identifier. Derivative instruments require structured symbology encoding expiration dates and strike prices.

## Source

- Based on [QuantConnect: Key Concepts — Security Identifiers](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/security-identifiers)
