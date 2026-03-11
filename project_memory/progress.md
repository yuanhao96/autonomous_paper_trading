# Project Progress

## Goal Summary

Build a paper trading system that autonomously learns alpha factors. The system should: (1) write alpha factor strategies from the knowledge base, (2) backtest in different periods, (3) screen stocks, (4) autonomously learn parameters for individual alpha factors, combination of alpha factors, and stock screening parameters, and (5) support paper trading with Alpaca. Complete and extend the existing framework with minimal complexity — no over-engineering.

## Completed Milestones

### Milestone: Fix Composite Alpha Signal Quality
- **Status**: completed
- **Date completed**: 2026-03-11
- **Summary**: Added configurable factor weighting methods (global_sign, global_ic, sign, icir) and IC-threshold filtering to composite_alpha(). Best result with global_sign + min_ic=0.01: IC=0.016, t=3.3, monotonicity=1.0, L/S spread=+15%.
- **Acceptance criteria met**:
  - [x] Composite alpha validation verdict is WEAK or STRONG (not NONE)
  - [x] Quintile spread is positive (top quintile outperforms bottom)
  - [x] Mean |IC| >= 0.015 across the evaluation period
  - [x] At least 2 forward horizons (of 1,5,10,20 days) show positive IC

## Current Milestone

### Milestone: Implement Portfolio Allocation
- **Status**: in-progress
- **Acceptance criteria**:
  - [ ] `stratgen allocate` command exists and runs without error
  - [ ] Produces portfolio weights that sum to <= 1.0
  - [ ] Respects position size limits (no single stock > 5%)
  - [ ] Output saved to results_allocate.json with weights and metadata
- **Phase**: brainstorm

## Upcoming Milestones

### Milestone: Paper Trading Execution via Alpaca
- **Priority**: high
- **Depends on**: Implement Portfolio Allocation
- **Rough scope**: Extend trade.py to submit, monitor, and rebalance orders on Alpaca paper trading based on allocation weights.

### Milestone: Autonomous Learning Loop
- **Priority**: medium
- **Depends on**: Paper Trading Execution via Alpaca
- **Rough scope**: Build a periodic re-optimization pipeline that re-trains factor params, screening thresholds, and combination weights on rolling windows, then redeploys updated signals.
