# Momentum and State of Market Filters

## Overview

Combines stock momentum with a market regime filter: when the broad market is in an "UP" state, trade momentum long/short; when "DOWN," liquidate all equities and rotate to Treasury bonds. Based on the finding that momentum returns depend significantly on broader market conditions.

## Academic Reference

- **Paper**: "Market States and Momentum" — Gutierrez, Cooper, and Hameed

## Strategy Logic

### Universe Selection

All NYSE and NASDAQ equities with price > $1 and fundamental data.

### Signal Generation

**Market State Filter** (Wilshire 5000 Total Market Index via FRED):
- 252-day (12-month) Rate of Change (ROC)
- Positive ROC = "UP" state; negative = "DOWN" state

**Stock Momentum**:
- MomentumPercent (MOMP) with 120-day (6-month) lookback
- Rank all stocks by MOMP

### Entry / Exit Rules

**When Market = UP**:
- Long top 20 stocks by momentum (1.25% each, 25% total)
- Short bottom 20 stocks by momentum (-1.25% each, -25% total)

**When Market = DOWN**:
- Liquidate all equity positions
- Allocate 100% to TLT (Treasury ETF)

### Portfolio Construction

Equal-weight within long/short buckets. 50% net exposure (25% long, 25% short) during UP state. 100% Treasury during DOWN state.

### Rebalancing Schedule

Monthly, first trading day of each month. Universe screened daily; positions updated monthly.

## Key Indicators / Metrics

- Market ROC (Wilshire 5000): 252-day lookback
- Stock MOMP: 120-day lookback
- TLT as safe haven allocation

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2011 – Aug 2018 |
| Initial Capital | $100,000 |

## Data Requirements

- **Asset Classes**: US equities + TLT
- **Resolution**: Daily
- **Lookback Period**: 252 days (market filter), 120 days (stock momentum)
- **External Data**: Wilshire 5000 from FRED (note: now discontinued)
- **Fundamental Data**: Price, fundamental data flags

## Implementation Notes

- **Critical**: Wilshire 5000 FRED dataset discontinued. Substitute: Russell 3000, MSCI U.S. Broad Market, or S&P 500.
- Three blacklisted equities with data issues excluded.
- `SymbolData` updated daily; positions only change monthly.
- PEP8 compliant update available.

## Risk Considerations

- Regime detection lag: 252-day lookback may miss rapid market shifts.
- Binary market state (UP/DOWN) oversimplifies complex regimes.
- Equal weighting concentrates risk in 20 stocks per side.
- Wilshire 5000 discontinuation requires data source substitution.
- Monthly rebalancing may miss intermediate regime changes.
- TLT allocation during DOWN state has duration risk.

## Related Strategies

- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)
- [Asset Class Trend Following](asset-class-trend-following.md)
- [Momentum and Reversal Combined with Volatility Effect in Stocks](momentum-and-reversal-combined-with-volatility-effect-in-stocks.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/momentum-and-state-of-market-filters)
