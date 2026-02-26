# Lessons Learned

## Milestone: Wire Evolution Loop into Agent Lifecycle (2026-02-25)

### What Worked
- Minimal wiring approach (add calls in existing code) was the right choice — all changes were additive try/except blocks with zero risk of regression.
- Lazy imports inside try/except handle the "no evolution DB yet" case naturally.
- The existing `load_survivors_from_store()` and `run_evolution_cycle()` methods were already well-designed; they just needed to be called.

### What Didn't Work
- Initial test patches targeted `agents.trading.agent.EvolutionStore` but the import is local (inside __init__), so `evolution.store.EvolutionStore` was the correct patch target. This cost one test iteration.

### Patterns to Reuse
- Lazy import + try/except: When adding optional integrations that may not have their backing store yet, use local imports inside try blocks with graceful fallback. This pattern keeps the system bootable in all states.
- Mirror changes: When two code paths do the same thing (TradingAgent.__init__ vs main.py _run_daily_cycle), apply the same change pattern to both and note the duplication for future cleanup.

### Patterns to Avoid
- Patching module-level attributes that are actually local imports: Always check whether the target is imported at module level or inside a function before choosing the patch path.

## Milestone: Strategy Promotion Pipeline (2026-02-25)

### What Worked
- Separate SQLite table approach: Adding `strategy_promotion` alongside existing `strategy_specs` avoided migration risk and kept concerns cleanly separated.
- SQL WHERE clauses for state machine enforcement: Using `WHERE status = 'candidate'` in UPDATE queries prevents invalid transitions without additional Python validation.
- tmp_path fixtures for SQLite tests: Each test gets its own DB, eliminating inter-test state leakage.

### What Didn't Work
- Initial implementation missed wiring `_check_promotions()` into the daily cycle — the method was defined but never called. Code reviewer caught this.
- No `unregister()` method existed on StrategyRegistry — reviewer flagged that retired strategies could never actually be removed from the in-memory registry. Added `unregister()` to fix.

### Patterns to Reuse
- Code review after implementation: The code reviewer agent caught two critical gaps (dead code, missing API) that were easy to fix post-implementation but would have been bugs in production.
- Backward-compatible loading: Check promoter first for promoted strategies, fall back to raw survivors from evolution store if none promoted yet. This lets the system work in all states (no promoter DB, empty promoter, populated promoter).

### Patterns to Avoid
- Defining methods without wiring them into the calling lifecycle: Always verify that new methods are actually invoked from the expected call sites, not just defined.

## Milestone: Template Engine & Backtester Robustness (2026-02-25)

### What Worked
- A+B hybrid (validation at entry points + defensive guards) was the right granularity — caught real bugs without over-engineering.
- Using `.get()` instead of `[]` on INDICATOR_REGISTRY avoids KeyError crashes and enables graceful fallback to empty Series.
- Skipping i=0 in backtester walk-forward roll (starting at i=1) is a one-line fix that eliminates an entire class of 1-bar edge cases.

### What Didn't Work
- Nothing notable — the milestone was well-scoped and all changes were defensive additions.

### Patterns to Reuse
- Column validation as first line of defense: `missing = REQUIRED - set(data.columns)` is a clean, readable pattern for data validation at function entry.
- Try/except with early return on price lookups: `try: price = float(data.loc[date, "Open"]) except (KeyError, TypeError): continue` handles sparse data gracefully.
- Opportunistic bug fixes: The `ingestion.py:543` undefined variable fix cost one line but prevented a runtime crash. Always fix discovered bugs even if they're outside the milestone scope.

### Patterns to Avoid
- Silent failures: Always log at WARNING level when returning early due to validation failures, so issues are visible in logs.

## Milestone: Auditor Safety & Preferences Enforcement (2026-02-25)

### What Worked
- AST-based validation is clean and reliable: `ast.walk()` catches all import/call patterns without executing the code.
- Separating `validate_code()` as a classmethod makes it independently testable without needing the full auditor pipeline.
- Post-generation preference validation as a standalone function (`validate_spec_against_preferences`) keeps concerns separated from the generator.

### What Didn't Work
- Initially included `input()` in forbidden calls, but the analysis scripts need `input()` to read context from stdin. Fixed by removing it from the list.

### Patterns to Reuse
- AST walking for code safety: `ast.parse()` + `ast.walk()` is the right tool for static analysis of untrusted code — no need for regex-based approaches.
- Preference validation as a pure function: Takes (spec, prefs) → violations list. Easy to test, easy to wire anywhere.

### Patterns to Avoid
- Over-restricting I/O: Think about what the sandboxed code actually needs (stdin/stdout for data exchange) before blocking everything.

## Milestone: Lint Cleanup & Code Quality (2026-02-25)

