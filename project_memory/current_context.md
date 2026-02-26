# Current Context

## Active Milestone

**Name**: Backtester Realism (Slippage & Commissions)
**Goal**: Add slippage and commission modeling to the walk-forward backtester so strategy evaluations reflect realistic trading costs.

## Current Phase

**Phase**: execute
**Started**: 2026-02-25

## Key Decisions

- Percentage-based slippage model: buy at `price * (1 + slippage_pct)`, sell at `price * (1 - slippage_pct)`
- Flat per-trade commission deducted from P&L on each completed trade
- Default values of 0.0 for both to preserve backward compatibility
- Also add configurable defaults in config/settings.yaml under a `backtesting:` section
- Changes are additive — only BacktestConfig and _simulate_window are modified

## Blockers

<!-- None -->

## Plan Reference

### Steps

- [ ] 1. Add `slippage_pct` and `commission_per_trade` to `BacktestConfig` dataclass
- [ ] 2. Pass config into `_simulate_window` (currently a static method with no config access)
- [ ] 3. Apply slippage to entry/exit prices in `_simulate_window`
- [ ] 4. Deduct commission from P&L on each completed trade
- [ ] 5. Add `backtesting:` section to `config/settings.yaml` with defaults
- [ ] 6. Write tests: slippage degrades returns, commission accumulates, zero-slippage matches current behavior
- [ ] 7. Run full test suite + ruff check

## Notes

- Acceptance criteria:
  1. BacktestConfig accepts slippage_pct and commission_per_trade parameters
  2. Trade simulation applies slippage to entry/exit prices and deducts commissions from P&L
  3. Default slippage/commission are configurable in config/settings.yaml
  4. Tests verify: slippage degrades returns, commission accumulates, zero-slippage matches current behavior
