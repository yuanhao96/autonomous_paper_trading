---
created: '2026-02-26T07:15:22.817912+00:00'
mastery_gaps: []
mastery_reasoning: The agent demonstrates solid understanding of session overlaps,
  particularly the London-New York overlap as the peak volatility/liquidity window.
  It successfully applies this knowledge to concrete trading scenarios with specific
  strategy recommendations (scalpers focus on London-NY overlap, day traders target
  London session, etc.). The evidence quality is strong with multiple high-confidence
  citations (0.85-0.95) from diverse sources including curriculum materials and external
  references. The agent identifies edge cases (DST shifts, major holidays, weekend
  gap risk) and failure modes (thin liquidity in after-hours, slippage during news
  events). However, the mastery criteria is only partially met because while the agent
  explains overlaps well and provides strategy applications, it doesn't walk through
  a single cohesive concrete scenario showing decision-making in real-time. The trading
  implications are presented as bullet points rather than an integrated narrative.
  No unsupported assertions (<0.5 confidence) or contradictions were found. Multiple
  source types are cited (curriculum docs, Babypips, trading books).
mastery_score: 0.75
sources:
- knowledge/memory/trading/curriculum/stage_1/market_hours.md (memory)
stage: 1
topic_id: session_overlaps
updated: '2026-02-26T07:15:28.002941+00:00'
---

## 2026-02-26 — knowledge/memory/trading/curriculum/stage_1/market_hours.md

The documents synthesize global forex and equity market hours, emphasizing that session overlaps—particularly London-New York—generate peak volatility and liquidity. ECNs enable after-hours trading but carry liquidity risks, while proper timing of trades based on session characteristics is critical for strategy selection and risk management.

**Key concepts:** Trading sessions (Sydney, Tokyo, London, New York), Session overlaps (London-New York, Tokyo-London, Sydney-Tokyo), ECNs (Electronic Communication Networks), Liquidity and volatility patterns, After-hours/pre-market trading, Daylight Saving Time shifts, Bid-ask spreads, Foreign exchange risk types (transaction, translation, economic), Currency diversification, Weekend gap risk

**Trading implications:**
- Trade during London-New York overlap for peak volatility and liquidity
- Use limit orders rather than market orders in after-hours/ECN trading
- Scalpers should focus on London-NY overlap and NY open; avoid Sydney and late NY sessions
- Day traders should target London session and NY morning; avoid Tokyo lunchtimes
- Swing traders find best setups during late NY and Sydney sessions
- News traders should focus on 8:30 AM EST for US data releases
- Close positions by 4:00 PM EST Friday to avoid weekend gap risk
- Reduce position sizes during session overlaps to manage heightened volatility risk

**Risk factors:**
- Thin liquidity and wide spreads in after-hours/ECN trading
- Weekend gap risk from open positions held through market close
- Erratic price spikes during major holidays with 70% liquidity reduction
- Slippage during high-volatility news events (NFP, CPI)
- DST shift confusion causing missed opportunities
- Adverse selection costs in ECN trading
- Economic event volatility 5-10x average during news releases
- Limited order types and access fees in ECN/after-hours trading

**Evidence trail:**
- [0.95] London-New York session overlap generates peak volatility and liquidity *(source: knowledge/memory/trading/curriculum/stage_1/market_hours.md)*
- [0.95] Forex market operates 24 hours a day, 5 days a week *(source: Forex Market Trading Sessions: Hours, Zones & When to Trade)*
- [0.9] ECNs enable direct trading without intermediaries and facilitate after-hours trading *(source: knowledge/memory/trading/curriculum/stage_1/ecns_electronic_communication_networks.md)*
- [0.9] After-hours trading carries risks of thin liquidity, wide spreads, and limited order types *(source: knowledge/memory/trading/curriculum/stage_1/after-hourspre-market_trading.md)*
- [0.85] London session provides the most movement (pips) for major currency pairs *(source: Forex Trading Sessions - Babypips.com)*
- [0.8] Major holidays reduce liquidity by approximately 70% *(source: Forex Market Trading Sessions: Hours, Zones & When to Trade)*
- [0.8] News events like NFP and CPI cause 5-10x average volatility *(source: Forex Market Trading Sessions: Hours, Zones & When to Trade)*
- [0.85] United Kingdom captures 31% of total FX volume, making London open exceptionally important *(source: knowledge/memory/trading/discovered/day_trading_the_currency_market_-_technical_and_fu_part_7.md)*
- [0.85] European trading as a whole accounts for 42% of total FX trading *(source: knowledge/memory/trading/discovered/day_trading_the_currency_market_-_technical_and_fu_part_7.md)*
- [0.85] United States accounts for approximately 19% of total FX turnover *(source: knowledge/memory/trading/discovered/day_trading_the_currency_market_-_technical_and_fu_part_7.md)*