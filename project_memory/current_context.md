# Current Context

## Active Milestone

**Name**: Implement Portfolio Allocation
**Goal**: Build the `allocate` command that converts composite alpha scores into portfolio weights with position limits.

## Current Phase

**Phase**: execute
**Started**: 2026-03-11

## Key Decisions

- [AUTO] Chose alpha-proportional weighting with caps over equal-weight (too simple) and MVO (too complex)
- [AUTO] Long-only portfolio, top-N stocks by composite alpha
- [AUTO] Position cap at 5% (configurable), remaining weight redistributed
- [AUTO] No sector constraints for now — keep simple, add in future milestone if needed

## Blockers

## Plan Reference

### Steps

1. [ ] Create `src/stratgen/allocator.py` — core allocation functions
2. [ ] Create `src/stratgen/factor_allocate.py` — command runner
3. [ ] Add `allocate` subcommand to `cli.py`
4. [ ] Add `RESULTS_ALLOCATE` path to `paths.py`
5. [ ] Create `tests/test_allocator.py`
6. [ ] Run `stratgen allocate` and verify output

## Notes

- Composite alpha scores available from score/validate pipeline
- Alpha-proportional: weight_i = max(alpha_i, 0) / sum(max(alpha_j, 0)) for j in top-N
- Position cap applied iteratively: excess weight redistributed to uncapped positions
