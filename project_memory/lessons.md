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
