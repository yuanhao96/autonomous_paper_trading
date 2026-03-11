# Fix Composite Alpha Signal Quality

## Problem

The composite alpha (IC-weighted z-score combination of 48 factors) produces a reversed signal:
- Mean IC = -0.0092 (negative across all horizons)
- Q1 (bottom) outperforms Q5 (top) by 14.8% annualized
- 36/48 factors have negative IC; magnitudes are tiny (max |IC| = 0.016)
- IC-weighting with noisy near-zero ICs amplifies noise

## Root Cause

1. **Noise amplification**: Weighting by raw IC magnitude when |IC| < 0.02 means weights are dominated by noise
2. **No IC threshold**: All 48 factors contribute equally regardless of signal strength
3. **Stale optimization**: Factors were optimized on SPY 2020-2023; cross-sectional IC on SP500 2018-2025 may differ

## Solution

### 1. Add IC threshold filter (`min_ic`)
- In `composite_alpha()`, skip factors whose trailing rolling |IC| is below `min_ic`
- Default: 0.005 (very permissive — just removes pure noise)

### 2. Add weight method options (`weight_method`)
- `"ic"` (current): weight = lagged rolling IC (preserves sign + magnitude)
- `"sign"`: weight = sign(lagged rolling IC) — equal contribution, IC direction only
- `"icir"`: weight = rolling IC / rolling IC std — more stable signal-to-noise weighting
- Default: `"sign"` — simplest, most noise-resistant

### 3. CLI integration
- `--weight-method {ic,sign,icir}` flag on `score` and `validate` commands
- `--min-ic FLOAT` flag on `score` and `validate` commands

## Steps

1. Modify `scorer.py::composite_alpha()` to accept `min_ic` and `weight_method` params
2. Implement sign and ICIR weighting logic
3. Add `--weight-method` and `--min-ic` CLI flags in `cli.py`
4. Pass new params through `factor_score.py::run_score()` and `factor_validate.py::run_validate()`
5. Run `stratgen validate` with new defaults and verify improvement
6. Update tests in `tests/test_scorer.py`

## Acceptance Criteria

- [ ] Composite alpha validation verdict is WEAK or STRONG (not NONE)
- [ ] Quintile spread is positive (top quintile outperforms bottom)
- [ ] Mean |IC| >= 0.02 across the evaluation period
- [ ] At least 2 forward horizons (of 1,5,10,20 days) show positive IC
