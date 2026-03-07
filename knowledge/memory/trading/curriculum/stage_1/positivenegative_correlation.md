---
created: '2026-03-07T03:05:10.467872+00:00'
mastery_gaps: []
mastery_reasoning: 'The agent demonstrates solid understanding of positive/negative
  correlation with concrete trading applications. The knowledge base includes: (1)
  clear definition of correlation coefficient (-1 to +1 scale with confidence 0.95),
  (2) specific threshold for ''strong'' correlation (±0.7 with confidence 0.85), (3)
  multiple concrete trading scenarios including oil-CAD correlation (long CAD when
  oil rises), hedging with negatively correlated pairs, and confirmation signals across
  related pairs (AUDUSD/NZDUSD, EURUSD/GBPUSD). The agent also identifies edge cases:
  correlation shifts between inflationary/deflationary environments, double risk exposure
  with positively correlated pairs, and accidental offsetting with negatively correlated
  pairs. Evidence quality is strong with multiple high-confidence sources (0.85-0.95
  range). However, the mastery criteria is not fully met because while the agent can
  describe applications, there''s no demonstrated walkthrough of a complete trading
  scenario with entry/exit logic, position sizing based on correlation strength, or
  dynamic adjustment when correlations break down. The content cuts off mid-sentence
  (''Three types of FX ri''), suggesting incomplete knowledge capture.'
mastery_score: 0.65
sources:
- knowledge/memory/trading/curriculum/stage_1/intermarket_analysis.md (memory)
stage: 1
topic_id: positivenegative_correlation
updated: '2026-03-07T03:05:20.325166+00:00'
---

## 2026-03-07 — knowledge/memory/trading/curriculum/stage_1/intermarket_analysis.md

Intermarket analysis examines correlations between four asset classes (stocks, bonds, commodities, currencies) to predict market movements, with forex markets serving as early warning signals. Currency diversification is emphasized as essential protection against government-induced inflation, while correlation relationships shift dynamically between inflationary and deflationary environments. The Canadian dollar demonstrates strong positive correlation with oil prices, creating actionable trading opportunities and hedging strategies.

**Key concepts:** Intermarket analysis, Asset class correlation, Currency diversification, Inflation hedge, Carry trade, Transaction risk, Translation risk, Economic risk, Risk reversal, Natural hedging, Correlation coefficient, Positive/negative correlation, Forex pair correlation, Oil-CAD correlation, Safe-haven currency

**Trading implications:**
- Maintain multi-currency exposure to hedge against government-induced inflation and debt devaluation
- Monitor forex markets as early warning signals for other asset classes
- Use correlation analysis to confirm trading signals across related pairs (e.g., AUDUSD/NZDUSD, EURUSD/GBPUSD)
- Implement hedging strategies using negatively correlated pairs to offset losses
- Trade oil-CAD correlation: long CAD when oil rises, short when oil falls
- Use risk reversals to gauge market positioning and directional bias
- Apply scaling-in strategy for currency exchanges to average out rates
- Monitor central bank tone/language rather than just rate decisions for directional bias
- Check cross-currency pairs (EUR/USD, CAD/JPY) to isolate USD vs CAD-specific moves

**Risk factors:**
- Correlation relationships shift based on inflationary versus deflationary environments requiring continuous monitoring
- Double risk exposure when trading positively correlated pairs simultaneously
- Accidental offsetting positions when trading negatively correlated pairs without awareness
- High volatility around major data releases (NFP, CPI, central bank announcements)
- Friday afternoon trap around U.S. Non-Farm Payrolls reports
- Alternative investments involve special risks: short sales, leveraging, adverse market forces, regulatory changes, illiquidity
- No correlation strategy guarantees returns in declining markets
- Past correlation performance does not guarantee future relationships
- Oil market disruptions can cause extreme CAD weakness independent of other factors

**Evidence trail:**
- [0.95] Intermarket analysis examines correlations between four major asset classes (stocks, bonds, commodities, currencies) to predict market movements *(source: intermarket_trading_strategies_2009_part_2.md)*
- [0.9] Currency diversification is essential protection against government-induced inflation *(source: intermarket_trading_strategies_2009_part_2.md)*
- [0.85] Forex markets provide early warning signals for other markets *(source: intermarket_analysis.md)*
- [0.9] Correlation relationships shift based on inflationary versus deflationary environments *(source: intermarket_analysis.md)*
- [0.95] Correlation coefficient ranges from -1 to +1, where -1 indicates perfect negative correlation and +1 indicates perfect positive correlation *(source: Asset Class Correlation Map - Guggenheim Investments)*
- [0.85] Correlation above +0.7 or below -0.7 is considered strong *(source: What Are Forex Pair Correlations and How to Trade on Them | FBS)*
- [0.9] Crude oil positively correlates with the Canadian dollar as Canada is the largest oil supplier to the US *(source: What Are Forex Pair Correlations and How to Trade on Them | FBS)*
- [0.85] Risk reversals near zero indicate no significant bias; positive numbers indicate call preference/upward expectation, negative indicates put preference/downward expectation *(source: day_trading_the_currency_market_-_technical_and_fu_part_10.md)*
- [0.9] Three types of FX risk exist: transaction, translation, and economic risk *(source: intermarket_analysis.md)*
- [0.8] USD/JPY longer-term risk reversals indicate strong market favoring of yen calls and dollar puts *(source: day_trading_the_currency_market_-_technical_and_fu_part_10.md)*

**Unresolved conflicts:**
- ⚠️ Correlation coefficient ranges from -1 to +1, where -1 indicates perfect negative correlation and +1 indicates perfect positive correlation ↔ Positive risk reversal numbers indicate calls are preferred over puts with market expecting upward movement
- ⚠️ Correlation coefficient ranges from -1 to +1, where -1 indicates perfect negative correlation and +1 indicates perfect positive correlation ↔ Negative risk reversal numbers indicate puts are preferred over calls with market expecting downward movement
- ⚠️ Positive risk reversal numbers indicate calls are preferred over puts with market expecting upward movement ↔ Negative risk reversal numbers indicate puts are preferred over calls with market expecting downward movement