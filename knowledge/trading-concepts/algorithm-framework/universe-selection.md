# Universe Selection

## Overview

Universe selection determines which assets are available for trading at any given time.
It is the first stage in the algorithm framework pipeline — all downstream components
(signal generation, portfolio construction, risk management, execution) operate only on
the assets that the universe model surfaces. A well-designed universe keeps the strategy
focused on tradeable, relevant instruments while filtering out noise.

## Selection Approaches

### Manual / Static Universes

A fixed, predefined set of assets (e.g., a handful of ETFs, specific currency pairs, or
a single equity). This is the simplest approach and is best suited for strategies that
target a known, narrow list of instruments. Because the set never changes, there is no
overhead from security additions or removals during the backtest or live session.

### Fundamental Universes

Filter the investable universe using fundamental data such as market capitalization,
price-to-earnings ratio, sector classification, or revenue growth. A typical
implementation uses **two-stage filtering**:

1. **Coarse filter** — fast, lightweight pass that screens on price, dollar volume, and
   whether fundamental data exists. This dramatically reduces the candidate pool before
   expensive calculations run.
2. **Fine filter** — detailed fundamental metrics applied to the smaller candidate set.
   Examples include selecting the top 100 stocks by market cap within a specific sector,
   or requiring a minimum return on equity.

Two-stage filtering is critical for performance: running fine-grained fundamental
calculations on thousands of securities is expensive, so the coarse pass keeps costs low.

### Scheduled Universes

Trigger the selection logic at regular calendar intervals — daily, weekly, or monthly.
This is useful for strategies that rebalance on a fixed schedule and do not need
intraday universe changes. Scheduled universes reduce unnecessary computation and
prevent excessive turnover caused by noisy daily fluctuations.

### Custom Universes

Fully user-defined selection logic driven by any data source: alternative data feeds,
custom databases, external APIs, or proprietary scoring models. Custom universes offer
maximum flexibility but require the developer to handle data retrieval and filtering.

## Key Concepts

### Universe Changes and Security Lifecycle

When the universe model adds or removes an asset, the framework fires events that the
rest of the pipeline must handle. Newly added securities need data subscriptions,
indicator warm-up, and state initialization. Removed securities should have open
positions considered for liquidation and their associated state cleaned up.

### Security Initialization

Each security added to the universe must be configured with appropriate settings:
- **Data normalization mode** — adjusted vs. raw prices for equities with splits/dividends.
- **Leverage** — the maximum allowable leverage for position sizing.
- **Resolution** — tick, second, minute, hour, or daily data granularity.

### Dynamic vs. Static Universes

Static universes never change composition. Dynamic universes update periodically,
and the framework must gracefully handle the resulting churn — warming up indicators
for new additions and winding down positions for removals.

### Universe Size Considerations

- **Too few assets** — concentration risk; a single adverse event can dominate returns.
- **Too many assets** — higher transaction costs, data overhead, and potential for
  over-diversification that dilutes alpha.
- A practical range depends on strategy type. Stat-arb may need hundreds of names;
  a macro strategy may need fewer than ten.

## Best Practices

1. **Start with coarse filters for efficiency.** Always reduce the candidate pool with
   cheap checks (price > $5, volume > 1M shares/day) before applying expensive logic.
2. **Enforce liquidity and market-cap minimums.** Illiquid or micro-cap names introduce
   slippage risk and unrealistic backtest fills.
3. **Account for survivorship bias.** Use point-in-time data that includes delisted
   securities; otherwise backtests overstate performance by only including survivors.
4. **Balance rebalance frequency.** Frequent rebalancing captures changes quickly but
   increases turnover and costs. Weekly or monthly rebalancing is sufficient for most
   fundamental strategies.
5. **Log universe changes.** Track additions and removals over time to debug unexpected
   behavior and understand portfolio turnover drivers.
6. **Warm up indicators before trading.** New securities should not generate signals
   until their technical indicators have enough history to be meaningful.

---
*Source: QuantConnect Algorithm Framework documentation.*
