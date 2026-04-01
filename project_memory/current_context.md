# Current Context

## Active Milestone

**Name**: Screen dedup and overlap detection
**Goal**: Detect near-duplicate KEEP screens via pairwise Jaccard similarity and cluster them.

## Current Phase

**Phase**: execute
**Started**: 2026-03-17

## Key Decisions

- Approach A chosen: enhance existing section_overlap in analyze.py
- Jaccard on stock picks per rebalance date, averaged across common dates
- Union-find clustering with threshold > 0.5
- No new files or dependencies
- LLM gets cluster info via analysis.md (already read by run.py)

## Blockers

<!-- None. -->

## Plan Reference

### Steps

1. [ ] Add pairwise Jaccard computation to analyze.py (helper function)
2. [ ] Add union-find clustering helper
3. [ ] Rewrite section_overlap to show pairwise matrix + clusters
4. [ ] Verify analysis.md output includes cluster info (via LLM interpretation)
5. [ ] Add tests for Jaccard and clustering
6. [ ] Run ruff check + pytest

## Milestone Rubric

| Dimension | Weight | 1-3 | 7-10 |
|-----------|--------|-----|------|
| acceptance_criteria | 4 | Missing Jaccard or clustering | Pairwise Jaccard + clusters + LLM integration |
| correctness | 4 | Jaccard wrong or clusters nonsensical | Correct overlap, meaningful clusters |
| test_coverage | 3 | No tests | Synthetic tests for Jaccard + clustering |
| code_quality | 3 | Monolithic, over 100 lines | Clean helpers, follows existing patterns |
| documentation | 1 | No docs | Clear output format |
| performance | 1 | Slow | Runs in seconds |

## Notes

- Detail files in data/details/ are indexed by result index (0.json, 1.json, ...)
- Each detail file is a list of {month, stocks: {ticker: return}}
- 68 detail files currently exist
