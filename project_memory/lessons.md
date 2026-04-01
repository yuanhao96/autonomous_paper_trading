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

## Milestone: Documentation and integration (2026-03-13)

### What Worked
- Updating docs after solid implementation is straightforward — no design decisions needed
- The autonomous loop (run.py -n 3) immediately used new _pctrank and composite features
- analyze.py changes were minimal (uses_score column + summary line)

### What Didn't Work
- Nothing significant — this was the simplest milestone

### Patterns to Reuse
- Save documentation milestones for last — they go fast when implementation is stable
- Include LLM prompt updates (run.py) alongside documentation — the LLM needs to know about new features to use them

### Patterns to Avoid
- Don't skip the integration test (run.py -n 3) — it validates the full pipeline end-to-end

## Milestone: Regime awareness + OOS discipline (2026-03-14)

### What Worked
- Brainstorming the design before implementation (2x2 grid, Option C split) made implementation smooth
- Broadcasting regime to all tickers in the feature DataFrame was simple and future-proof
- Adding split_date as optional parameter preserved backward compatibility cleanly
- Keeping regime diagnostic-only (not filterable) kept scope tight
- Fallback in analyze.py (BULL/BEAR/FLAT for old data, 4-label for new) avoids migration

### What Didn't Work
- Synthetic test for MultiIndex prices DataFrame construction required debugging (nested DataFrame constructor doesn't work, need explicit MultiIndex)
- Adding market_regime broke existing pctrank test (32 vs 33 features) — needed to exclude non-numeric feature

### Patterns to Reuse
- When adding a new feature type to the DataFrame, check downstream consumers (pctrank, filters, tests)
- Optional parameters with None default + conditional result fields = clean backward compatibility
- Helper functions (_compute_sharpe, _compute_split_metrics, _compute_regime_stats) keep apply_screen under line limit

### Patterns to Avoid
- Don't assume pd.DataFrame constructor handles nested DataFrames — use explicit MultiIndex
- When adding categorical features, exclude them from numeric-only operations (pctrank)

## Milestone: Alpha decay curve (2026-04-01)

### What Worked
- Computing decay inline in _backtest_period was clean — entry_prices dict already available, just needed intermediate date lookups
- Backward compatibility via conditional alpha_decay field (only present when non-empty)
- Reviewer agent caught that 21d checkpoint was missing from ALPHA_DECAY_CHECKPOINTS despite being in acceptance criteria

### What Didn't Work
- Initially forgot that monthly_details gets split into slim (no stocks) and stock_details (with stocks) — alpha_decay needs to go in the slim version since it's diagnostic, not per-stock data

### Patterns to Reuse
- When adding per-period diagnostic data, include it in monthly_details (not stock_details) since it's screen-level, not stock-level
- Use conditional dict unpacking (`**({"key": val} if cond else {})`) for backward-compatible fields

### Patterns to Avoid
- Don't assume all intermediate data ends up in the final result dict — trace the data flow through the slim/archive split
