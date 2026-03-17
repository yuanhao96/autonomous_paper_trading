# Current Context

## Active Milestone

**Name**: Screen dedup and overlap detection
**Goal**: Detect when KEEP screens are near-duplicates (same core factors, slightly different thresholds) so the LLM avoids proposing more of the same.

## Current Phase

**Phase**: brainstorm
**Started**: 2026-03-17

## Key Decisions

- The system is producing KEEP screens at a healthy rate but many are variations of momentum + idio_vol + sector_contrarian
- Need overlap detection at the stock-pick level (Jaccard similarity), not just at the filter/score definition level

## Blockers

<!-- None. -->

## Plan Reference

<!-- Not yet planned. -->

## Milestone Rubric

| Dimension | Weight | 1-3 | 7-10 |
|-----------|--------|-----|------|
| acceptance_criteria | 4 | Missing overlap computation or clustering | All 5 criteria met |
| correctness | 4 | Jaccard computed wrong or clustering nonsensical | Correct overlap, meaningful clusters |
| test_coverage | 3 | No tests | Synthetic + real data tests for overlap |
| code_quality | 3 | Monolithic function, over 100 lines | Clean helpers, follows existing patterns |
| documentation | 1 | No docs | Overlap section clear in analysis.md |
| performance | 1 | Slow on large results.jsonl | Runs in seconds |

## Notes

- Stock details are archived in data/details/ as JSON per screen — these contain per-rebalance stock picks needed for Jaccard computation
- analyze.py already has a correlation section (--section correlation) that could be extended
- The overlap section in analyze.py already exists (--section overlap) — need to check what it currently does
