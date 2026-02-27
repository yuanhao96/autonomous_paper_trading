# Project Structure & Strategy Index — Design

## Folder Hierarchy

Flat categories under `strategies/`:

```
strategies/
├── README.md                          # Master index (all 83 strategies by category)
├── momentum/                          # ~24 strategies
├── factor-investing/                  # 10 strategies
├── mean-reversion-and-pairs-trading/  # 10 strategies
├── calendar-anomalies/                # 9 strategies
├── value-and-fundamental/             # 7 strategies
├── volatility-and-options/            # 5 strategies
├── forex/                             # 4 strategies
├── commodities/                       # 4 strategies
├── machine-learning/                  # 5 strategies
└── technical-and-other/               # 5 strategies
```

Each category folder contains a `README.md` listing its strategies and individual `.md` files per strategy.

## Document Template

Each strategy file follows this structure:

1. **Overview** — Core thesis in 2-3 sentences
2. **Academic Reference** — Paper title, authors, year, link
3. **Strategy Logic** — Universe selection, signal generation, entry/exit rules, portfolio construction, rebalancing
4. **Key Indicators / Metrics** — Technical indicators or financial metrics used
5. **Backtest Performance** — Period, benchmark, results table (Sharpe, returns, drawdown)
6. **Data Requirements** — Asset classes, resolution, lookback period
7. **Implementation Notes** — Code architecture, key classes/methods
8. **Risk Considerations** — Assumptions, limitations, failure modes
9. **Related Strategies** — Cross-references
10. **Source** — QuantConnect URL

## URL Pattern

Strategy detail pages: `https://www.quantconnect.com/learning/articles/investment-strategy-library/<slug>`

Slug is the kebab-case strategy name (e.g., `gaussian-naive-bayes-model`, `momentum-effect-in-stocks`).

## Strategy-to-Category Mapping

See `strategies/README.md` for the complete mapping of all 83 strategies to categories.
