# Liquidity Effect in Stocks

## Overview

Exploits the illiquidity premium — less liquid stocks tend to earn higher returns as compensation for the higher transaction costs and difficulty of trading them. The strategy focuses on small-cap stocks within a liquid universe and goes long the most illiquid names while shorting the most liquid, capturing the spread in expected returns driven by liquidity risk.

## Academic Reference

- **Paper**: "Liquidity Effect in Stocks" — Quantpedia Screener #18
- **Link**: https://quantpedia.com/Screener/Details/18

## Strategy Logic

### Universe Selection

1. Select the top 500 US stocks ranked by dollar trading volume (ensures a baseline level of tradability).
2. From these 500 stocks, take the lowest quartile (bottom 125) by market capitalization — isolating small-cap stocks where the liquidity premium is most pronounced.

### Signal Generation

Turnover ratio is used as the liquidity measure:

```
Turnover = Average Daily Trading Volume / Shares Outstanding
```

Average daily volume is computed over a trailing period. All stocks in the small-cap sub-universe are ranked by turnover from lowest to highest.

### Entry / Exit Rules

- **Entry (Long)**: Go long the bottom 5% of stocks by turnover ratio (most illiquid stocks).
- **Entry (Short)**: Go short the top 5% of stocks by turnover ratio (most liquid stocks).
- **Exit**: Liquidate positions at annual rebalance for stocks that no longer qualify for the top or bottom 5%.

### Portfolio Construction

- Equal-weight allocation within each leg (long and short).
- 50/50 capital allocation between the long and short sides.

### Rebalancing Schedule

Annual. Reconstitute the universe and rebalance positions once per year.

## Key Indicators / Metrics

- **Turnover Ratio**: Average Daily Volume / Shares Outstanding
- **Dollar Volume**: Used for initial universe selection (top 500 filter)
- **Market Capitalization**: Used for small-cap quartile selection (bottom 25% of top 500)

## Backtest Performance

| Metric | Strategy | Benchmark |
|--------|----------|-----------|
| Period | Jan 2016 – Jul 2018 | SPY |
| Initial Capital | $1,000,000 | — |
| Resolution | Daily | — |

*(Detailed Sharpe/return metrics not disclosed in source.)*

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily prices and volume data
- **Lookback Period**: Trailing period for average daily volume calculation (typically 20–60 trading days)
- **Fundamental Data**: Shares Outstanding, Market Capitalization

## Implementation Notes

- The two-stage universe selection (top 500 by dollar volume, then bottom quartile by market cap) is designed to find small-cap stocks that are still minimally tradable.
- Turnover ratio provides a share-adjusted liquidity measure that is more comparable across stocks than raw volume.
- The 5% thresholds on each side result in relatively concentrated portfolios (approximately 6–7 stocks per leg from the ~125 stock sub-universe).
- Python implementation on QuantConnect LEAN engine using coarse universe selection for volume and market cap screening.
- Slippage and market impact modeling is particularly important for this strategy, as the long leg consists of illiquid stocks where execution costs can erode returns.

## Risk Considerations

- Illiquid stocks may have wide bid-ask spreads and high market impact costs that are difficult to model accurately in backtests.
- The long leg targets the least liquid stocks, making real-world execution challenging, especially at scale.
- Short selling illiquid stocks may face borrow constraints, high borrow costs, or outright unavailability.
- Annual rebalancing with a concentrated portfolio exposes the strategy to significant idiosyncratic risk between rebalances.
- The illiquidity premium can disappear or reverse during liquidity crises when illiquid stocks experience forced selling.
- Small-cap focus introduces sensitivity to market microstructure changes (e.g., decimalization effects, changes in market maker behavior).

## Related Strategies

- [ROA Effect Within Stocks](roa-effect-within-stocks.md)
- [Asset Growth Effect](asset-growth-effect.md)
- [Earnings Quality Factor](earnings-quality-factor.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/liquidity-effect-in-stocks)
