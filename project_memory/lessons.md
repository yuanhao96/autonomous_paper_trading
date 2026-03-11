# Lessons Learned

## Milestone: Fix Composite Alpha Signal Quality (2026-03-11)

### What Worked
- global_sign weighting (using overall mean IC direction instead of rolling IC) eliminated noise from day-to-day IC sign flips
- Increasing min_ic from 0.005 to 0.01 filtered 43/48 factors, concentrating signal from the 5 strongest
- Perfect monotonicity (1.00) achieved with just 5 factors — less is more for noisy factor combinations

### What Didn't Work
- Rolling IC-based sign weighting ("sign" method) — rolling IC at 60-day window flips sign randomly, destroying the signal
- IC-magnitude weighting ("ic" method) — near-zero ICs amplify noise
- PASS-only factors made things worse — the PASS criteria was based on SPY time-series, not cross-sectional quality

### Patterns to Reuse
- Global (full-period) IC as factor direction indicator is more stable than rolling IC for factor weighting
- min_ic threshold should be set at 0.01+ to filter noise factors
- When combining many weak factors, fewer + stronger beats many + weak

### Patterns to Avoid
- Don't use rolling IC estimates as weights when individual factor ICs are < 0.02 — noise dominates
- Don't assume SPY time-series factor quality (PASS/MARGINAL) transfers to cross-sectional SP500 quality
