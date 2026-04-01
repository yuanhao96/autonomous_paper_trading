# Current Context

## Active Milestone

**Name**: Alpha decay curve
**Goal**: Compute cumulative alpha at sub-holding-period checkpoints for each rebalance period to distinguish front-loaded vs gradual edges.

## Current Phase

**Phase**: execute
**Started**: 2026-04-01

## Key Decisions

- Compute decay inline in screen.py `_backtest_period()` — already has prices and date_range loaded
- Checkpoints: 5d, 10d only (filtered to those < holding_days; full period alpha already logged)
- Alpha at checkpoint = mean(stock_return_at_t) - spy_return_at_t for each rebalance period
- Add `alpha_decay` dict to each monthly_details entry (backward compatible — old results just lack the field)
- Aggregate decay profile in analyze.py as new `section_decay` section
- No changes to feature_stats.py in this milestone (quintile monotonicity is Milestone 9)

## Blockers

<!-- None. -->

## Plan Reference

### Steps

1. [x] Add alpha decay checkpoint computation to `_backtest_period()` in screen.py
2. [x] Add `section_decay` to analyze.py for KEEP screens
3. [x] Register section_decay in SECTIONS dict
4. [x] Add tests for alpha decay computation (9 tests: 4 synthetic + 1 e2e + 5 classify)
5. [x] Run ruff check + pytest (101 passed, 0 failed)
6. [ ] Update CLAUDE.md/program.md if needed

## Milestone Rubric

| Dimension | Weight | 1-3 | 7-10 |
|-----------|--------|-----|------|
| acceptance_criteria | 4 | Missing decay computation or logging | Decay at checkpoints, logged in results, surfaced in analysis |
| correctness | 4 | Alpha computed wrong or checkpoints misaligned | Correct per-period alpha relative to SPY |
| test_coverage | 3 | No tests | Synthetic tests for decay computation |
| code_quality | 3 | Monolithic, over 100 lines | Clean addition to existing functions |
| documentation | 1 | No docs | Clear output in analysis |
| performance | 1 | Slow | Runs in seconds |

## Notes

- date_range in _backtest_period is daily trading dates, so date_range[rebal_indices[i] + 5] gives the 5th trading day after rebalance
- Need to handle edge case where checkpoint index exceeds period length
- Each detail file has ~65 periods with ~20 stocks each
