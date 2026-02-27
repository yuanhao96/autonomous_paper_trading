# Using News Sentiment to Predict Price Direction of Drug Manufacturers

## Overview

NLP-based strategy using dictionary sentiment analysis on news headlines to predict intraday price direction of drug manufacturing stocks. Trades only on Wednesdays (day-of-week anomaly), entering 30 minutes after open and exiting at close. Long-only on positive cumulative sentiment.

## Academic Reference

- **Papers**: Isah, Shah & Zulkernine (2018) — "Predicting the Effects of News Sentiments on the Stock Market"; Berument & Kiymaz (2001) — day-of-week anomalies.

## Strategy Logic

### Universe Selection

1. Top 2,500 stocks by dollar volume with fundamental data.
2. Filter to drug manufacturing industry (MorningStar classification).
3. Top 50 by P/E ratio.

### Signal Generation

**NLP pipeline**:
1. Retrieve news articles (Tiingo News Feed) — titles and descriptions.
2. Extract n-grams (single to multi-word phrases).
3. Match against curated sentiment dictionary (~70 phrases).
4. Compute cumulative sentiment score per stock.

### Entry / Exit Rules

- **Long**: Non-zero cumulative positive sentiment → enter 30 minutes after market open.
- **Exit**: Liquidate at market close (same-day intraday positions).
- **Day filter**: Trade only on Wednesdays.

### Portfolio Construction

EqualWeightingPortfolioConstructionModel. ImmediateExecutionModel. Daily liquidation.

### Rebalancing Schedule

Daily (Wednesdays only). Intraday entry/exit.

## Key Indicators / Metrics

- Cumulative news sentiment score
- N-gram phrase matching
- Day-of-week filter (Wednesday)
- 30-minute post-open entry delay

## Backtest Performance

| Metric | Strategy | SPY Benchmark |
|--------|----------|---------------|
| Sharpe (2019–2022) | -1.619 | -0.579 |

"Strategy achieves profitability only after restricting trading to Wednesday." Transaction costs and spreads erode returns.

## Data Requirements

- **Asset Classes**: US equities (drug manufacturers)
- **Resolution**: Minute
- **Alternative Data**: Tiingo News Feed (real-time)
- **Fundamental Data**: MorningStar sector classification, P/E ratios
- **Libraries**: NLTK (n-grams)

## Implementation Notes

- DrugNewsSentimentAlphaModel, SymbolData, DrugManufacturerUniverseSelection classes.
- Sentiment dictionary: lowercase phrases with integer sentiment values.
- NLTK n-grams utility for phrase extraction.
- Python on QuantConnect LEAN.

## Risk Considerations

- Sharpe ratio (−1.619) — strategy significantly loses money.
- Dictionary-based sentiment is simplistic — misses context, sarcasm, and nuance.
- Drug manufacturing is a narrow sector — high idiosyncratic risk from FDA decisions.
- Wednesday-only trading is a fragile day-of-week anomaly.
- Transaction costs severely impact intraday profitability.
- Sentiment threshold (any non-zero) is too permissive — generates too many false signals.
- Authors suggest geographic filtering, text preprocessing, and expanded dictionaries.

## Related Strategies

- [Gaussian Naive Bayes Model](gaussian-naive-bayes-model.md)
- [Sentiment and Style Rotation Effect in Stocks](../momentum/sentiment-and-style-rotation-effect-in-stocks.md)
- [Gradient Boosting Model](gradient-boosting-model.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/using-news-sentiment-to-predict-price-direction-of-drug-manufacturers)
