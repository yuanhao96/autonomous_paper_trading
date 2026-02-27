# Sector Momentum

## Overview

Applies momentum rotation principles to sector-based ETFs, systematically reallocating capital to the top-performing sectors. Selects the 3 sectors with strongest 12-month momentum and weights them equally.

## Academic Reference

- **Paper**: "Sector Momentum" — Quantpedia

## Strategy Logic

### Universe Selection

Ten sector-focused ETFs:

| ETF | Sector |
|-----|--------|
| VNQ | Real Estate |
| XLK | Technology |
| XLE | Energy |
| XLV | Healthcare |
| XLF | Financials |
| KBE | Banking |
| VAW | Materials |
| XLY | Consumer Discretionary |
| XLP | Consumer Staples |
| VGT | Information Technology |

### Signal Generation

12-month Momentum (MOM) indicator (period = 3 × 21 trading days = 63 days in implementation). Rank all 10 ETFs by momentum.

### Entry / Exit Rules

- **Long**: Top 3 ETFs by 12-month momentum.
- **Exit**: Securities no longer in top 3 are liquidated before new positions established.

### Portfolio Construction

Equal-weight: 1/3 allocation to each of the 3 selected sector ETFs.

### Rebalancing Schedule

Monthly, at month start via Scheduled Event.

## Key Indicators / Metrics

- Momentum (MOM): 12-month lookback
- Sector classification via ETF selection

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2007–present |
| Initial Capital | $100,000 |

*(Detailed Sharpe/return metrics not disclosed.)*

## Data Requirements

- **Asset Classes**: US sector ETFs (10 tickers)
- **Resolution**: Daily
- **Lookback Period**: 12 months (~252 trading days)

## Implementation Notes

- Straightforward implementation using MOM indicator per symbol.
- Monthly rebalance via Scheduled Event.
- Liquidation of exiting positions occurs before new position establishment.
- Python implementation on QuantConnect LEAN.

## Risk Considerations

- Only 3 positions — high concentration in specific sectors.
- Sector momentum may underperform during sector rotation or market-wide selloffs.
- No hedging or short positions — purely long.
- Overlap between XLK and VGT (both tech-focused) could lead to unintended concentration.
- Monthly rebalancing may be too slow to capture rapid sector shifts.
- No volatility or risk management beyond momentum filtering.

## Related Strategies

- [Asset Class Momentum](asset-class-momentum.md)
- [Momentum and Style Rotation Effect](momentum-and-style-rotation-effect.md)
- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/sector-momentum)
