# Current Context

## Active Milestone

**Name**: Implement Portfolio Allocation
**Goal**: Build the `allocate` command that converts composite alpha scores into portfolio weights with position limits and basic risk constraints.

## Current Phase

**Phase**: brainstorm
**Started**: 2026-03-11

## Key Decisions

## Blockers

## Plan Reference

### Steps

## Notes

- Composite alpha is validated (WEAK verdict, IC=0.016, monotonicity=1.0)
- Best settings: weight_method=global_sign, min_ic=0.01
- 5 active factors after filtering, 478 screened stocks
- Top stocks by composite alpha: LW, AZO, LEN (from previous score run)
