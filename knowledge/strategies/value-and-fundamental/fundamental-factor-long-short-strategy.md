# Fundamental Factor Long Short Strategy

## Overview

AQR-inspired long/short equity strategy combining value, quality, and momentum factors. Ranks 250 liquid stocks on a weighted composite score (40% value, 40% quality, 20% momentum), goes long the top 10 and shorts the bottom 10 with monthly rebalancing.

## Academic Reference

- **Paper**: "A New Core Equity Paradigm" — AQR Capital Management
- Adapted from a long-only approach into a long/short equity strategy.

## Strategy Logic

### Universe Selection

1. All US equities with fundamental data.
2. Price filter: > $5.
3. Sort by dollar volume, select top 250.

### Signal Generation

**Three factors**, each ranked 1–250:

1. **Value (40%)**: Book value per share — higher = better ranked.
2. **Quality (40%)**: Operating margin — higher = better ranked.
3. **Momentum (20%)**: 1-month price return — higher = better ranked.

**Composite score**: `(value_rank × 0.4) + (quality_rank × 0.4) + (momentum_rank × 0.2)`

Lower composite score = better opportunity.

### Entry / Exit Rules

- **Long**: Top 10 stocks (lowest composite scores).
- **Short**: Bottom 10 stocks (highest composite scores).
- **Exit**: Full reconstitution at monthly rebalance.

### Portfolio Construction

Equal-weight: 4.5% per position (90% invested, 10% cash buffer to prevent margin calls).

### Rebalancing Schedule

Monthly, 5 minutes after market open on the first trading day.

## Key Indicators / Metrics

- Book Value Per Share (value factor)
- Operating Margin (quality factor)
- 1-month price return (momentum factor)
- Weighted composite rank score

## Backtest Performance

| Metric | Value |
|--------|-------|
| Period | 2015 – 2018 |
| Initial Capital | $100,000 |
| Result | Consistently beats market benchmark |
| Note | Short leg improves returns vs. long-only variant |

## Data Requirements

- **Asset Classes**: US equities
- **Resolution**: Daily
- **Fundamental Data**: Book value per share, operating margin, dollar volume
- **Price Data**: 1-month trailing returns
- **Lookback**: 1 month (momentum)

## Implementation Notes

- `CoarseSelectionFunction`: Dollar volume filtering.
- `FineSelectionFunction`: Factor ranking and composite score calculation.
- `ScheduledEvent`: Monthly rebalance trigger.
- 10% cash buffer prevents margin calls on short positions.
- Python on QuantConnect LEAN.

## Risk Considerations

- Operating margin alone may not capture full quality picture — misses balance sheet health, earnings quality.
- Monthly turnover in a 20-stock portfolio generates meaningful transaction costs.
- Equal-weighting ignores volatility differences across positions.
- Short positions carry theoretically unlimited loss potential.
- 250-stock universe is mid-sized — may miss smaller value opportunities.
- Factor weights (40/40/20) are fixed — no regime adaptation.
- Backtest period (2015–2018) is relatively short.

## Related Strategies

- [Stock Selection Based on Fundamental Factors](stock-selection-based-on-fundamental-factors.md)
- [Fama-French Five Factors](../factor-investing/fama-french-five-factors.md)
- [Earnings Quality Factor](../factor-investing/earnings-quality-factor.md)

## Source

- [QuantConnect Strategy Library](https://www.quantconnect.com/learning/articles/investment-strategy-library/fundamental-factor-long-short-strategy)
