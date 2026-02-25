# Current Context

## Active Milestone

**Name**: Auditor Safety & Preferences Enforcement
**Goal**: Tighten auditor sandbox and ensure generated strategies respect human preferences.

## Current Phase

**Phase**: execute
**Started**: 2026-02-25

## Key Decisions

- AST-based code validation for Layer2 auditor: Check for forbidden imports (os, subprocess, sys, etc.) and dangerous builtins (eval, exec, __import__) before executing LLM-generated code.
- Post-generation preference validation: After LLM generates a spec, validate RiskParams against preferences.yaml limits. Reject specs that violate preferences.

## Blockers

<!-- None -->

## Plan Reference

### Steps

1. [ ] Add `_validate_code()` to Layer2Auditor with AST-based forbidden import/call checks
2. [ ] Add `validate_spec_against_preferences()` function
3. [ ] Wire preference validation into StrategyGenerator
4. [ ] Write tests for both safety features
5. [ ] Run full test suite

## Notes

- Forbidden imports: os, subprocess, sys, shutil, socket, http, urllib, ctypes, importlib
- Forbidden builtins: eval, exec, __import__, compile, open (file access)
- Preferences to enforce: max_position_pct, max_drawdown_pct via stop_loss_pct
