# Plan: Strategy Promotion Pipeline

**Date**: 2026-02-25
**Milestone**: Strategy Promotion Pipeline

## Files

| File | Action | Description |
|------|--------|-------------|
| `evolution/promoter.py` | CREATE | StrategyPromoter class with SQLite promotion table |
| `agents/trading/agent.py` | MODIFY | Wire promoter into init (load promoted) + daily cycle (check promotions) |
| `config/settings.yaml` | MODIFY | Add promotion settings |
| `tests/test_promoter.py` | CREATE | Tests for full promotion lifecycle |

## Tasks

### Task 1: Create evolution/promoter.py
**Files**: `evolution/promoter.py`
**Description**: Create `StrategyPromoter` class with:
- SQLite table `strategy_promotion`: id, spec_name, spec_json, status (candidate/paper_testing/promoted/retired), composite_score, created_at, testing_started_at, promoted_at, retired_at, signals_generated, notes
- `submit_candidate(name, spec_json, score)` — insert with status='candidate'
- `start_testing(name)` — set status='paper_testing', testing_started_at=now
- `check_ready_for_promotion(testing_days, min_signals)` — return candidates whose testing period has elapsed and meet signal gate
- `promote(name)` — set status='promoted', promoted_at=now
- `retire(name, reason)` — set status='retired', retired_at=now
- `get_promoted() -> list[dict]` — return spec_json for all promoted strategies
- `get_paper_testing() -> list[str]` — return names of strategies in paper_testing
- Auto-create table in __init__
**Verify**: Unit tests in Task 4.

### Task 2: Wire promoter into evolution cycle
**Files**: `evolution/cycle.py`
**Description**: After tournament survivors are saved, submit them as candidates to the promoter. Then auto-start testing for any untested candidates.
**Verify**: Existing cycle tests still pass.

### Task 3: Wire promoter into TradingAgent
**Files**: `agents/trading/agent.py`
**Description**:
- In __init__: Load promoted strategies (from promoter) instead of raw survivors. Fall back to survivors if no promoted strategies exist.
- Add `_check_promotions()` method called at end of daily cycle: checks if any paper_testing candidates are ready for promotion.
- Track signal count per strategy during daily cycle to feed into promoter.
**Verify**: Agent starts cleanly. Integration tests pass.

### Task 4: Add promotion settings to config
**Files**: `config/settings.yaml`
**Description**: Add under `evolution:`:
- `promotion.testing_days: 5`
- `promotion.min_signals: 1`
**Verify**: Settings load correctly.

### Task 5: Write tests
**Files**: `tests/test_promoter.py`
**Description**: Test:
- Full lifecycle: submit → start_testing → check_ready → promote
- Retirement
- Not ready (too early, too few signals)
- get_promoted returns correct specs
- Backward compatibility: no promoter table → falls back to survivors
**Verify**: `pytest tests/test_promoter.py -v` passes.

## Dependency Order

- Task 1 must complete first (other tasks depend on promoter.py)
- Tasks 2, 3, 4 can proceed in parallel after Task 1
- Task 5 after Tasks 1-4

## Rollback

All changes are additive. The promoter creates a new table; existing tables untouched. Removing promoter.py and reverting agent.py restores current behavior.
