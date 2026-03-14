# Project Progress

## Goal Summary

Add regime awareness (2x2 grid: trend x volatility from SPY data) and out-of-sample discipline (IS/OOS split with configurable split_date) to the AutoScreen system. Regime labels tag every backtest period; OOS Sharpe drives keep/discard verdicts; LLM sees only IS-period stats. Coupled design ensures OOS periods cover multiple regime conditions.

## Completed Milestones

<!-- None yet. -->

## Current Milestone

### Milestone 1: Regime computation and feature integration
- **Status**: not_started
- **Phase**: brainstorm
- **Acceptance Criteria**:
  1. `compute_regime(prices)` returns daily Series with 4 labels (quiet_bull, volatile_bull, quiet_bear, volatile_bear)
  2. Trend axis uses SPY close vs SMA(200)
  3. Volatility axis uses SPY 20d realized vol vs expanding median
  4. Regime column added to feature DataFrame via `compute_all_features()`
  5. Tests verify regime labels on synthetic price data

## Upcoming Milestones

### Milestone 2: IS/OOS split in backtest
- **Status**: not_started
- **Acceptance Criteria**:
  1. `apply_screen()` accepts optional `split_date` parameter
  2. Returns `sharpe_is`, `sharpe_oos`, `sharpe_ratio`, and per-regime `regime_stats`
  3. Verdict uses `sharpe_oos >= 0.3` when split_date is set
  4. Without `split_date`, behavior is identical to current (backward compatible)
  5. Tests verify split metrics and backward compatibility

### Milestone 3: Analysis sections (regime + oos)
- **Status**: not_started
- **Acceptance Criteria**:
  1. `analyze.py --section regime` shows per-regime breakdown with robustness scores
  2. `analyze.py --section oos` shows IS vs OOS Sharpe with overfit warnings (ratio > 3)
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
