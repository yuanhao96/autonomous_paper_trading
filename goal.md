# AutoScreen: Regime Awareness + Out-of-Sample Discipline

## Purpose

Add two foundational capabilities that make the screening loop robust:

1. **Regime awareness** — tag every backtest period with a market regime so the system
   (and LLM) can distinguish "works everywhere" from "only works in quiet bull markets"
2. **Out-of-sample discipline** — split the backtest into IS/OOS periods so the
   keep/discard decision uses forward performance, not the same data the LLM optimized on

These are coupled: regime labels make OOS splits meaningful by ensuring the test period
isn't just "a different regime" but covers multiple conditions.

### Problem

Current system has two blind spots:

1. **No regime context** — a screen with Sharpe 0.5 might only work during 2020–2021
   easy-money bull runs. The LLM can't see this and keeps proposing momentum screens
   that worked historically but are regime-dependent.
2. **Overfitting loop** — the LLM sees full-period stats (2020–2025), proposes screens
   to beat those stats, and the keep/discard verdict uses the same period. In-sample
   Sharpes of 0.5+ routinely shrink to 0.0–0.2 out-of-sample.

## Design

### Regime Model: 2x2 grid

Two axes, both computed from S&P 500 (SPY) price data already in cache:

| | Low Vol | High Vol |
|---|---------|----------|
| **Uptrend** | `quiet_bull` | `volatile_bull` |
| **Downtrend** | `quiet_bear` | `volatile_bear` |

- **Trend**: SPY close vs SMA(200). Above = uptrend, below = downtrend.
- **Volatility**: SPY 20-day realized vol. Above rolling median = high, below = low.

Regime is computed daily, stored as a column in the feature DataFrame.

### OOS Split: Option C (expanding window with held-out buffer)

```
Full backtest:     2020-01-01 ──────────── 2025-12-31
                   ├── IS ──────┤├── OOS ──────────┤
                   2020-01-01   split_date    2025-12-31
```

- `split_date` defaults to `2023-07-01` (~60/40 IS/OOS split)
- `split_date` is configurable via CLI (`--split-date`)
- Backtest runs over the full period but reports IS and OOS metrics separately
- LLM sees IS-period stats only (via analyze.py)
- Keep/discard decision uses OOS Sharpe

## Requirements

### 1. Regime computation (`screen.py`)

Add a function `compute_regime(prices)` that returns a Series of regime labels
(`quiet_bull`, `volatile_bull`, `quiet_bear`, `volatile_bear`) indexed by date.

- Uses SPY close vs SMA(200) for trend
- Uses SPY 20-day realized vol vs its expanding median for volatility threshold
- Returns one label per trading day
- Regime column added to the feature DataFrame via `compute_all_features()`

### 2. Split backtest results (`screen.py`)

Modify `apply_screen()` to accept an optional `split_date` parameter:

- When `split_date` is provided, compute and return separate metrics:
  - `sharpe_is`, `sharpe_oos` (in-sample and out-of-sample Sharpe)
  - `alpha_monthly_mean_is`, `alpha_monthly_mean_oos`
  - `win_rate_is`, `win_rate_oos`
  - `n_months_is`, `n_months_oos`
  - `sharpe_ratio` (IS/OOS — overfit detector; >3 is a red flag)
- Per-regime stats: `regime_stats` dict mapping regime label to
  `{alpha_mean, win_rate, n_months}` for each of the 4 regimes
- Verdict uses `sharpe_oos` when `split_date` is set
- When `split_date` is None, behavior is unchanged (backward compatible)
- Full-period `sharpe` still computed and returned for continuity

### 3. Regime-aware analysis (`analyze.py`)

Upgrade the `regime` section:
- Show per-regime performance breakdown for each KEEP screen
  (mean alpha, win rate, N periods per regime)
- Add regime robustness score: fraction of regimes where mean alpha > 0
- Show current regime (latest date in data)

Add IS/OOS analysis:
- New section `oos` showing IS vs OOS Sharpe for all screens
- Flag screens with IS/OOS ratio > 3 as "OVERFIT WARNING"
- Summary stats: mean IS Sharpe, mean OOS Sharpe, mean shrinkage

### 4. Update orchestration (`run.py`)

- Pass `split_date` to `apply_screen()`
- Add `--split-date` CLI argument (default: `2023-07-01`)
- Keep/discard: use `sharpe_oos >= 0.3` when split_date is set
- LLM analysis prompt includes regime context and IS/OOS framing
- Log both IS and OOS metrics to `results.jsonl`

### 5. Update LLM context (`program.md`)

- Document the 4 regime labels and what they mean
- Explain IS/OOS split: LLM sees IS stats, screens judged on OOS
- Add `market_regime` to the feature table
- Note that IS/OOS Sharpe ratio > 3 indicates overfitting
- Encourage the LLM to consider regime robustness when proposing screens

### 6. Update analysis LLM prompt (`run.py`)

- Ask the LLM to comment on regime robustness
- Ask the LLM to note IS vs OOS shrinkage patterns
- Provide current regime label as context for proposals

## Scope

- **Modify**: `screen.py`, `analyze.py`, `run.py`, `program.md`
- **Do NOT modify**: `data.py`, `feature_stats.py`, `screen_report.py`
- **Do NOT change**: data download pipeline, parquet format

## Constraints

- **No new dependencies**: use only numpy, pandas, scipy (already available)
- **No classes**: functional style, consistent with existing code
- **All code passes `ruff check`** with 100-char line length
- **Tests in `tests/`** covering regime computation, IS/OOS split, verdict logic
- **Backward compatible**: `apply_screen()` without `split_date` behaves exactly as before.
  Existing `results.jsonl` entries remain valid.

## Quality Priorities

| Dimension | Weight |
|-----------|--------|
| acceptance_criteria | 4 |
| correctness | 4 |
| test_coverage | 3 |
| code_quality | 3 |
| documentation | 1 |
| performance | 1 |

threshold: 7.0

## Definition of Done

1. `compute_regime()` returns 4-label regime Series from SPY price data
2. `apply_screen(split_date="2023-07-01")` returns `sharpe_is`, `sharpe_oos`,
   `sharpe_ratio`, and `regime_stats`
3. `apply_screen()` without `split_date` returns identical results to current behavior
4. Verdict is `KEEP` when `sharpe_oos >= 0.3`, `DISCARD` otherwise (when split_date set)
5. `analyze.py --section regime` shows per-regime breakdown with robustness scores
6. `analyze.py --section oos` shows IS vs OOS comparison with overfit warnings
7. `run.py --split-date 2023-07-01` runs the loop with OOS discipline
8. `program.md` documents regime labels, IS/OOS split, and overfit detection
9. LLM analysis prompt references regime and OOS context
10. Existing `results.jsonl` entries work unchanged
11. All tests pass (`pytest tests/ -v`)
12. All code passes `ruff check`
