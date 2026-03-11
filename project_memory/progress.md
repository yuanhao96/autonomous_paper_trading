# Project Progress

## Goal Summary

Build a paper trading system that autonomously learns alpha factors. The system should: (1) write alpha factor strategies from the knowledge base, (2) backtest in different periods, (3) screen stocks, (4) autonomously learn parameters for individual alpha factors, combination of alpha factors, and stock screening parameters, and (5) support paper trading with Alpaca. Complete and extend the existing framework with minimal complexity — no over-engineering.

## Completed Milestones

### Milestone: Fix Composite Alpha Signal Quality
- **Status**: completed
- **Date completed**: 2026-03-11
- **Summary**: Added configurable factor weighting methods (global_sign, global_ic, sign, icir) and IC-threshold filtering. Best: global_sign + min_ic=0.01 → IC=0.016, t=3.3, monotonicity=1.0, L/S spread=+15%.
- **Acceptance criteria met**:
  - [x] Composite alpha validation verdict is WEAK or STRONG
  - [x] Quintile spread is positive (+15.35%)
  - [x] Mean |IC| >= 0.015 (IC=0.0161)
  - [x] At least 2 forward horizons show positive IC (all 4)

### Milestone: Implement Portfolio Allocation
- **Status**: completed
- **Date completed**: 2026-03-11
- **Summary**: Built `allocate` command with alpha-proportional weighting, top-N filtering, and position caps. 20 positions at 5% each.
- **Acceptance criteria met**:
  - [x] `stratgen allocate` command exists and runs without error
  - [x] Portfolio weights sum to <= 1.0
  - [x] No single stock > 5%
  - [x] Output saved to results_allocate.json

## Current Milestone

### Milestone: Paper Trading Execution via Alpaca
- **Status**: in-progress
- **Acceptance criteria**:
  - [ ] `stratgen trade` command submits orders to Alpaca paper trading
  - [ ] Orders match the allocation weights from results_allocate.json
  - [ ] Position sizing accounts for account equity
  - [ ] `stratgen status` shows updated positions after trading
- **Phase**: brainstorm

## Upcoming Milestones

### Milestone: Autonomous Learning Loop
- **Priority**: medium
- **Depends on**: Paper Trading Execution via Alpaca
- **Rough scope**: Build a periodic re-optimization pipeline that re-trains factor params, screening thresholds, and combination weights on rolling windows.
