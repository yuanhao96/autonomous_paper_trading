# AutoScreen: Percentile Ranks & Composite Scoring

## Purpose

Upgrade the screen DSL from absolute-threshold filtering to relative factor ranking.
Currently, screens express ideas like `ROE > 0.15` — but the right threshold shifts
over time. Professional quants think in cross-sectional terms: "top quintile of ROE,"
"composite of momentum + quality." This work adds percentile-rank features and
composite scoring to the DSL, making the autonomous loop capable of expressing
canonical multi-factor strategies.

## Requirements

### 1. Cross-Sectional Percentile Ranks
- For every existing numeric feature, compute its percentile rank (0-1) across all
  S&P 500 stocks on each rebalance date
- Expose as `{feature}_pctrank` in the feature matrix (e.g., `roe_pctrank`,
  `return_6m_pctrank`, `volatility_20d_pctrank`)
- Filters can then use relative thresholds: `{"feature": "roe_pctrank", "op": ">", "value": 0.8}`
  means "top 20% of ROE"
- Percentile ranks must be computed fresh at each rebalance date (no look-ahead bias)

### 2. Composite Scoring
- New DSL field `"score"` that defines a weighted combination of features:
  ```json
  {
    "score": [
      {"feature": "return_6m_pctrank", "weight": 0.4},
      {"feature": "roe_pctrank", "weight": 0.3},
      {"feature": "volatility_20d_pctrank", "weight": -0.3}
    ]
  }
  ```
- The composite score is computed per stock as a weighted sum
- Negative weights invert the feature (lower volatility = better)
- `rank_by` can reference `"_score"` to rank by the composite
- Filters still apply first, then composite scoring ranks the survivors

### 3. Backward Compatibility
- Existing screens in `results.jsonl` must remain valid — no breaking changes
- Screens without `score` or `_pctrank` features work exactly as before
- The new capabilities are purely additive

### 4. Update Program & Analysis
- Add `_pctrank` features and `score` field to the available features in `program.md`
- Update `analyze.py` to handle screens that use composite scoring
- Update the LLM prompt so it knows about and can propose percentile + composite screens

## Constraints

- **Modify existing files**: `screen.py`, `program.md`, `analyze.py` — no new modules
- **No paid data**: percentile ranks are computed from existing feature matrix
- **No classes**: functional style
- **All code passes `ruff check`** with 100-char line length
- **Tests in `tests/`** covering percentile computation, composite scoring, DSL parsing
- **No look-ahead bias**: percentile ranks computed only from data available at rebalance date

## Quality Priorities

| Dimension | Weight |
|-----------|--------|
| acceptance_criteria | 4 |
| correctness | 4 |
| test_coverage | 2 |
| code_quality | 3 |
| documentation | 1 |
| performance | 1 |

threshold: 7.0

## Definition of Done

1. `_pctrank` variants exist for all numeric features in the feature matrix
2. Percentile ranks are cross-sectional (computed per date, no look-ahead)
3. `score` field in DSL computes weighted composite and `rank_by: "_score"` works
4. Existing screens (without new fields) produce identical results
5. A sample composite screen (e.g., momentum + quality + low-vol) backtests successfully
6. `program.md` documents the new features and scoring syntax
7. `conda run -n data_science python run.py -n 3` completes 3 iterations using new features
8. All tests pass (`pytest tests/ -v`)
9. All code passes `ruff check`
