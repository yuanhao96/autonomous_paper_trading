# Current Context

## Active Milestone

**Name**: Composite scoring DSL
**Goal**: Add `score` field to screen DSL for weighted multi-factor composite ranking

## Current Phase

**Phase**: plan
**Started**: 2026-03-13

## Key Decisions

- [AUTO] Compute composite score in `_rank_and_select()` when `rank_by == "_score"`. Score is per-screen (not pre-computable), so it's computed on-the-fly from the `score` field in the screen definition.
- [AUTO] Score = weighted sum of feature values for each passing ticker. Negative weights invert the feature. No normalization — users should use `_pctrank` features for comparable scales.
- [AUTO] Missing features or NaN values → stock gets NaN score → excluded from ranking (same behavior as current rank_by).
- [AUTO] The `score` field is a list of `{"feature": str, "weight": float}` dicts.
- [AUTO] Filters still apply first. Score only affects ranking of survivors.
- [AUTO] Store the `score` definition in the result JSON for reproducibility.

## Blockers

<!-- None. -->

## Plan Reference

### Steps

1. [ ] Add `_compute_composite_score()` helper in screen.py
2. [ ] Modify `_rank_and_select()` to handle `rank_by: "_score"`
3. [ ] Include `score` field in result dict from `apply_screen()`
4. [ ] Add tests: basic scoring, negative weights, missing features, backward compat
5. [ ] Run all tests + ruff check

## Milestone Rubric

| Dimension | Weight | Target |
|-----------|--------|--------|
| acceptance_criteria | 4 | All 6 criteria met |
| correctness | 4 | Tests pass, score computed correctly |
| test_coverage | 2 | Composite scoring + edge cases |
| code_quality | 3 | Minimal changes, follows existing patterns |
| documentation | 1 | Docstrings on new functions |
| performance | 1 | No measurable overhead |

## Notes

- The `_rank_and_select()` function is the natural insertion point — it already handles `rank_by`
- A new helper `_compute_composite_score()` keeps the function under 100 lines
- The `score` field format matches goal.md spec exactly
- pctrank features make composite scores meaningful (all components on 0-1 scale)

## Score Cards

### Round 1 (2026-03-13)

| Dimension | Weight | Score | Evidence | Delta |
|-----------|--------|-------|----------|-------|
| acceptance_criteria | 4 | 9 | 5/5 criteria verified: weighted sum, negative weights, _score ranking, backward compat, 4 tests | - |
| correctness | 4 | 9 | 10/10 tests pass, synthetic tests verify exact arithmetic, real data end-to-end works | - |
| test_coverage | 2 | 9 | 4 new tests covering: basic scoring, negative weights, missing features, end-to-end | - |
| code_quality | 3 | 9 | 30-line helper + 10-line modification to existing function, follows existing patterns, ruff clean | - |
| documentation | 1 | 7 | Full docstring on _compute_composite_score, clear param docs | - |
| performance | 1 | 9 | Score computed only for passing tickers (not full universe), negligible overhead | - |

**Weighted average**: 8.9 / 10 (threshold: 7.0) - PASS
