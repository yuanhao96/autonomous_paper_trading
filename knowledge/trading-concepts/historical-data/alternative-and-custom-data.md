# Alternative & Custom Data

## Overview

Beyond standard price and volume data, modern algorithmic trading increasingly relies on
alternative and custom data sources. These can provide unique alpha signals not captured
by traditional market data.

## Alternative Data Categories

### Fundamental Data

- **Financial statements**: Revenue, earnings, assets, liabilities (quarterly and annual).
- **Valuation ratios**: P/E, P/B, EV/EBITDA, dividend yield.
- **Growth metrics**: Revenue growth, earnings growth, ROE, ROIC.
- **Quality metrics**: Debt-to-equity, current ratio, free cash flow margin.
- **Sources**: SEC filings (EDGAR), company investor relations, data vendors
  (Bloomberg, Refinitiv, S&P Capital IQ).

### Sentiment Data

- **News sentiment**: NLP-derived scores from financial news articles.
- **Social media**: Twitter/Reddit/StockTwits sentiment, posting volume, trending tickers.
- **Analyst ratings**: Consensus estimates, target price changes, upgrades/downgrades.
- **Earnings call tone**: NLP analysis of management commentary during conference calls.
- **Sources**: RavenPack, Alexandria, Quandl, proprietary NLP pipelines.

### Economic Data

- **Macroeconomic indicators**: GDP, CPI, unemployment rate, PMI.
- **Central bank data**: Interest rate decisions, monetary policy statements, balance sheets.
- **Yield curves**: Treasury rates across maturities, term structure dynamics.
- **Housing and consumer data**: Housing starts, consumer confidence, retail sales.
- **Sources**: FRED (Federal Reserve Economic Data), World Bank, IMF, BLS.

### Event Data

- **Earnings announcements**: Dates, EPS surprises, revenue surprises, forward guidance.
- **Corporate actions**: Splits, dividends, mergers, acquisitions, buybacks, spinoffs.
- **Insider trading**: SEC Form 4 filings — insider buy/sell patterns and volumes.
- **Institutional holdings**: 13F filings showing quarterly positions of large investors.
- **Regulatory filings**: 10-K (annual), 10-Q (quarterly), 8-K (material events).

### Exotic Alternative Data

- **Satellite imagery**: Parking lot counts, crop health, oil storage levels.
- **Web traffic**: Company website visits, app downloads, Google Trends.
- **Credit card data**: Aggregated consumer spending by merchant category.
- **Geolocation**: Foot traffic to retail locations, airports, factories.
- **Patent filings**: Innovation indicators, competitive intelligence.
- **Job postings**: Hiring trends as a proxy for company growth or contraction.

## Custom Data Integration

When incorporating a new data source into a trading system, follow these steps:

1. **Define the data schema.** Specify column names, data types, timestamp format,
   and update frequency. Establish what each row represents (one observation per day?
   per event? per symbol?).
2. **Implement a data reader/parser.** Write code that can ingest the raw data (CSV,
   JSON, API response) and convert it into the internal format your system expects.
3. **Handle timezone alignment.** Ensure that data timestamps align with your market
   data. Economic releases are often in ET; satellite data may be in UTC; social
   media data is continuous. Misalignment causes look-ahead bias.
4. **Deal with irregular frequencies.** Unlike daily price bars, alternative data
   often arrives at irregular intervals (earnings quarterly, news randomly, satellite
   weekly). Your system must handle this without forward-filling prematurely.
5. **Validate data quality.** Check for missing values, outliers, stale records, and
   format changes. Data vendors occasionally alter schemas without notice.

## Best Practices

- **Evaluate signal decay.** How quickly does the data lose predictive value after
  release? News sentiment may decay in hours; fundamental data may persist for weeks.
- **Assess coverage and history.** A dataset covering only 50 stocks or only 2 years
  of history limits the strategies you can build and the confidence of backtests.
- **Check for survivorship bias.** Many alternative datasets only include currently
  active entities, which inflates historical performance.
- **Consider cost vs. alpha.** Premium alternative data can cost thousands per month.
  Ensure the expected alpha justifies the licensing expense.
- **Combine multiple sources.** Single alternative data signals are often weak.
  Combining several (e.g., sentiment + insider trading + earnings surprise) improves
  robustness and reduces overfitting to any one signal.
- **Backtest with realistic delays.** Model the actual delivery lag of the data.
  If satellite imagery is delivered with a 3-day delay, your backtest must reflect that.
- **Monitor for regime changes.** Alternative data relationships can break down.
  A signal that worked pre-2020 may not work post-pandemic. Continuous monitoring
  and periodic revalidation are essential.

## Key Takeaways

1. Alternative data provides informational edges beyond price and volume.
2. Categories span fundamentals, sentiment, economics, events, and exotic sources.
3. Integrating custom data requires careful schema design, timezone handling, and validation.
4. Always evaluate signal decay, coverage, cost, and potential biases before committing.
5. Combine multiple data sources and monitor for regime changes over time.

---

Source: Generalized from QuantConnect Historical Data documentation.
