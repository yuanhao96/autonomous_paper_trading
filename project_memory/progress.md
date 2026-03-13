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

## Current Milestone

### Milestone: Composite scoring DSL
- **Status**: in-progress
- **Acceptance criteria**:
  - [ ] `score` field in screen DSL computes weighted sum of features per stock
  - [ ] Negative weights invert the feature (lower = better)
  - [ ] `rank_by: "_score"` ranks stocks by composite score
  - [ ] Screens without `score` work identically (backward compat)
  - [ ] Tests cover composite scoring computation and ranking
- **Phase**: brainstorm

## Upcoming Milestones

### Milestone: Documentation and integration
- **Priority**: medium
- **Depends on**: Composite scoring DSL
- **Rough scope**: Update `program.md` with new features/syntax, update `analyze.py` for composite screens, run 3 autonomous iterations to validate end-to-end