### What Worked
- Using `ruff check --fix` first to auto-fix 30/60 errors (import sorting, simple unused imports) saved significant time.
- Adding `# noqa: E402` for legitimate sys.path manipulation scripts is the right approach — restructuring imports would break the scripts.

### What Didn't Work
- Nothing notable — straightforward cleanup milestone.

### Patterns to Reuse
- Fix lint in layers: auto-fix first, then categorize remaining by rule code, batch-fix each category.
- For scripts that need sys.path manipulation before imports, use `# noqa: E402` rather than restructuring.

### Patterns to Avoid
- Don't try to fix E402 in scripts by moving sys.path into a conftest or similar — the scripts need to be standalone runnable.

## Milestone: Evolution Error Handling & Feedback Loop (2026-02-25)

### What Worked
- Using `audit_passed: set[str]` to track which survivors pass audit before the promotion step is clean and readable.
- Verifying existing wiring (feedback loop) before implementing saved time — the planner → store → generator → LLM prompt chain was already correct, just needed verification not reimplementation.
- Moving exhaustion check to cycle start (step 1b) with early return is a minimal, safe change.

### What Didn't Work
- Exhaustion test initially failed because `can_run_today()` returned False before the exhaustion check ran (seeded cycles completed "today"). Fixed by patching `can_run_today` to return True in the test.

### Patterns to Reuse
- When testing early-exit logic that depends on ordering, patch the preceding early-exit check to ensure the check-under-test actually runs.
- Verify existing wiring before building new: read the full call chain (store → planner → generator → prompt template) to confirm whether a gap actually exists.

### Patterns to Avoid
- Don't assume a gap exists without tracing the full call chain — the feedback loop was already wired correctly despite the acceptance criteria suggesting otherwise.

## Milestone: Daily P&L Tracking (2026-02-25)

### What Worked
- Minimal change approach: added `opening_equity` + `day_date` columns to existing account table rather than creating new tables. Schema migration via ALTER TABLE for pre-existing DBs.
- The `_ensure_day_baseline()` pattern cleanly handles both "first call of the day" (set baseline) and "subsequent calls" (compute delta) without explicit reset calls.
- Replacing `daily_pnl=0.0` with `daily_pnl=portfolio.daily_pnl` in two files was the minimal change needed to activate the existing RiskManager gate.

### What Didn't Work
- Nothing notable — the milestone was well-scoped and all changes were straightforward.

### Patterns to Reuse
- "Ensure baseline" pattern: On first access, set a baseline value; on subsequent accesses, compute delta from baseline. Auto-resets when the context changes (new day, new session).
- Schema migration in _init_db: Use PRAGMA table_info to check for missing columns and ALTER TABLE to add them. This handles upgrading existing databases without losing data.

### Patterns to Avoid
- Don't create separate P&L tables when the data naturally belongs as columns on an existing table (account).

## Milestone: Integration Test Suite (2026-02-25)

### What Worked
- Organizing tests by user-visible flow (startup→execution, evolve→promote, error recovery, persistence) made it clear what each test verifies.
- Using real (not mocked) components for most tests (compile_spec, EvolutionStore, StrategyPromoter, StateManager) caught a method name error (record_signal vs record_signals) that mocks would have hidden.

### What Didn't Work
- Initially used wrong method name `record_signal` instead of `record_signals` — caught by test execution.

### Patterns to Reuse
- Integration tests should use real components where possible; only mock external I/O (network, LLM calls, price fetching).
- Test corrupted DB by writing garbage bytes to the file path, then assert the constructor raises.

### Patterns to Avoid
- Don't over-mock: if the component is local and deterministic, use the real one.

## Milestone: Backtester Realism (Slippage & Commissions) (2026-02-25)

### What Worked
- Additive approach: only two fields added to BacktestConfig, one method signature changed. Zero risk of regression with default values of 0.0.
- Testing commission accumulation via `pnl_diff == num_trades * commission` is a clean, deterministic assertion that validates the exact deduction logic.
- Comparing trade-by-trade entry/exit prices between slippage and no-slippage runs validates the price adjustment direction (buy higher, sell lower).

### What Didn't Work
- Added `import numpy as np` to test file but never used it — caught by ruff. Minor issue.

### Patterns to Reuse
- Backward-compatible defaults: Adding new config fields with 0.0 defaults means all existing tests and callers work unchanged.
- Pair-wise comparison testing: Run the same strategy with two configs (one clean, one with costs) and compare results. This pattern is more robust than hardcoding expected values.
- Static method with optional config param: Passing `config: BacktestConfig | None = None` keeps the method as a static method while adding configurability.

### Patterns to Avoid
- Don't add imports speculatively — only import what you actually use in the file.
