# Current Context

## Active Milestone

**Name**: Regime computation and feature integration
**Goal**: Add compute_regime() function to screen.py that classifies each trading day into one of 4 regimes using SPY price data (trend x volatility). Integrate regime as a column in the feature DataFrame.

## Current Phase

**Phase**: brainstorm
**Started**: 2026-03-13

## Key Decisions

<!-- None yet. -->

## Blockers

<!-- None. -->

## Plan Reference

<!-- Not yet planned. -->

## Milestone Rubric

| Dimension | Weight | Target |
|-----------|--------|--------|
| acceptance_criteria | 4 | All 5 criteria met |
| correctness | 4 | Regime labels match expected classification |
| test_coverage | 3 | Synthetic price data tests, edge cases |
| code_quality | 3 | Functional style, follows existing patterns |
| documentation | 1 | Docstrings on new functions |
| performance | 1 | No measurable overhead |

## Notes

- SPY is already in prices.parquet
- Existing regime in analyze.py uses BULL/BEAR/FLAT from monthly SPY return — this replaces it with daily 2x2 grid
- compute_all_features() orchestrates all feature computation — regime gets added there
