# AutoScreen: Mispricing Mechanism Testing

## Current Milestone

Evolve from "does this screen make money?" to "does this screen make money
for the reason I think it does?" by adding mechanism-aware diagnostics.

### 1. Alpha Decay Curve

Decompose each screen's returns by days-since-entry across rebalance periods.
Plot cumulative alpha over time (5, 10, 21, 42, 63 days) to distinguish
front-loaded edges (earnings drift) from slow structural edges (low-vol anomaly).

Data source: per-rebalance stock picks already in `data/details/` JSON files.

### 2. Quintile Monotonicity

For each screen's primary `rank_by` feature, compute returns across all five
quintiles (not just top vs. bottom). A real edge shows monotonic returns across
quintiles. Non-monotonic patterns suggest noise or confounding.

Extend `feature_stats.py` to report all five quintile returns.

### 3. Mechanism Field in Screen DSL

Add an optional `mechanism` field to the screen JSON:

```json
{
  "mechanism": {
    "cause": "Why consensus is wrong",
    "expected_decay": "front-loaded | gradual | regime-dependent"
  }
}
```

The LLM must articulate a mispricing cause for every proposal. The backtest
compares observed alpha decay against `expected_decay` and flags mismatches.

### 4. Mechanism Diagnostics in Backtest Output

After backtesting, compute and log:
- Alpha decay profile (cumulative return at 5d, 10d, 21d, 42d, 63d checkpoints)
- Quintile monotonicity score for the primary ranking feature
- Observed vs. expected decay match (if mechanism field provided)

Include these diagnostics in `results.jsonl` and surface them in `analysis.md`
so the LLM learns which mechanisms hold up and which don't.

## Why

The LLM currently proposes screens by pattern-matching on feature stats, producing
mechanistically hollow filters that overfit. By requiring a causal mechanism and
testing its specific predictions (alpha decay shape, quintile gradient), we:

- Reduce overfitting (testing structured predictions, not a single Sharpe number)
- Help the LLM compound understanding across iterations (learn which mechanisms
  hold up, not just which features have high IC)
- Distinguish real edges from statistical noise with limited data

## Definition of Done

1. Alpha decay curve computed for each backtest, logged in results.jsonl
2. All five quintile returns shown in feature_stats.py output
3. Screen DSL accepts optional `mechanism` field (backward compatible)
4. Backtest output includes mechanism diagnostics (decay profile, monotonicity)
5. `analysis.md` surfaces mechanism diagnostic summaries for KEEP screens
6. LLM prompt references mechanism diagnostics to improve proposal quality
7. All tests pass, all code passes ruff check

## Future (not this milestone)

- Mechanism-specific falsification tests (sector decomposition, earnings
  calendar alignment, analyst coverage filtering)
- Out-of-mechanism correlation (flag screens with different stated mechanisms
  but identical stock picks)
- Alpha combination: ensemble layer combining top uncorrelated screens
- Risk-aware weighting (min-variance, risk parity)
- Transaction cost modeling at 5/10/20 bps
