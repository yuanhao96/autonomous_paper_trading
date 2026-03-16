# AutoScreen: Score-First + Walk-Forward + Feature Enrichment

## Current Milestone

Three changes to make the screening loop more robust:

1. **Score-first strategy** (DONE) — Composite scoring replaces hard AND-filters as the
   primary screen mechanism. Scores degrade gracefully; filters create cliff effects.

2. **Walk-forward evaluation** (IN PROGRESS) — Replace single-date IS/OOS split with
   rolling walk-forward windows (18mo train / 6mo test). Multiple OOS observations
   produce a more robust Sharpe estimate than one fixed split.

3. **Feature enrichment + extended history** (NEXT) — Add return_1w, return_12m_skip_1m,
   idio_vol, volume_change_20d. Extend price data from 2019 to 2014 for 10+ years
   of backtest history and more walk-forward windows.

## Why

The previous approach had three problems:
- **Weak features**: No single feature had meaningful rank IC (best was 0.047). AND-filter
  screens on these features are searching in a desert.
- **Adversarial IS period**: 2020-2022 IS period spans covid crash, meme stocks, and rate
  hikes — three regime breaks that make finding stable screens almost impossible.
- **Rigid DSL**: Hard filters create cliff effects. A stock at 79th percentile is excluded
  while 80th passes, even though they're nearly identical.

## Definition of Done

1. `program.md` instructs LLM to use score-based screens by default
2. `apply_screen(walk_forward=True)` returns `wf_oos_sharpe_mean` across multiple windows
3. Walk-forward is the default mode in `run.py`
4. 4 new price features added: return_1w, return_12m_skip_1m, idio_vol, volume_change_20d
5. Data extended to 2014, backtest starts 2015
6. All tests pass, all code passes ruff check
