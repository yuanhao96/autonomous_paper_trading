# Time Zones

## Overview

Covers time zone management in algorithmic trading: algorithm time vs exchange time vs UTC, market hours for different asset classes, handling daylight saving time, and aligning data across global markets. Correct time zone handling is critical for multi-market strategies.

## Three Time References

Every algorithmic trading system tracks three time references:

| Time Reference | Description | Example |
|---------------|-------------|---------|
| **Algorithm Time** | The "local" time of the algorithm, set by the user | New York (ET) |
| **Exchange Time** | The local time of each instrument's exchange | Tokyo (JST) for Nikkei |
| **UTC Time** | Universal coordinated time; the timezone-neutral reference | UTC+0 |

### Algorithm Time

The algorithm's reference clock. All logging, scheduled events, and time comparisons use this time zone.

```python
# Set algorithm time zone (typically done in initialization)
self.set_time_zone("America/New_York")

# Access current algorithm time
current_time = self.time           # In algorithm time zone
utc_time = self.utc_time           # In UTC
```

**Default**: Most platforms default to New York (Eastern Time) since major US exchanges operate in ET.

### Exchange Time

Each exchange has its own local time. The engine tracks exchange time zones internally to:
- Determine market open/close times
- Know when to expect data
- Handle pre-market and after-hours sessions

### UTC as Universal Reference

UTC serves as the internal synchronization layer:
- All data timestamps are stored in UTC internally
- Conversion to algorithm or exchange time happens at display/access time
- UTC has no daylight saving time transitions

## Market Hours

### Major Exchange Hours

| Exchange | Time Zone | Open | Close | Notes |
|----------|-----------|------|-------|-------|
| NYSE/NASDAQ | ET (UTC-5/-4) | 9:30 AM | 4:00 PM | Pre-market 4:00 AM, after-hours to 8:00 PM |
| LSE | GMT/BST (UTC+0/+1) | 8:00 AM | 4:30 PM | |
| TSE (Tokyo) | JST (UTC+9) | 9:00 AM | 3:00 PM | Lunch break 11:30-12:30 |
| HKEX | HKT (UTC+8) | 9:30 AM | 4:00 PM | Lunch break 12:00-1:00 PM |
| Forex | N/A | 24 hours | 24 hours | Sunday 5 PM ET to Friday 5 PM ET |
| Crypto | N/A | 24/7 | 24/7 | No market hours |
| CME Futures | CT (UTC-6/-5) | ~5:00 PM | ~4:00 PM+1 | Nearly 24 hours with breaks |

### Extended Hours

Some instruments trade outside regular market hours:
- **Pre-market**: Lower liquidity, wider spreads
- **After-hours**: Same characteristics
- Extended hours data may need separate subscriptions

## Daylight Saving Time (DST)

DST transitions create complications:

- US clocks change on the 2nd Sunday of March and 1st Sunday of November
- European clocks change on the last Sunday of March and October
- The US-Europe offset shifts by 1 hour during the gap weeks
- Asia-Pacific generally does not observe DST

### Impact on Trading

- Market open/close times shift relative to UTC during DST transitions
- Cross-market strategies must account for the changing time offset
- Scheduled events should use exchange-relative timing (e.g., "30 minutes after market open") rather than fixed UTC times

## Data Alignment Across Time Zones

When trading instruments on exchanges in different time zones:

### Overlapping Hours

```
US and Europe overlap (approx):
  US:     9:30 AM - 4:00 PM ET
  Europe: 8:00 AM - 4:30 PM GMT

  Overlap: 9:30 AM - 11:30 AM ET (2:30 PM - 4:30 PM GMT)
  → Both markets produce live data simultaneously
```

### Non-Overlapping Hours

```
US and Asia:
  US:    9:30 AM - 4:00 PM ET
  Tokyo: 9:00 AM - 3:00 PM JST (7:00 PM - 1:00 AM ET)

  → No overlap; one market is always closed when the other is open
```

When one market is closed:
- Prices for closed-market instruments are stale (fill-forwarded)
- Cross-market signals based on contemporaneous prices may be unreliable
- Consider using close-to-close returns rather than intraday comparisons

## Best Practices

### Use Exchange-Relative Timing

```python
# Good: relative to market events
schedule.on(date_rules.every_day(),
            time_rules.after_market_open("SPY", minutes=30))

# Risky: fixed clock time (breaks with DST changes)
schedule.on(date_rules.every_day(),
            time_rules.at(10, 0))
```

### Store Timestamps in UTC

- Internal data storage should use UTC
- Convert to local time only for display and comparison
- This eliminates ambiguity during DST transitions

### Be Explicit About Time Zones

When comparing times or scheduling events, always specify the time zone explicitly rather than relying on defaults.

## Financial Application Notes

- Forex and crypto trade 24 hours — "daily" bars can be defined with different cut-off times (5 PM ET is conventional for forex)
- Cross-market arbitrage strategies are sensitive to time alignment — microsecond precision matters for HFT
- Economic data releases are typically scheduled in local time — convert to your algorithm's time zone
- Earnings announcements may be pre-market or after-hours, requiring awareness of exchange time
- Rolling daily statistics (volatility, correlation) can shift when markets observe different holidays

## Summary

Time zone management involves tracking three references (algorithm time, exchange time, UTC), understanding market hours for each exchange, handling DST transitions, and correctly aligning data across global markets. Use UTC as the internal reference, exchange-relative timing for scheduled events, and be careful with cross-market signals when markets have non-overlapping hours.

## Source

- Based on [QuantConnect: Key Concepts — Time Modeling — Time Zones](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/time-modeling/time-zones)
