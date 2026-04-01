# Current Context

## Active Milestone

**Name**: Alpha decay curve
**Goal**: Compute cumulative alpha at sub-holding-period checkpoints for each rebalance period, enabling mechanism-aware evaluation of screens.

## Current Phase

**Phase**: brainstorm
**Started**: 2026-04-01

## Key Decisions

<!-- None yet. -->

## Blockers

<!-- None. -->

## Plan Reference

<!-- Not yet planned. -->

## Milestone Rubric

| Dimension | Weight | 1-3 | 7-10 |
|-----------|--------|-----|------|
| acceptance_criteria | 4 | Missing decay computation or logging | Decay at all checkpoints, logged, surfaced in analysis |
| correctness | 4 | Alpha computed wrong or checkpoints misaligned | Correct per-period alpha relative to benchmark |
| test_coverage | 3 | No tests | Synthetic + real data tests for decay computation |
| code_quality | 3 | Monolithic, over 100 lines | Clean helpers, follows existing patterns |
| documentation | 1 | No docs | Clear output in analysis.md |
| performance | 1 | Slow | Runs in seconds |

## Notes

- Detail files in data/details/ contain per-rebalance stock picks with returns
- Need daily price data to compute sub-period returns (already in parquet cache)
- Alpha = screen portfolio return - SPY return over same period
