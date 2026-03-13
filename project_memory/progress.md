# Project Progress

## Goal Summary

Upgrade the AutoScreen DSL from absolute-threshold filtering to relative factor ranking by adding cross-sectional percentile ranks (`_pctrank` features) and composite scoring (`score` DSL field). This makes the autonomous loop capable of expressing canonical multi-factor strategies (value, quality, momentum, low-vol) the way professional quants think — in relative terms.

## Completed Milestones

### Milestone: Percentile rank features
- **Status**: completed
- **Date completed**: 2026-03-13
- **Summary**: Added `_pctrank` variants for all 32 numeric features, computed cross-sectionally per date using `df.rank(axis=1, pct=True)`.
- **Acceptance criteria met**:
  - [x] `compute_all_features()` returns `_pctrank` variants for all numeric features
  - [x] Percentile ranks are cross-sectional (computed per date across all tickers, no look-ahead)
  - [x] Filters using `_pctrank` features work in `apply_screen()`
  - [x] Existing screens without `_pctrank` produce identical results (backward compat)
  - [x] Tests cover percentile rank computation and filtering (3 new tests)
- **Final score**: 8.6 / 10

### Milestone: Composite scoring DSL
- **Status**: completed
- **Date completed**: 2026-03-13
- **Summary**: Added `score` DSL field for weighted composite ranking with `rank_by: "_score"` support. 4 new tests.
- **Acceptance criteria met**:
  - [x] `score` field computes weighted sum of features per stock
  - [x] Negative weights invert the feature
  - [x] `rank_by: "_score"` ranks stocks by composite score
  - [x] Screens without `score` work identically (backward compat)
  - [x] Tests cover composite scoring computation and ranking (4 new tests)
- **Final score**: 8.9 / 10

## Current Milestone

### Milestone: Documentation and integration
- **Status**: in-progress
- **Acceptance criteria**:
  - [ ] `program.md` documents `_pctrank` features and `score` DSL field
  - [ ] `analyze.py` handles screens with composite scoring
  - [ ] `run.py` LLM prompt mentions new features
  - [ ] `conda run -n data_science python run.py -n 3` completes 3 iterations
  - [ ] All tests pass, ruff clean
- **Phase**: brainstorm

## Upcoming Milestones

<!-- None — this is the final milestone. -->
