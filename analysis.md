# AutoScreen Research Analysis

*Computed from 20 screen evaluations, 2020-2025 monthly backtest*

## 1. Summary

- **20 screens tested**: 14 KEEP (Sharpe >= 0.3), 6 DISCARD
- **Best Sharpe**: 0.818 ("Refined momentum + volume — tighter vol band, drawdown guard")
- **Best annual alpha**: 13.3% | **Best win rate**: 61.5%
- **Heavy duplication**: Only 8 unique filter sets among 14 KEEP screens (many are identical)

## 2. What Works: The Winning Template

**Every single KEEP screen uses volatility_20d (14/14) and volume_ratio (14/14).** The top 7 screens all use the same 5-filter template:

| Feature | Typical threshold | Effect |
|---------|------------------|--------|
| `return_6m` | > 0.12 to 0.15 | Medium-term momentum |
| `volume_ratio` | > 1.15 to 1.20 | Rising volume (breakout signal) |
| `close_vs_sma200` | > 1.03 to 1.05 | Confirmed uptrend |
| `volatility_20d` | between [0.22, 0.38] | Not too calm, not too wild |
| `drawdown` | > -0.05 to -0.07 | Near highs, limited pullback |

**Key insight**: The core alpha comes from *momentum + volume confirmation + controlled volatility*. Stocks in an uptrend, with rising volume, and moderate (not low!) volatility.

### Threshold sensitivity
- `return_6m > 0.12` (Sharpe 0.818) slightly beats `> 0.15` (Sharpe 0.728-0.760) — looser threshold catches more stocks
- `volatility_20d between [0.25, 0.38]` (best) slightly beats `[0.22, 0.38]` and `[0.22, 0.4]` — tighter band helps
- `drawdown > -0.07` (best) slightly beats `> -0.05` — slightly more lenient drawdown tolerance helps

## 3. What Fails (Avoid These)

| Strategy | Sharpe | Why it fails |
|----------|--------|-------------|
| Low volatility screens (`vol_20d < 0.22` or `< 0.30`) | -0.99 to -0.04 | Low-vol stocks are crowded / already priced in |
| Short-term reversal (`return_1m < -0.03`) | -0.51 | Mean reversion doesn't work in this universe |
| `sma50_vs_sma200` (golden cross) | -0.35 avg | Cross signals are lagging, no alpha |
| `high_52w_pct` as primary filter | -0.13 avg | Near-highs alone doesn't distinguish |
| `return_1m` as filter (any direction) | All DISCARD | 1-month momentum is noise |
| Constraining `return_1m` to narrow band | -0.48 | "Coiled momentum" theory didn't work |
| 6-filter screens | Only DISCARD | Over-fitting — too many constraints |

**Critical pattern**: Screens that select for *low* volatility consistently lose money. The alpha is in the *moderate-to-high* volatility band (0.22-0.38).

## 4. Stock Concentration & Overlap

- **446 unique stocks** appeared across KEEP screens
- **57.8% of stocks per month appear in multiple KEEP screens** — very high overlap (screens are variants of the same idea)
- Top picks by frequency: EME (123), ARES (109), META (99), DECK (97), MOH (97)

### Best alpha contributors (min 5 appearances)
| Ticker | Mean Return | Appearances |
|--------|------------|-------------|
| WSM | +26.3% | 17 |
| NUE | +22.1% | 19 |
| VST | +19.8% | 26 |
| SMCI | +18.6% | 16 |
| GEV | +17.1% | 28 |
| STX | +11.2% | 73 |
| TRGP | +10.8% | 46 |
| EME | +5.2% | 123 |

### Worst alpha contributors (frequent picks that hurt)
| Ticker | Mean Return | Appearances |
|--------|------------|-------------|
| NCLH | -20.6% | 6 |
| CVNA | -18.5% | 15 |
| PLTR | -18.2% | 14 |
| MGM | -13.1% | 14 |
| MRK | -10.8% | 26 |
| EPAM | -9.8% | 32 |
| DXCM | -8.2% | 32 |

## 5. Regime & Temporal Patterns

### Alpha by year (KEEP screens only)
| Year | Mean Alpha | Win% | Assessment |
|------|-----------|------|-----------|
| 2020 | +1.91% | 64.7% | Strong — post-COVID recovery favors momentum |
| 2021 | +0.25% | 46.7% | Weak — low-vol bull market, momentum crowded |
| 2022 | +2.50% | 66.2% | **Strongest** — volatile bear, screen picks survivors |
| 2023 | +0.27% | 58.4% | Weak — narrow mega-cap rally, breadth limited |
| 2024 | -0.53% | 50.0% | **Negative** — alpha decayed |
| 2025 | +1.57% | 57.4% | Recovering |

**Concerning**: Alpha decay in 2023-2024. Best screen's first-half mean alpha is 1.80% vs 0.44% in second half. Could indicate crowding or regime shift.

### Best screen per-year detail
| Year | Mean Alpha | Win% |
|------|-----------|------|
| 2020 | +2.22% | 72.7% |
| 2021 | +0.28% | 58.3% |
| 2022 | +2.26% | 72.7% |
| 2023 | -0.28% | 45.5% |
| 2024 | +0.14% | 54.5% |
| 2025 | +2.32% | 66.7% |

## 6. Alpha Correlation Between Screens

All KEEP screens are **highly correlated** (0.61 to 1.00 pairwise alpha correlation). Several pairs are effectively identical (0.96-1.00). This means:
- **No diversification** across current screens
- All capture the same factor: *momentum + volume + moderate volatility*
- To find genuinely new alpha, need **different factor families**

## 7. Promising Directions to Explore

### A. Differentiated strategies (low correlation to current winner)
1. **Fundamental-only screens**: gross_margin, roe, debt_to_equity — completely untested in KEEP screens. Limited backtest (1.5yr) but could find orthogonal alpha.
2. **Value + momentum combo**: Low `return_12m` + high `return_3m` — losers starting to recover.
3. **Vol compression ratio**: `volatility_20d` much lower than `volatility_60d` as a breakout-pending signal.

### B. Refinements to current winner
4. **Tighten the vol band**: Try `[0.25, 0.35]` — narrowing top end from 0.38.
5. **Loosen momentum**: Try `return_6m > 0.08` or `> 0.10` — catches more stocks, may diversify.
6. **Add `avg_volume_20d`**: Untested. Filtering for liquid stocks could remove noisy picks.
7. **Replace `drawdown` with `high_52w_pct > 0.93`**: Different proximity-to-highs measure.

### C. Anti-patterns to try
8. **Cap recent runup**: `return_1m < 0.15` — avoid parabolic short-term moves that mean-revert. (Different from failed `return_1m < -0.03` which was buying dips.)

## 8. Current Benchmark to Beat

| Metric | Value |
|--------|-------|
| Best Sharpe | **0.818** |
| Best annual alpha | **13.3%** |
| Best win rate | **61.5%** |

The best screen's filters:
```json
{
  "return_6m": "> 0.12",
  "volume_ratio": "> 1.15",
  "close_vs_sma200": "> 1.03",
  "volatility_20d": "between [0.25, 0.38]",
  "drawdown": "> -0.07"
}
```

**Priority**: Find screens with alpha correlation < 0.5 to the current winner — even if lower Sharpe, uncorrelated alpha is more valuable than another variant of the same momentum screen.
