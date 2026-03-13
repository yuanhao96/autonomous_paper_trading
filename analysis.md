# AutoScreen Research Memo — 82 Screens Evaluated

## 1. What Works

**42-day holding period dominates.** 41/52 screens KEEP (78.8%), avg Sharpe 0.398 vs 21-day's 16/29 KEEP (55.2%), avg Sharpe 0.197. The single 10-day screen was discarded (Sharpe 0.225). Slower rebalancing consistently wins.

**Core momentum template.** The highest-Sharpe screens all share: `return_6m > 0.12`, `close_vs_sma200 > 1.03`, `drawdown > -0.07`, `volume_ratio > 1.1`. These four features appear in 9 of the top 10 screens.

**Feature keep rates (top performers):**
- `volume_ratio`: 77.5% KEEP, avg Sharpe with 0.411 vs 0.236 without — single most predictive filter
- `avg_volume_20d`: 83.9% KEEP, avg Sharpe 0.389 — liquidity gate works
- `return_6m`: 75.0% KEEP, avg Sharpe 0.373 vs 0.089 without
- `close_vs_sma50`: 73.1% KEEP, avg Sharpe 0.412
- `return_1m_vs_sector`: 74.2% KEEP, avg Sharpe 0.435

**Ranking matters.** `return_1m_vs_sector` as rank_by: 7/8 KEEP, avg Sharpe 0.590 — best rank feature. `return_6m` rank: 29/38 KEEP, avg Sharpe 0.370. `alpha` rank: 18/29 KEEP, avg Sharpe 0.233 — weakest viable rank.

**Sector-relative quality overlay lifts Sharpe dramatically.** The top 3 screens (Sharpe 1.855–1.995) all use `gross_margin_vs_sector > 1.0–1.05` and `roe_vs_sector > 1.0`, but only have 2–4 months of coverage — high signal, needs more data.

## 2. What Fails

**Volatility compression / mean-reversion strategies: 0% KEEP rate.** Six vol-compression screens tested (volatility_60d > X, volatility_20d < Y), all discarded. Sharpe range: -0.575 to +0.250. The "coiling spring" thesis is dead in this data.

**Short-term reversal (`return_1m < 0`):** Sharpe -0.508. Buying dips within uptrends does not work.

**Low-volatility anomaly:** "Low-vol trend leaders" Sharpe -0.075. `volatility_60d` has 14.3% KEEP rate, avg Sharpe -0.032.

**`sma50_vs_sma200` (golden cross):** 0/3 KEEP, avg Sharpe -0.347. Completely useless as a filter.

**`return_12m`:** 1/3 KEEP (33.3%), avg Sharpe -0.809. Long-lookback momentum hurts.

**`high_52w_pct`:** 2/6 KEEP (33.3%), avg Sharpe -0.003. Proximity to 52w high is not predictive.

**ROE as absolute filter:** The one screen with `roe > 0.15` hit Sharpe -2.923 (worst in dataset). Quality as absolute threshold is toxic; sector-relative quality (`roe_vs_sector`) works.

**Tight consolidation filters (`return_1m between [0.0, 0.05]`):** "Coiled momentum" Sharpe -0.478. Constraining near-term returns kills the signal.

## 3. Stock Concentration & Overlap

**High overlap:** 38.3% avg fraction of stocks appearing in >1 screen/month (max 80.8%). The 51 unique KEEP screens are not independent bets.

**Correlation clusters are extreme.** Within 21-day screens, most pairs correlate 0.65–0.97. Within 42-day screens, the core momentum cluster shows correlations 0.88–0.999 (effectively identical). The "Sector-relative momentum + SMA50 confirm" and "42d momentum + sector outperformance" screens correlate at 1.000.

**Low-correlation outliers exist:**
- "Vol compression breakout — was wild, now calm" correlates only 0.089–0.356 with the 21-day momentum cluster
- "Momentum + sector alpha + far from 52w low" correlates 0.244–0.558 with the 42-day cluster — genuinely different signal (Sharpe 0.966, 35 months coverage)

**Stock concentration:** 491 unique stocks, but STX (231 picks), GNRC (213), EME (211) dominate. Top alpha contributors are high-vol names: MRNA (+47.2%, n=13), TSLA (+37.0%, n=69, std 0.51), SMCI (+36.3%, n=53). These are lottery tickets — high mean, huge variance.

