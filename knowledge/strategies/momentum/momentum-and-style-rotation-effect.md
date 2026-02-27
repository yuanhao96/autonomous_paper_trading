# Momentum and Style Rotation Effect

## Overview

A systematic momentum-based strategy exploiting performance differences across equity style categories. Uses six index ETFs representing the style box (large/mid/small × value/growth) to go long the highest-momentum style and short the lowest-momentum style.

## Academic Reference

- **Paper**: "Momentum and Style Rotation Effect" — Quantpedia Screener #91
- **Link**: https://quantpedia.com/Screener/Details/91

## Strategy Logic

### Universe Selection

Six ETFs representing the equity style box:

| ETF | Category |
|-----|----------|
| IVE | S&P 500 Value (Large Value) |
| IVW | S&P 500 Growth (Large Growth) |
| IJJ | S&P Mid-Cap 400 Value |
| IJK | S&P Mid-Cap 400 Growth |
| IJS | S&P Small-Cap 600 Value |
| IJT | S&P Small-Cap 600 Growth |

### Signal Generation

MomentumPercent (MOMP) indicator with 12-month lookback (~240 trading days). ETFs ranked by MOMP value.

### Entry / Exit Rules

- **Long**: Highest-momentum ETF at 50% portfolio allocation.
- **Short**: Lowest-momentum ETF at -50% portfolio allocation.
- **Liquidate**: Four middle-ranked ETFs.

### Portfolio Construction

50% long / 50% short — single ETF on each side. Market-neutral by construction.

### Rebalancing Schedule

Monthly, at month start (using IJJ as schedule anchor).

## Key Indicators / Metrics

- MomentumPercent (MOMP): ~240-day lookback
- Style box categorization (value/growth × size)

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2001 – Aug 2018 |
| Initial Capital | $100,000 |
| Resolution | Daily |

*(Detailed return/Sharpe metrics not disclosed.)*

## Data Requirements

- **Asset Classes**: US equity style ETFs (6 tickers)
- **Resolution**: Daily
- **Lookback Period**: ~240 trading days (12 months)

## Implementation Notes

- Momentum indicator stored in dictionary structure for each symbol.
- Security initializer with brokerage model implementation.
- Warm-up period matches lookback length.
- Monthly schedule-based rebalancing trigger.
- Simple, compact implementation — no fundamental data needed.

## Risk Considerations

- Only 2 positions (1 long, 1 short) — concentrated factor bet.
- Style rotation may be slow or nonexistent in certain market regimes.
- No explicit transaction costs, slippage, or survivorship bias adjustments.
- Growth/value definitions embedded in index methodology may shift over time.
- Long backtest period (2001–2018) spans multiple regimes, which is positive for robustness.

## Related Strategies

- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)
- [Sector Momentum](sector-momentum.md)
- [Asset Class Momentum](asset-class-momentum.md)
- [Sentiment and Style Rotation Effect in Stocks](sentiment-and-style-rotation-effect-in-stocks.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/momentum-and-style-rotation-effect)
