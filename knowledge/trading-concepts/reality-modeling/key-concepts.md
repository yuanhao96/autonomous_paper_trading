# Reality Modeling — Key Concepts

## Overview

Reality modeling makes backtests as realistic as possible to how a strategy would perform
in live trading. Without accurate reality models, backtests produce overly optimistic
results that don't survive contact with real markets. Every algorithmic trading platform
must bridge the gap between simulated and actual execution.

## Why Reality Modeling Matters

- **Backtesting accuracy**: Unrealistic backtests lead to false confidence and real losses.
- **Strategy capacity**: Determines how much capital a strategy can handle before market impact degrades returns.
- **Execution realism**: Models the gap between theoretical and actual trading performance.
- **Cost awareness**: Accounts for all friction costs — fees, slippage, spread, and market impact.

## Components of Reality Modeling

| Component | What It Models | Impact on Returns |
|-----------|---------------|-------------------|
| Brokerage Model | Broker constraints, supported features | Determines what's tradeable |
| Fee Model | Transaction costs per order | Direct cost reduction |
| Slippage Model | Price impact of orders | Hidden execution cost |
| Fill Model | How orders get filled (partial, timing) | Execution uncertainty |
| Settlement Model | When funds become available | Cash flow timing |
| Buying Power / Margin | Available leverage | Position sizing limits |
| Volatility Model | Price volatility estimation | Options pricing, risk |

## The Simulation Pipeline

When a backtest engine processes a trade, it flows through a chain of reality models:

```
Order placed
  -> Fee calculation
    -> Fill simulation (with slippage)
      -> Settlement
        -> Portfolio update
```

Each stage can reject, modify, or delay the order — just as a real broker would.

## Per-Security Configuration

Each security can (and should) have different reality models. For example:

- **US Equities**: T+1 settlement, SEC/FINRA fees, market-maker fill model.
- **Forex**: Immediate settlement, spread-based costs, no exchange fees.
- **Futures**: Margin-based, exchange fees, daily settlement (mark-to-market).
- **Crypto**: Immediate settlement, percentage-based fees, 24/7 market hours.

This per-security granularity prevents a one-size-fits-all model from silently
distorting results for asset classes with very different trading mechanics.

## Common Backtesting Pitfalls

| Pitfall | Why It's Dangerous |
|---------|--------------------|
| Zero-fee assumption | Even small fees compound over many trades |
| Instant fills | Real orders have latency and partial fills |
| No slippage | Large orders move the market against you |
| Unlimited liquidity | You can't always get the desired fill size |
| Ignoring spreads | The bid-ask spread is a real and constant cost |
| Forward-looking data | Using information not available at trade time |

Any single pitfall can turn a profitable backtest into a losing live strategy.

## Best Practices

1. **Start conservative.** Use pessimistic assumptions for slippage, fees, and fill rates.
   It is better to be pleasantly surprised in live trading than painfully disappointed.
2. **Validate against live results.** If you have historical live fills, compare them to
   your backtest fills for the same period.
3. **Add a safety margin.** Increase slippage and fee estimates by 50-100% beyond your
   best estimate. This buffers against model error.
4. **Test at multiple scales.** A strategy that works with $100K may fail at $10M due to
   market impact. Find the capacity ceiling.
5. **Model different market regimes.** Test under normal conditions, high-volatility periods,
   and low-liquidity environments (e.g., holidays, after-hours).
6. **Iterate on the model.** As you gather live data, continuously refine your reality
   models to better match observed execution quality.

## Key Takeaway

Reality modeling is not an optional refinement — it is a prerequisite for any backtest
result to be trustworthy. The closer your simulation matches real-world execution, the
more confidently you can deploy capital.

---

Source: Generalized from QuantConnect Reality Modeling documentation.
