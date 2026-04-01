# Project Progress

## Goal Summary

Evolve AutoScreen from "does this screen make money?" to "does this screen make money for the reason I think it does?" by adding mechanism-aware diagnostics: alpha decay curves, quintile monotonicity, mechanism fields in the DSL, and mechanism diagnostics in backtest output.

## Completed Milestones

### Milestone 1: Regime computation and feature integration
- **Status**: completed
- **Date completed**: 2026-03-14
- **Summary**: Added compute_regime() to screen.py — 2x2 grid (trend x vol) from SPY data. Regime broadcast to all tickers in feature DataFrame.
- **Final score**: 9.0 / 10

### Milestone 2: Walk-forward OOS evaluation
- **Status**: completed
- **Date completed**: 2026-03-16
- **Summary**: Replaced single IS/OOS split with rolling walk-forward windows (18mo train / 6mo test). Multiple OOS observations produce robust Sharpe estimates. Walk-forward is now the default mode.
- **Final score**: N/A (completed outside project-finisher)

### Milestone 3: Feature enrichment + extended history
- **Status**: completed
- **Date completed**: 2026-03-16
- **Summary**: Added return_1w, return_12m_skip_1m, idio_vol, volume_change_20d, value features (earnings_yield, book_to_price, fcf_yield, market_cap), growth features (revenue_growth_qoq, margin_expansion). Extended data to 2014.
- **Final score**: N/A (completed outside project-finisher)

### Milestone 4: Score-first DSL + documentation
- **Status**: completed
- **Date completed**: 2026-03-16
- **Summary**: Composite scoring with rank_by=_score replaces hard AND-filters as primary mechanism. program.md and CLAUDE.md updated with all new features and walk-forward docs.
- **Final score**: N/A (completed outside project-finisher)

### Milestone 5: Screen dedup and overlap detection
- **Status**: completed
- **Date completed**: 2026-03-17
- **Summary**: Added pairwise Jaccard overlap and union-find clustering to analyze.py section_overlap. KEEP screens are clustered by stock-pick similarity.
- **Final score**: N/A (completed outside project-finisher)

### Milestone 8: Alpha decay curve
- **Status**: completed
- **Date completed**: 2026-04-01
- **Summary**: Added _compute_alpha_decay to screen.py computing cumulative alpha at 5d, 10d, 21d checkpoints within each holding period. Added section_decay to analyze.py classifying decay patterns. 10 new tests.
- **Final score**: 8.4 / 10

### Milestone 9: Quintile monotonicity in feature stats
- **Status**: completed
- **Date completed**: 2026-04-01
- **Summary**: Added q2-q4 alpha to compute_quintile_sharpe output. Updated feature_stats.md table to show all 5 quintile returns. 5 new tests.
- **Final score**: 9.0 / 10

### Milestone 10: Mechanism field in screen DSL
- **Status**: completed
- **Date completed**: 2026-04-01
- **Summary**: Added mechanism field (cause, expected_decay) to screen DSL. Backtest compares observed vs expected alpha decay. LLM prompt and program.md require mechanism. section_decay shows match/mismatch.
- **Final score**: 8.9 / 10

### Milestone 11: Mechanism diagnostics in analysis
- **Status**: completed
- **Date completed**: 2026-04-01
- **Summary**: Diagnostics were integrated into milestones 8-10 rather than needing a separate milestone. section_decay shows decay profiles + mechanism match. feature_stats.md shows quintile monotonicity. LLM prompt references both.
- **Final score**: N/A (absorbed into milestones 8-10)

## Current Milestone

None — all goal requirements satisfied.

## Upcoming Milestones

None.
