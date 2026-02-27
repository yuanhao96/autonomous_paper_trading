# Market Hours & Data Handling

## Overview

Different securities trade at different times across different exchanges and time zones. Properly handling market hours, data gaps, and cross-market synchronization is essential for algorithmic trading.

## Market Hours by Exchange

### Major US Exchanges

| Exchange | Pre-Market | Regular | After-Hours |
|----------|-----------|---------|-------------|
| NYSE / NASDAQ | 4:00-9:30 ET | 9:30-16:00 ET | 16:00-20:00 ET |
| CME (Futures) | 17:00 CT (prev day) | Nearly continuous | 16:00-17:00 CT break |
| CBOE (Options) | — | 9:30-16:00 ET | — |

### Global Markets

| Region | Exchange | Hours (Local) | UTC Offset |
|--------|----------|---------------|-----------|
| US | NYSE | 9:30-16:00 ET | UTC-5 / UTC-4 |
| UK | LSE | 8:00-16:30 GMT | UTC+0 / UTC+1 |
| Europe | Euronext | 9:00-17:30 CET | UTC+1 / UTC+2 |
| Japan | TSE | 9:00-15:00 JST | UTC+9 |
| China | SSE | 9:30-15:00 CST | UTC+8 |
| Australia | ASX | 10:00-16:00 AEST | UTC+10 / UTC+11 |
| India | NSE | 9:15-15:30 IST | UTC+5:30 |
| Hong Kong | HKEX | 9:30-16:00 HKT | UTC+8 |

## Data Handling Concepts

### Fill Forward

- If no new data arrives for a given bar period, repeat the previous bar's close
- Prevents gaps in the data series that could break indicator calculations
- Important distinction: fill-forwarded data does not represent real trading activity
- Algorithms should check whether a bar is fill-forwarded before acting on it

### Extended Market Hours Data

- Pre-market and after-hours data is available but significantly less liquid
- Wider bid-ask spreads and thinner order books during extended hours
- Some strategies specifically target these periods for earnings reactions
- Volume is typically 5-15% of regular session volume

### Data Filtering

- Filter out bars with zero volume (no actual trading occurred)
- Handle trading halts gracefully (no data is generated during a halt)
- Adjust for half-trading days around holidays (early close at 13:00 ET for US markets)
- Be aware of exchange-specific quirks (e.g., TSE lunch break 11:30-12:30)

### Corporate Actions

- **Stock splits**: Adjust historical prices and position quantities proportionally
- **Dividends**: Adjust prices on ex-date when using adjusted data mode
- **Mergers and acquisitions**: Handle symbol changes, cash/stock consideration
- **Spin-offs**: New securities created; cost basis must be allocated
- **Delistings**: Security becomes untradable; positions must be liquidated or written off

### Cross-Market Data Synchronization

- Align data from different exchanges by converting all timestamps to UTC
- Handle gaps when one market is closed but another is open
- Use fill-forward to maintain data continuity for cross-market strategies
- Be cautious with correlations calculated across markets with non-overlapping hours

## Daylight Saving Time

- **US**: Second Sunday in March to first Sunday in November (EDT, UTC-4)
- **Europe**: Last Sunday in March to last Sunday in October (CEST, UTC+2)
- **Misalignment period**: Approximately two weeks in March and one week in November when US and European offsets differ from the usual gap
- Algorithms must handle these transitions to avoid incorrect market hours checks
- Some markets (Japan, China, India) do not observe DST

## Holidays and Special Sessions

- Each exchange maintains its own holiday calendar
- US markets close on ~9 holidays per year; early closes on ~3 additional days
- Global strategies must track holidays for every market they trade
- Reduced liquidity on days adjacent to holidays ("half days" by convention)

## Best Practices

- Store all timestamps in UTC internally; convert to local time only for display
- Convert to exchange local time only for market hours checks and scheduling
- Account for holidays in each market — do not assume all markets share the same calendar
- Test strategies across DST transitions to catch time-zone-related bugs
- Handle overnight gaps (equity close to next-day open) in risk and P&L calculations
- Monitor for exchange-specific circuit breakers and trading halts (e.g., LULD in US equities)
- Use exchange-provided calendars or reliable third-party holiday data
- Log and alert on unexpected data gaps that might indicate feed issues vs. genuine market closures

Source: Generalized from QuantConnect Securities documentation.
