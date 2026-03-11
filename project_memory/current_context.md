# Current Context

## Active Milestone

**Name**: Autonomous Learning Loop
**Goal**: Build a single command that re-runs the full pipeline, logs results, and supports auto-tuning.

## Current Phase

**Phase**: review
**Started**: 2026-03-11

## Key Decisions

- [AUTO] `stratgen learn` chains screen → score → allocate end-to-end
- [AUTO] Factor combination weights already learned via IC-weighting in composite_alpha()
- [AUTO] Screen auto-tune: grid of min_adv values, pick best by composite |IC|
- [AUTO] Factor param re-optimization gated behind --reoptimize flag (not default)
- [AUTO] Each run logged to runs/YYYY-MM-DD-HHMMSS/ with summary JSON

## Blockers

(none)

## Plan Reference

### Steps

1. [x] Create src/stratgen/learner.py — run_learn(), tune_screen(), log_run()
2. [x] Add run logging: timestamped results to runs/ directory
3. [x] Add --tune-screen mode: grid search over min_adv
4. [x] Add learn subcommand to cli.py (parser + dispatch)
5. [x] Create tests/test_learner.py with 5 tests
6. [x] All 53 tests pass, lint clean
