# Plan: Wire Evolution Loop into Agent Lifecycle

**Date**: 2026-02-25
**Milestone**: Wire Evolution Loop into Agent Lifecycle

## Files to Modify

| File | Change |
|------|--------|
| `agents/trading/agent.py` | Load survivors in __init__, trigger evolution after learning |
| `main.py` | Load survivors in _run_daily_cycle |
| `config/settings.yaml` | Add `auto_trigger_after_learning` setting |
| `tests/test_evolution_integration.py` | New integration test file |

## Tasks

### Task 1: Add survivor loading to TradingAgent.__init__()
**Files**: `agents/trading/agent.py`
**Change**: After registering default strategies (line 78), add a try/except block that creates an EvolutionStore and calls `self._registry.load_survivors_from_store(store)`. Log how many survivors were loaded.
**Verify**: Existing tests still pass. Agent starts cleanly with no evolution DB.

### Task 2: Add optional evolution trigger to run_learning_session()
**Files**: `agents/trading/agent.py`, `config/settings.yaml`
**Change**: At the end of `run_learning_session()` (after line 649), check the `evolution.auto_trigger_after_learning` setting. If true and topics were studied, call `self.run_evolution_cycle(trigger="knowledge_acquired")`. Add `auto_trigger_after_learning: false` to config/settings.yaml under evolution section.
**Verify**: Learning session still returns same summary. With setting=false, no evolution runs.

### Task 3: Add survivor loading to main.py _run_daily_cycle()
**Files**: `main.py`
**Change**: After the default strategy registration block (line 424), add a try/except that loads survivors into the module-level `registry`. Same pattern as Task 1 but using the module-level singleton.
**Verify**: Daily cycle still works. With no DB, no crash.

### Task 4: Write integration test
**Files**: `tests/test_evolution_integration.py` (new)
**Change**: Create an integration test that mocks call_llm and get_ohlcv_range, then verifies the full pipeline: generate specs → compile → backtest → tournament → audit → persist → reload survivors into registry. Also test that TradingAgent.__init__ loads survivors when store has data.
**Verify**: `pytest tests/test_evolution_integration.py -v` passes.

## Dependency Order

- Tasks 1, 2, 3 are independent of each other.
- Task 4 depends on Tasks 1-3 (tests the integrated result).

## Tests

- **Unit**: Existing 232 tests must still pass after all changes.
- **Integration**: New test_evolution_integration.py covers the full pipeline.
- **Manual**: `python main.py --dry-run` should show evolved strategies if any exist.

## Rollback

All changes are additive (new code in try/except blocks). Removing the added blocks reverts to current behavior. No database migrations or breaking changes.
