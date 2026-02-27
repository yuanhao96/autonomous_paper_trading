# Value Effect Within Countries

## Overview

Uses the Cyclically Adjusted Price-to-Earnings (CAPE) ratio to identify undervalued country equity markets. Invests in the cheapest third of 26 country ETFs where CAPE is below 15, equal-weighting positions with monthly rebalancing. Holds cash when no country qualifies.

## Academic Reference

- **Paper**: Based on Robert Shiller's CAPE ratio research (Yale University)
- **Data Source**: Barclays Indices CAPE data, Quantpedia

## Strategy Logic

### Universe Selection

26 country equity ETFs: EWA (Australia), EWZ (Brazil), XIC (Canada), MCHI (China), IEUR (Europe), EWQ (France), EWG (Germany), EWH (Hong Kong), EWI (Italy), INDY (India), EIS (Israel), EWJ (Japan), EWY (South Korea), EWW (Mexico), EWN (Netherlands), EPOL (Poland), ERUS (Russia), EWS (Singapore), EZA (South Africa), EWP (Spain), EWD (Sweden), EWL (Switzerland), EWT (Taiwan), TUR (Turkey), EWU (UK), SPY (USA).

### Signal Generation

1. Retrieve monthly CAPE ratios for all 26 countries.
2. Rank countries by CAPE ratio ascending (lowest = most undervalued).
3. Select the bottom third (~9 countries) with CAPE < 15.

### Entry / Exit Rules

- **Long**: Equal-weight ETFs of countries in the cheapest third with CAPE < 15.
- **Exit**: Liquidate when a country's CAPE rises above the threshold or leaves the bottom third.
- **Cash**: Hold cash if no countries meet the CAPE < 15 threshold.

### Portfolio Construction

Equal-weight among qualifying country ETFs. Cash position when no countries qualify.

### Rebalancing Schedule

Monthly, aligned with CAPE data updates.

## Key Indicators / Metrics

- CAPE ratio (Shiller PE Ratio) — 10-year inflation-adjusted earnings average
- Country ETF prices
- CAPE threshold: 15

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | Jan 2000 – Sep 2018 |
| Universe | 26 country ETFs |
| CAPE Data | Barclays Indices (from Jan 1982) |

## Data Requirements

- **Asset Classes**: International equity ETFs (26 countries)
- **Resolution**: Daily
- **External Data**: Custom CAPE ratio CSV from Barclays Indices
- **Lookback**: 10 years of earnings data (embedded in CAPE)

## Implementation Notes

- Custom CAPE data imported via remote CSV file subscription.
- Dictionary maps country names to ETF tickers.
- Monthly rebalancing triggered by scheduled event.
- Python on QuantConnect LEAN.

## Risk Considerations

- CAPE data is backward-looking (10-year average) — slow to reflect structural changes.
- Strategy may hold 100% cash for extended periods if no country qualifies.
- Concentrated in cheapest markets, which may be cheap for fundamental reasons (political risk, economic decline).
- Emerging market ETFs (ERUS, TUR, EWZ) carry significant country-specific risk.
- ETF tracking error relative to underlying equity markets.
- External data dependency (Barclays CAPE CSV) adds fragility.

## Related Strategies

- [Price Earnings Anomaly](price-earnings-anomaly.md)
- [Book-to-Market Value Anomaly](book-to-market-value-anomaly.md)
- [Beta Factor in Country Equity Indexes](../factor-investing/beta-factor-in-country-equity-indexes.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/value-effect-within-countries)
