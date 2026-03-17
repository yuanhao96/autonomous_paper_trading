# Project Progress

## Goal Summary

Move AutoScreen from "collect individual screens" to "build a useful portfolio" by adding screen deduplication/overlap detection and automatic rejection of degenerate screens (too concentrated, high turnover, sector-biased).

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

## Current Milestone

### Milestone 5: Screen dedup and overlap detection
- **Status**: in-progress
- **Phase**: brainstorm
- **Acceptance criteria**:
  - [ ] analyze.py computes pairwise overlap (Jaccard similarity of stock picks across rebalance dates) between all KEEP screens
  - [ ] analysis.md includes a "redundancy cluster" section showing groups of near-duplicate screens
  - [ ] LLM prompt in run.py references overlap stats to avoid redundant proposals
  - [ ] Tests for overlap computation
  - [ ] All code passes ruff check

## Upcoming Milestones

### Milestone 6: Automatic reject for degenerate screens
- **Priority**: high
- **Depends on**: none
- **Rough scope**: Add hard reject criteria in screen.py for avg_stocks < 5, turnover > 0.8, max_sector_weight > 0.5, win_rate < 0.45. Log rejected screens with reason.

### Milestone 7: Transaction cost modeling
- **Priority**: medium
- **Depends on**: Milestone 6
- **Rough scope**: Subtract turnover * cost_bps from period returns before computing Sharpe. One realistic cost parameter, not multi-assumption testing.
