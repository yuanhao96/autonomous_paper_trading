# Project Progress

## Goal Summary

Add regime awareness (2x2 grid: trend x volatility from SPY data) and out-of-sample discipline (IS/OOS split with configurable split_date) to the AutoScreen system. Regime labels tag every backtest period; OOS Sharpe drives keep/discard verdicts; LLM sees only IS-period stats.

## Completed Milestones

### Milestone 1: Regime computation and feature integration
- **Status**: completed
- **Date completed**: 2026-03-14
- **Summary**: Added compute_regime() to screen.py — 2x2 grid (trend x vol) from SPY data. Regime broadcast to all tickers in feature DataFrame. 4 new tests (2 synthetic, 2 real data).
- **Final score**: 9.0 / 10

## Current Milestone

### Milestone 2: IS/OOS split in backtest
- **Status**: in_progress
- **Phase**: brainstorm
- **Acceptance Criteria**:
  1. `apply_screen()` accepts optional `split_date` parameter
  2. Returns `sharpe_is`, `sharpe_oos`, `sharpe_ratio`, and per-regime `regime_stats`
  3. Verdict uses `sharpe_oos >= 0.3` when split_date is set
  4. Without `split_date`, behavior is identical to current (backward compatible)
  5. Tests verify split metrics and backward compatibility

## Upcoming Milestones

### Milestone 3: Analysis sections (regime + oos)
- **Status**: not_started
- **Acceptance Criteria**:
  1. `analyze.py --section regime` shows per-regime breakdown with robustness scores
  2. `analyze.py --section oos` shows IS vs OOS Sharpe with overfit warnings
  3. Summary section includes OOS stats when available
  4. Tests for new analysis sections

### Milestone 4: Orchestration and LLM integration
- **Status**: not_started
- **Acceptance Criteria**:
  1. `run.py --split-date 2023-07-01` passes split_date through the loop
  2. LLM analysis prompt references regime robustness and OOS shrinkage
  3. `program.md` documents regime labels, IS/OOS split, overfit detection
  4. Current regime label provided as context for proposals
  5. All code passes `ruff check` and `pytest tests/ -v`
