# Mean Reversion Effect in Country Equity Indexes

## Overview

Exploits long-term mean reversion across international equity markets. Goes long the 4 worst-performing country ETFs over the past 36 months and shorts the 4 best-performing, rebalancing monthly. Based on the premise that countries with extreme past returns tend to revert.

## Academic Reference

- **Paper**: Quantpedia — "Mean Reversion Effect in Country Equity Indexes"
- **Source**: quantpedia.com/Screener/Details/16

## Strategy Logic

### Universe Selection

19 country equity ETFs: EWJ (Japan), EFNL (Finland), EWW (Mexico), ERUS (Russia), IVV (S&P 500), AUD (Australia), EWQ (France), EWH (Hong Kong), EWI (Italy), EWY (Korea), EWP (Spain), EWD (Sweden), EWL (Switzerland), EWC (Canada), EWZ (Brazil), EWO (Austria), EWK (Belgium), BRAQ (Brazil Consumer), ECH (Chile).

### Signal Generation

Rate of Change (ROC) with 756-day lookback (36 months × 21 trading days/month). Rank all 19 ETFs by 36-month return.

### Entry / Exit Rules

- **Long**: Bottom 4 countries (worst 36-month performance).
- **Short**: Top 4 countries (best 36-month performance).
- **Exit**: Positions close at end-of-month when insights expire.

### Portfolio Construction

Equal-weight across 8 total positions (4 long, 4 short). Margin account enabled.

### Rebalancing Schedule

Monthly signal reassessment. Full reconstitution every 36 months.

## Key Indicators / Metrics

- Rate of Change (ROC): 756-day lookback
- Warm-up period: 31 days
- 36-month return ranking

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Mar 2023 – Mar 2024 |
| Resolution | Daily |

## Data Requirements

- **Asset Classes**: International equity ETFs (19 countries)
- **Resolution**: Daily
- **Lookback Period**: 36 months (756 trading days)
- **Warm-up**: 31 days

## Implementation Notes

- Multi-module Python system: universe selection, alpha generation, portfolio construction.
- ROC indicator with 756-day period.
- Corporate action handling: indicator reset on splits/dividends.
- NullRiskManagementModel, ImmediateExecutionModel.
- Python on QuantConnect LEAN.

## Risk Considerations

- 36-month lookback is extremely long — mean reversion may not occur within a single holding period.
- Mean reversion assumption may fail during structural economic shifts (e.g., sustained emerging market decline).
- Concentrated country exposure — geopolitical and currency risks in international holdings.
- Emerging market ETFs (ERUS, EWZ, TUR) have significant liquidity and political risk.
- Margin requirements and leverage risks from short positions.
- Tax implications of frequent monthly rebalancing in international ETFs.

## Related Strategies

- [Pairs Trading with Country ETFs](pairs-trading-with-country-etfs.md)
- [Value Effect Within Countries](../value-and-fundamental/value-effect-within-countries.md)
- [Momentum Effect in Country Equity Indexes](../momentum/momentum-effect-in-country-equity-indexes.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/mean-reversion-effect-in-country-equity-indexes)
