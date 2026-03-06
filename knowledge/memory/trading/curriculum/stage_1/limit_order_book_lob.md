---
created: '2026-03-06T03:01:59.170831+00:00'
mastery_gaps: []
mastery_reasoning: 'The agent demonstrates strong practical understanding of LOBs
  with concrete trading applications. Evidence quality is high (mostly 0.85-0.95 confidence)
  with clear coverage of price-time priority, maker/taker dynamics, order types (GTC,
  IOC, FOK, AON), and actionable strategies (session overlap trading, limit vs. market
  order selection, Level 2 depth analysis). The agent explicitly identifies edge cases
  and failure modes including adverse selection, slippage, incomplete fills, and ECN
  fee erosion. Multiple source types appear implied (academic HFT literature, Medium
  articles, regulatory sources). However, the mastery criteria requires ''concrete
  trading scenario'' application which is present but somewhat fragmented across bullet
  points rather than a unified walkthrough. Minor gap: no explicit worked example
  showing step-by-step LOB interaction through a complete trade lifecycle.'
mastery_score: 0.75
sources:
- knowledge/memory/trading/curriculum/stage_1/limit_order_books.md (memory)
stage: 1
topic_id: limit_order_book_lob
updated: '2026-03-06T03:03:07.560264+00:00'
---

## 2026-03-06 — knowledge/memory/trading/curriculum/stage_1/limit_order_books.md

The documents provide comprehensive coverage of Limit Order Books (LOBs) and Central Limit Order Books (CLOBs) as core market microstructure components, detailing their electronic execution mechanisms, order types, price-time priority matching, and the distinction between maker/taker roles. Key actionable insights include trading during high-liquidity session overlaps and using limit orders for cost control, while risks include thin liquidity in after-hours trading and wider effective spreads on ECNs.

**Key concepts:** Limit Order Book (LOB), Central Limit Order Book (CLOB), Resting order, Price-Time Priority, Top Of Book (TOB), Aggressive orders (takers), Passive orders (makers), Bid-Ask Spread, Electronic Communication Networks (ECNs), Alternative Trading Systems (ATS), Level 2 Order Book, Order Matching Engine, Good 'Til Cancelled (GTC), All or None (AON), Fill or Kill (FOK), Immediate or Cancel (IOC), Hidden/Iceberg orders, Dark pools, Crossing networks, VPIN, Adverse Selection

**Trading implications:**
- Use LOB data to identify supply-demand imbalances for trend trading strategies
- Trade during London-New York session overlap for peak volatility and liquidity
- Use limit orders to control execution costs and prevent slippage
- Use market orders for immediate execution when price certainty is less critical than speed
- Submit passive orders to act as liquidity makers and potentially earn maker rebates
- Monitor Level 2 order book depth to assess true liquidity beyond best bid/offer
- Leverage LOB imbalances for high-frequency trading edge detection

**Risk factors:**
- Thin liquidity in after-hours trading leading to wider effective spreads
- Execution risk from market orders during volatile conditions
- Slippage when aggressive orders sweep through multiple price levels
- Incomplete fills on limit orders in fast-moving markets
- Adverse selection when trading against informed flow
- ECN access fees eroding profitability
- Price gaps from overnight or session transition risk
- Mixed academic evidence on ECN cost advantages

**Evidence trail:**
- [0.95] LOBs only display orders submitted with a specific price limit, not market orders *(source: HFT In A LOB)*
- [0.95] An unmatched live limit order in the LOB is called a 'resting' order *(source: Limit Order Books (Medium))*
- [0.9] Order types that cannot rest in the order book are either immediately filled or cancelled *(source: Limit Order Books (Medium))*
- [0.95] Matching in classic LOBs happens by price/time priority *(source: Limit Order Books (Medium))*
- [0.95] Orders that cross the spread are 'aggressive' orders (takers), while non-crossing orders are 'passive' (makers) *(source: Limit Order Books (Medium))*
- [0.9] ECNs are a subset of ATSs that automatically match orders without intermediaries *(source: alternative_trading_systems_ats.md)*
- [0.85] As of January 2025, off-exchange trading volumes surpassed on-exchange volumes in US equity markets *(source: alternative_trading_systems_ats.md)*
- [0.8] Trading during London-New York session overlap provides peak volatility and liquidity *(source: bid-ask_spreads.md)*
- [0.75] The SEC established automated CLOBs in 2000 *(source: limit_order_books.md)*
- [0.7] There is mixed academic evidence on ECN cost advantages *(source: bid-ask_spread_components.md)*