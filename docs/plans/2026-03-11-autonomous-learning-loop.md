# Plan: Autonomous Learning Loop

## Objective

Build `stratgen learn` — a single command that chains the full pipeline (screen → score → allocate), logs timestamped results, and optionally auto-tunes screening thresholds.

## Steps

### 1. Create `src/stratgen/learner.py`

Core module with:

- `run_learn()` — orchestrates: screen → score → allocate
  - Calls existing `run_screen()`, reuses score+allocate logic
  - Returns a summary dict with key metrics (composite IC, n_positions, etc.)
- `tune_screen()` — tries min_adv grid [1M, 5M, 10M], picks best by composite |IC|
  - For each min_adv: run screen → score, extract mean |IC|
  - Returns best params
- `log_run()` — saves run results to `runs/YYYY-MM-DD-HHMMSS/`
  - Copies result JSONs (screen, score, allocate) into the run directory
  - Creates `summary.json` with key metrics + params used
- `compare_runs()` — loads previous run summaries and compares IC trend

### 2. Add `learn` subcommand to cli.py

Flags:
- `--tune-screen` — enable screening param auto-tune (default: off)
- `--trade` — also execute trade after allocate (default: off)
- `--dry-run` — print orders without executing
- Standard flags: `--universe`, `--weight-method`, `--min-ic`

### 3. Create `tests/test_learner.py`

- Test `log_run()` creates correct directory structure
- Test `compare_runs()` with mock run directories
- Test `tune_screen()` picks best min_adv (with mocked score results)

### 4. Verify end-to-end

- Run `stratgen learn` and confirm it chains all steps
- Check `runs/` directory has timestamped output

## Files

| File | Action |
|------|--------|
| `src/stratgen/learner.py` | Create |
| `src/stratgen/cli.py` | Modify (add learn subcommand) |
| `src/stratgen/paths.py` | Modify (add RUNS_DIR) |
| `tests/test_learner.py` | Create |

## Dependencies

- All existing pipeline modules (screener, scorer, allocator, factor_screen, factor_score, factor_allocate)
- No new external dependencies