**Alpha destroyers to watch:** WBD (-36.9%, n=18), PSKY (-27.9%, n=41), J (-17.9%, n=8). These consistently destroy value when selected.

## 4. Regime / Temporal Patterns

**Alpha is regime-dependent and inconsistent:**

| Year | Mean Alpha | Win% |
|------|-----------|------|
| 2020 | +3.7% | 60.8% |
| 2021 | -1.0% | 38.4% |
| 2022 | +3.2% | 64.7% |
| 2023 | -1.7% | 42.5% |
| 2024 | +0.1% | 50.1% |
| 2025 | +3.7% | 58.3% |

**Odd/even year pattern:** 2020/2022/2024-25 positive, 2021/2023 negative. Momentum screens fail in narrow-leadership bull markets (2021 mega-cap, 2023 AI-only). This is the biggest risk — screens have ~40% win rate in bad regimes.

**Best screen decay is minimal:** "Stacked sector-relative momentum" first half mean alpha 5.1%, second half 3.7% — but only 4 months total, too few to judge decay.

## 5. Strategies Already Tried — Do Not Repeat

1. **Vol compression / coiling spring** (6 variants, all failed)
2. **Golden cross / `sma50_vs_sma200`** (3 variants, all failed)
3. **Short-term reversal / dip-buying** (failed)
4. **Absolute ROE filter** (catastrophic)
5. **Low-volatility anomaly** (failed)
6. **`high_52w_pct` as rank_by** (failed)
7. **`volatility_20d` as rank_by** (Sharpe -0.575)
8. **Biweekly (10-day) holding** (insufficient — only 1 test, but underperformed)
9. **`operating_margin_stability`** (Sharpe -0.151)
10. **`sector_breadth > 0.6`** (too restrictive, Sharpe 0.214)

## 6. Promising Directions

### A. Exploit the decorrelated "far from lows" signal
"Momentum + sector alpha + far from 52w low" has Sharpe 0.966 with 35 months coverage and low correlation (0.24–0.56) to the main cluster. Key filters: `low_52w_pct > 1.35`, `return_1m_vs_sector > 0.005`, `return_6m > 0.08`. Try variations:
- Tighten `low_52w_pct > 1.4` with `close_vs_sma50 > 1.0`
- Rank by `return_1m_vs_sector` instead of `return_6m` (rank avg Sharpe 0.590 vs 0.370)

### B. Sector-relative quality + momentum (more coverage needed)
Top 3 Sharpe screens (1.855–1.995) use `gross_margin_vs_sector` and `roe_vs_sector` but only have 2–4 months of data. Need relaxed thresholds to get more months:
- Try `gross_margin_vs_sector > 0.95` (lower bar) with `roe_vs_sector > 0.9`
- Combine with `return_1m_vs_sector` rank_by for the 0.590 avg Sharpe boost

### C. Rank_by `return_1m_vs_sector` is undertested
Only 8 screens use it, but 7/8 KEEP with avg Sharpe 0.590. Apply to the core momentum template with 42-day hold. This is the single highest-impact change available.

### D. Liquidity-gated variants
`avg_volume_20d > 50M` has 83.9% KEEP rate. Combine with the decorrelated "far from lows" template which currently lacks a liquidity gate.

### E. Exclude known alpha destroyers
Screens systematically pick WBD, PSKY, LYB, NEE — consider whether a sector or fundamental filter can exclude these. `gross_margin_vs_sector > 1.0` may naturally filter them.

## 7. Current Best to Beat

- **Sharpe 1.995** — "Stacked sector-relative momentum + margin quality, 42d" (4 months, 2.0 avg stocks — too few months and stocks to be reliable)
- **Realistic target: Sharpe > 0.966** — "Momentum + sector alpha + far from 52w low" (35 months, 19.7 avg stocks — statistically meaningful)
- **Robust floor: Sharpe > 0.818** — "Refined momentum + volume" (65 months, 11.2 avg stocks — longest-running high-Sharpe screen)

Any new screen should aim for Sharpe > 0.5 with >20 months coverage and >5 avg stocks to be considered a genuine improvement over the existing portfolio.
