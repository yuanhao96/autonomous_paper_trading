---
created: '2026-03-03T03:08:22.315486+00:00'
mastery_gaps: []
mastery_reasoning: 'The agent demonstrates solid conceptual understanding of earnings
  yield as E/P, its reciprocal relationship to P/E, and its primary use case for comparing
  equities to bond yields (Fed model). The evidence quality is strong (mostly 0.85-0.95
  confidence) with multiple source types (Wikipedia, internal docs). However, the
  mastery criteria requires demonstrating application in a ''concrete trading scenario,''
  which is not met. The ''Trading implications'' section mentions earnings yield only
  abstractly (''apply earnings yield for immediate comparison to prevailing long-term
  interest rates'') without walking through a specific decision: e.g., ''When 10-year
  Treasury yields 4.5% and Stock X has earnings yield of 3%, I would avoid/underweight
  because...'' or ''When earnings yield exceeds bond yield by X margin, this signals...''
  The agent identifies edge cases (Fed model disputed, risk profile assumptions) but
  lacks executable trading logic. Score starts at 0.5 (can explain), +0.05 for edge
  cases, +0.05 for multiple sources, -0.1 for unmet mastery criteria, -0.05 for no
  concrete scenario = 0.45 → adjusted to 0.55 recognizing strong conceptual foundation
  but clear application gap.'
mastery_score: 0.55
sources:
- knowledge/memory/trading/curriculum/stage_1/trailing_pe_ratio.md (memory)
stage: 1
topic_id: earnings_yield
updated: '2026-03-03T03:08:38.428321+00:00'
---

## 2026-03-03 — knowledge/memory/trading/curriculum/stage_1/trailing_pe_ratio.md

These documents synthesize fundamental valuation metrics—primarily P/E ratios (trailing, forward, absolute, and relative forms) and earnings yield—with technical analysis methodologies rooted in Dow Theory. Trailing P/E uses historical 12-month earnings for objective valuation of mature companies, while forward P/E incorporates analyst estimates for growth assessment. Earnings yield (E/P) serves as the reciprocal of P/E, enabling direct comparison to bond yields and aggregate market valuation via models like the Fed model.

**Key concepts:** Trailing P/E Ratio (TTM/LTM), Forward P/E Ratio, Earnings Per Share (EPS), Basic EPS, Diluted EPS, Earnings Yield (E/P), PEG Ratio, Absolute P/E, Relative P/E, Dow Theory, Trend Analysis, Support and Resistance, Breakouts, Market Breadth, Advance-Decline Line, Sentiment Analysis, Fed Model, Enterprise Value Adjusted Earnings Yield

**Trading implications:**
- Use trailing P/E for mature, stable companies with consistent earnings history; forward P/E for high-growth companies where future earnings matter more than past performance
- Apply earnings yield for immediate comparison to prevailing long-term interest rates and bond yields to assess relative attractiveness of equities
- Combine fundamental P/E-based valuation with technical trend identification, support/resistance levels, and breakouts for market timing
- Use adjusted earnings yield (EBITDA-based with enterprise value) to account for differing debt levels and tax rates when comparing companies
- Monitor market breadth and advance-decline lines alongside valuation metrics to confirm or contradict price trends

**Risk factors:**
- Forward P/E relies on analyst estimates which may be inaccurate or subject to revision
- Trailing P/E may not reflect current business conditions or future prospects for rapidly changing companies
- Earnings yield comparisons to bond yields assume similar risk profiles, which may not hold during market stress
- The Fed model for aggregate market valuation is disputed and may be misleading
- Technical analysis patterns and trend signals can generate false breakouts and whipsaws
- Market efficiency debates suggest neither fundamental nor technical analysis may consistently produce excess returns

**Evidence trail:**
- [0.9] Trailing P/E uses historical 12-month earnings for objective valuation of mature companies *(source: trailing_pe_ratio.md)*
- [0.9] Forward P/E incorporates analyst estimates for growth assessment *(source: trailing_pe_ratio.md)*
- [0.75] Wall Street generally prefers forward-looking metrics *(source: trailing_pe_ratio.md)*
- [0.95] Basic EPS is defined as net income minus preferred dividends divided by weighted average common shares outstanding *(source: earnings_per_share_eps.md)*
- [0.95] Earnings yield is the quotient of earnings per share divided by share price (E/P) *(source: Earnings yield - Wikipedia)*
- [0.95] Earnings yield is the reciprocal of the P/E ratio *(source: Earnings yield - Wikipedia)*
- [0.9] Earnings yield allows immediate comparison to prevailing long-term interest rates *(source: Earnings yield - Wikipedia)*
- [0.85] The Fed model uses earnings yield to assess aggregate stock market valuation levels *(source: Earnings yield - Wikipedia)*
- [0.85] The Fed model is disputed *(source: Earnings yield - Wikipedia)*
- [0.9] Greenblatt's adjusted earnings yield uses (EBITDA - CapEx) / Enterprise Value *(source: Earnings yield - Wikipedia)*