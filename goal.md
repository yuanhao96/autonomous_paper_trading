# AutoScreen: Alpha Combination & Screen Quality

## Current Milestone

Two changes to move from "collect individual screens" to "build a useful portfolio":

1. **Screen dedup & overlap detection** — Many KEEP screens are near-duplicates
   (same core factors, slightly different thresholds). Add correlation analysis
   between KEEP screens' stock picks across time. Flag redundant screens so the
   LLM avoids proposing more of the same. Surface overlap stats in analysis.md.

2. **Automatic reject for degenerate screens** — Screens that pass Gate 1
   (backtest runs) can still be degenerate. Add hard reject criteria:
   - Average stock count < 5 (too concentrated)
   - Turnover > 80% per rebalance (churning)
   - > 50% of weight in a single sector (sector bet, not alpha)
   - Win rate < 45% (losing more periods than winning)

## Why

The loop is now producing KEEP screens at a healthy rate, but quantity without
quality control leads to a bloated pool of correlated bets. The two biggest
risks at this stage:

- **Redundancy**: The LLM keeps proposing slight variations of the same
  momentum + idio_vol + sector_contrarian screen. Without overlap detection,
  the KEEP pool grows but diversification doesn't.
- **Degenerate screens**: Some screens pass the Sharpe threshold by being
  extremely concentrated or sector-biased, which wouldn't survive real
  portfolio construction.

## Definition of Done

1. `analyze.py` computes pairwise overlap (Jaccard similarity of stock picks
   across rebalance dates) between all KEEP screens
2. `analysis.md` includes a "redundancy cluster" section showing groups of
   near-duplicate screens
3. `screen.py` rejects screens with avg_stocks < 5, turnover > 0.8,
   max_sector_weight > 0.5, or win_rate < 0.45 before computing Sharpe
4. Rejected screens are logged to results.jsonl with verdict REJECT and reason
5. LLM prompt in run.py references overlap stats to avoid redundant proposals
6. All tests pass, all code passes ruff check

## Future (not this milestone)

- **Alpha combination**: Ensemble layer combining top uncorrelated screens
  into a single portfolio with diversified alpha sources
- **Risk-aware weighting**: Move from equal-weight to min-variance or risk
  parity within the combined portfolio
- **Marginal IR**: Score new screens by how much incremental Sharpe they add
  to the existing portfolio, not just standalone performance
- **Transaction cost modeling**: Test screens at 5/10/20 bps cost assumptions
- **Complexity penalty**: Penalize screens with many filters to reduce
  overfitting risk
