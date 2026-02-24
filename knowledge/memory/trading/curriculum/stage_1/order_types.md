---
created: '2026-02-24T20:04:32.727014+00:00'
mastery_gaps: []
mastery_reasoning: The agent demonstrates solid practical understanding of order types
  and their appropriate use cases. It correctly identifies when to use market vs.
  limit orders, understands the critical distinction between stop and stop-limit orders
  (execution certainty vs. price control), and grasps advanced concepts like OCO orders,
  trailing stops, and extended hours limitations. The trading implications show functional
  knowledge of real-world application. However, the learning materials appear to be
  reference documentation rather than demonstrated decision-making, and there's no
  evidence of handling edge cases like choosing between stop-limit vs. trailing stop
  in specific volatility conditions, or nuanced scenarios like illiquid options markets
  where standard rules may not apply.
mastery_score: 0.7
sources:
- The Encyclopedia Of Trading Strategies 2000 Part 1 (/Users/howard_openclaw/projects/autonomous_paper_trading/knowledge/memory/trading/discovered/the_encyclopedia_of_trading_strategies_2000_part_1.md)
stage: 1
topic_id: order_types
updated: '2026-02-24T20:04:40.714847+00:00'
---

## 2026-02-24 — The Encyclopedia Of Trading Strategies 2000 Part 1

### Summary

This collection of documents covers fundamental order types (market, limit, stop, stop-limit, trailing stop) used in trading across stocks, ETFs, and forex markets. The materials span from basic mechanics to advanced exit strategies, emphasizing how order selection impacts execution certainty, price control, and risk management in both equity and foreign exchange trading environments.

### Key Concepts

- Market order
- Limit order
- Stop order
- Stop-limit order
- Trailing stop order
- Time in force (Day, GTC, IOC, FOK)
- Fill or kill (FOK)
- All or none (AON)
- Conditional orders
- Peg orders
- One cancels other (OCO)
- One sends other (OSO)
- Bracket orders
- Hidden/iceberg orders
- Entry orders
- Exit strategies
- Profit targets
- Stop losses
- Price gaps
- Extended hours trading
- Market microstructure
- Order flow
- ADX indicator for ranging markets

### Trading Implications

- Use market orders when execution certainty is prioritized over price control
- Use limit orders when price control matters more than immediate execution
- Trailing stops automatically adjust to lock in profits as price moves favorably
- Stop orders become market orders when triggered, exposing traders to slippage during gaps
- Stop-limit orders provide price control after trigger but risk non-execution in fast markets
- OCO orders allow simultaneous profit target and stop loss placement
- Range trading requires ADX below 25 and ideally trending downward
- Extended hours trading only accepts limit orders due to lower liquidity
- Peg orders help mimic market maker behavior by jumping to best bid/offer
- Dynamic stops based on ATR or moving averages can improve exit performance

### Risk Factors

- Market orders may execute at significantly different prices than last quoted in fast-moving or illiquid markets
- Stop orders can trigger during price gaps, resulting in execution far from stop price
- Stop-limit orders may not execute if price gaps through limit level
- Extended hours trading has lower liquidity, higher volatility, and wider spreads
- Hidden/iceberg orders receive lower execution priority
- Conditional orders face execution uncertainty based on trigger conditions
- Trailing stops may trigger prematurely on normal volatility without trend reversal
- GTC orders remain exposed to overnight news and gap risk
- Forex trading carries leverage-related margin call risk