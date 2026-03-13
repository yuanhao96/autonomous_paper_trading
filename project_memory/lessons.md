# Lessons Learned

## Milestone: Percentile rank features (2026-03-13)

### What Worked
- `df.rank(axis=1, pct=True)` is the entire implementation — 14 lines total
- Synthetic test with known values caught the design right immediately
- Computing pctrank as post-processing on the full feature matrix is clean and simple

### What Didn't Work
- Branch setup was messy — milestone branch created off main which doesn't have screen.py (it's on structured). Had to merge structured in with conflicts.

### Patterns to Reuse
- For cross-sectional features, compute after all raw features are assembled
- Synthetic tests with hand-verifiable values are fast to write and catch real bugs

### Patterns to Avoid
- Don't create milestone branches off main when the working code is on a different branch

## Milestone: Composite scoring DSL (2026-03-13)

### What Worked
- Inserting score computation into existing `_rank_and_select()` was clean — only 10 lines changed
- Separate helper function keeps both functions under 100 lines
- Synthetic tests with exact arithmetic catch bugs immediately

### What Didn't Work
- Initial docstring was inaccurate (said NaN for missing features, but actually skips them). Reviewer caught it.

### Patterns to Reuse
- When extending DSL, add a helper function rather than bloating existing functions
- Always include the new field in the result dict for reproducibility

### Patterns to Avoid
- Don't write docstrings that describe intended behavior rather than actual behavior
