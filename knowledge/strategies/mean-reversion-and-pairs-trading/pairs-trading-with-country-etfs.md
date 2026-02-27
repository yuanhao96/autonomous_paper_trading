# Pairs Trading with Country ETFs

## Overview

Distance-based pairs trading on 25 international country ETFs. During a 120-day formation period, computes normalized cumulative price indices and selects the top 5 closest pairs by distance. Trades when spreads diverge beyond 0.5× the formation distance, targeting mean reversion within a 20-day trading window.

## Academic Reference

- **Paper**: "Pairs Trading on International ETFs" — Panagiotis, Dimitrios & Tao
- **Source**: SSRN Abstract ID: 1958546

## Strategy Logic

### Universe Selection

25 international ETFs: EWY, EWP, EWD, EWL, GXC, EWC, EWZ, AIA, EWJ, EWH, EIDO, EWO, EWK, EWI, EZU, EWQ, ADRU, EWW, IVV, ECH, AAXJ, ENZL, NORW, GAF, and others.

### Signal Generation

**Formation period (120 trading days)**:
1. Compute normalized cumulative price indices: R_t = ∏(1 + r_t).
2. Calculate distance: D = (1/120) × Σ|P_a − P_b| for all pairs.
3. Select top 5 pairs with smallest distances.

**Trading period (20 days)**:
Monitor spread (index_a − index_b) relative to 0.5 × distance threshold.

### Entry / Exit Rules

- **Long pair**: When index_a − index_b < −0.5 × distance → short B, long A.
- **Short pair**: When index_a − index_b > 0.5 × distance → short A, long B.
- **Exit**: Liquidate when spread reverts within (−0.5 × distance, +0.5 × distance).
- Dollar-neutral positioning.

### Portfolio Construction

5% of portfolio per asset in each pair trade. Maximum 5 concurrent pair positions. Dollar-neutral (equal capital in long/short legs).

### Rebalancing Schedule

Monthly. Pairs reselected after each 20-day trading window.

## Key Indicators / Metrics

- Normalized cumulative price indices
- Distance metric (mean absolute price deviation)
- Threshold: 0.5 × calculated distance
- Formation period: 120 days
- Trading period: 20 days

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2011 – Aug 2018 |
| Initial Capital | $100,000 |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: International equity ETFs (25 countries)
- **Resolution**: Daily
- **Lookback Period**: 121 days minimum per security
- **Data**: Daily closing prices

## Implementation Notes

- Python `deque` container for fixed-length rolling price series.
- `itertools` for generating all symbol pair combinations.
- Floor function for whole-share calculations.
- Scheduled events for monthly rebalancing.
- Position sizing reduced from original to avoid margin calls.
- Python on QuantConnect LEAN.

## Risk Considerations

- Mean reversion assumption — pairs may permanently diverge (structural break).
- Continued co-movement of paired country ETFs is not guaranteed.
- Historical distance may not predict future convergence.
- Emerging market ETFs have liquidity constraints and wider spreads.
- Currency risk in international ETFs adds noise to distance calculations.
- 5% per-asset allocation limits return potential but also limits risk.
- Monthly pair reselection may be too slow during volatile markets.

## Related Strategies

- [Pairs Trading with Stocks](pairs-trading-with-stocks.md)
- [Mean Reversion Effect in Country Equity Indexes](mean-reversion-effect-in-country-equity-indexes.md)
- [Value Effect Within Countries](../value-and-fundamental/value-effect-within-countries.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/pairs-trading-with-country-etfs)
