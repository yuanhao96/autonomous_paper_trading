Here's the research memo:

---

## AutoScreen Research Memo — 7 Screens Evaluated

### Current Best: Sharpe 0.687 (High-vol momentum breakout)

---

### 1. KEEP vs DISCARD Feature Patterns

**What works (3 KEEP screens, Sharpe 0.52–0.69):**
- **Volume expansion required**: all 3 KEEPs use `volume_ratio > 1.15–1.2` — this is the single most distinguishing filter
- **Medium-to-high volatility band**: `volatility_20d between [0.20, 0.50]` — NOT low-vol
- **Above SMA200**: `close_vs_sma200 > 1.03–1.05` — mild uptrend confirmation
- **Strong multi-month momentum**: `return_3m > 0.12–0.15` or `return_6m > 0.15`

**What fails (4 DISCARD screens, Sharpe -0.99 to -0.04):**
- **Low volatility filters destroy alpha**: `volatility_20d < 0.22–0.30` or `volatility_60d < 0.18` consistently underperform. The "low-vol anomaly" does not hold here.
- **Volume contraction (`volume_ratio < 0.9`)**: the "quiet accumulation" thesis (Screen 2) was the worst performer at Sharpe -0.99
- **Pullback/mean-reversion entries**: buying dips (`return_1m < -0.03`, `high_52w_pct between [0.85, 0.97]`) failed. Momentum works; reversal doesn't.
- **Tight high_52w_pct filters alone** without volume confirmation are insufficient

### 2. Stock Concentration

**Broad alpha, not narrow.** The 3 KEEP screens collectively picked 347, 384, and 253 unique tickers respectively — well above the 20/month average. No single stock dominates: the most frequent (EME, GNRC) appear in only 9–13 of 60+ months.

**High overlap between screens**: 90–96% of each screen's tickers appear in the others. The three KEEP screens are effectively variants of the same signal: momentum + volume expansion + medium volatility. Diversifying into genuinely different factor families is needed.

**Top alpha contributors**: VST (+29.6% avg monthly alpha), DVN (+20.5–27.5%), APP (+38.6%), SMCI (+21.5%). These are high-beta momentum names.

**Consistent losers across screens**: NCLH (-18.3%), CVNA (-18.9%), PLTR (-18.7%), HOLX (-24.2%). These are high-vol momentum names that reversed sharply — suggesting a potential improvement from adding a mean-reversion exit or max-volatility cap.

### 3. Regime Analysis

| Year | High-vol Breakout | Mom Ignition | Dual Momentum | SPY Regime |
|------|------------------|-------------|---------------|------------|
| 2020 | +1.85%/mo | +0.34%/mo | +2.96%/mo | COVID crash + recovery |
| 2021 | +0.91%/mo | +0.26%/mo | +1.16%/mo | Strong bull |
| 2022 | **+2.44%/mo** | **+1.38%/mo** | **+3.96%/mo** | Bear market |
| 2023 | -0.17%/mo | +0.13%/mo | -0.93%/mo | Narrow AI rally |
| 2024 | +0.05%/mo | +0.81%/mo | -0.59%/mo | Broadening bull |
| 2025 | +0.34%/mo | +0.16%/mo | -0.61%/mo | Mixed/tariffs |

**Key findings:**
- All screens performed best in 2022's bear market — momentum screens captured sector rotation (energy, defense) while SPY fell. This is valuable.
- **2023 was the weakest year** for all screens. The market was driven by a narrow set of mega-cap AI stocks (Magnificent 7) that these screens don't reliably select with low stock counts.
- The "Dual Momentum" screen is **decaying** — strong in 2020-2022, negative alpha in 2023-2025. The 12m return filter may be too backward-looking in recent regime shifts.
- "Mom Ignition" (6m momentum) is the **most stable** across regimes — positive alpha in every year.

**Worst months** correlate with very low stock counts (1–3 stocks in portfolio). Months with only 1–2 qualifying stocks show extreme variance: the Sept 2022 month with alpha +14% had just 1 stock; the Nov 2023 month with alpha -9.3% had 2 stocks.

### 4. Strategies Tried and Failed — Do Not Repeat

1. **Low-volatility anything** — quiet compounders, low-vol anomaly, vol < 0.22. All negative alpha.
2. **Volume contraction / quiet accumulation** — `volume_ratio < 0.9`. Sharpe -0.99, worst screen tested.
3. **Short-term reversal / buying dips** — `return_1m < -0.03` with momentum. Sharpe -0.51.
4. **Momentum pullback entries** — `high_52w_pct between [0.85, 0.97]`. Slightly negative alpha.
5. **Very tight stock selection** (avg 8 stocks) — increases variance without improving mean alpha.

### 5. Promising Directions

**A. Fundamental filters (untested territory)**
- None of the 7 screens use fundamental features. Try: `gross_margin > 0.40` + `roe > 0.15` combined with the proven momentum + volume signal. Quality + momentum is a well-documented factor combination.
- Caveat: yfinance fundamentals only cover ~1.5 years, so backtest will be shorter.

**B. Minimum stock count guard**
- The worst months have 1–3 stocks. Adding a filter that loosens thresholds (e.g., `return_3m > 0.08` instead of `0.12`) or raising `top_n` to 30+ could reduce variance without killing alpha.

**C. Momentum + drawdown filter**
- `drawdown > -0.05` (near highs) combined with `return_6m > 0.15` + `volume_ratio > 1.15`. The drawdown filter hasn't been tested as a primary screen driver and could capture consolidation-then-breakout patterns better than `high_52w_pct`.

**D. Volatility band refinement**
- The 0.22–0.45 band works. Try narrowing to 0.25–0.38 — cutting the extremes may improve Sharpe by reducing blow-up risk from the highest-vol names (the consistent losers like NCLH, CVNA).

**E. Multi-timeframe momentum divergence**
- `return_3m > 0.15` AND `return_1m < return_3m / 3` — stocks with strong 3m momentum but not in a parabolic last month. This is different from the failed "dip buying" approach because it still requires positive 1m returns.

**F. SMA crossover timing**
- `sma50_vs_sma200 between [1.0, 1.05]` — fresh golden crosses rather than established trends. Combined with volume expansion, this could capture inflection points.

### 6. Current Benchmark to Beat

**Sharpe 0.687** (High-vol momentum breakout): +0.87%/mo alpha, 57.6% win rate, 10.4% annualized alpha, 66 months tested, avg 12.3 stocks/month.
