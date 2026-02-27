# Momentum Effect in REITs

## Overview

Exploits the momentum anomaly specifically within Real Estate Investment Trusts (REITs), holding the top-performing tercile with quarterly rebalancing. Uses an 11-month momentum calculation with a 1-month lag to avoid short-term reversal effects.

## Academic Reference

- **Paper**: "Momentum Effect in REITs" — Quantpedia Screener #152
- **Link**: https://quantpedia.com/Screener/Details/152

## Strategy Logic

### Universe Selection

1. **Coarse filter**: Stock price > $1, must have fundamental data, trading volume > 10,000 shares. Applied only during quarterly rebalance periods.
2. **Fine filter**: Filter for REITs using Morningstar's `IsREIT` field.

### Signal Generation

11-month momentum with 1-month lag:

```
Momentum = (End_Price - Start_Price) / Start_Price
```

Historical window: 365 days back to 30 days back (i.e., months 2–12, skipping the most recent month).

### Entry / Exit Rules

- **Long**: Top tercile (top third) of ranked REITs by momentum score.
- **Exit**: Holdings outside top tercile liquidated at rebalance.

### Portfolio Construction

Equal weight across selected holdings:

```
Weight = 1 / portfolio_size
where portfolio_size = total_REITs / 3
```

### Rebalancing Schedule

Quarterly. Monthly checks trigger every three months via Scheduled Event.

## Key Indicators / Metrics

- 11-month momentum (with 1-month lag)
- Morningstar `IsREIT` classification
- Trading volume > 10,000 shares

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Dec 2010 – Jul 2018 |
| Initial Capital | $1,000,000 |
| Benchmark | SPY |
| Resolution | Daily |

*(Detailed return/Sharpe metrics not disclosed.)*

## Data Requirements

- **Asset Classes**: US REITs
- **Resolution**: Daily
- **Lookback Period**: 365 days (with 30-day recency exclusion)
- **Fundamental Data**: Morningstar (REIT classification, volume)

## Implementation Notes

- Key methods: `_coarse_selection_function()`, `_fine_selection_function()`, `_rebalance()`, `on_data()`.
- The 1-month lag (skipping most recent 30 days) is a deliberate design choice to avoid capturing short-term reversal noise.
- Python implementation on QuantConnect LEAN.

## Risk Considerations

- Long-only — no short leg to capture full momentum premium.
- REIT-specific risk: interest rate sensitivity, sector concentration.
- 30-day lag may miss reversal patterns or rapid regime changes.
- Tercile approach assumes sufficient REIT universe size.
- Backtest period (2010–2018) was generally favorable for REITs (low rates) — may not generalize.
- Equal weighting doesn't account for momentum strength differences.

## Related Strategies

- [Momentum Effect in Stocks](momentum-effect-in-stocks.md)
- [Sector Momentum](sector-momentum.md)
- [Momentum and Style Rotation Effect](momentum-and-style-rotation-effect.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/momentum-effect-in-reits)
