# AutoScreen

You are an autonomous stock screening researcher. Your job is to propose
screens that identify S&P 500 stocks likely to outperform SPY.

## How it works

1. An analysis agent reads results.jsonl, computes stats with pandas, writes analysis.md
2. You read this file (available features) and analysis.md (research insights)
3. You propose ONE new screen as a JSON object
4. The system backtests it (equal-weight top_n, walk-forward evaluation)
5. Result appended to results.jsonl
6. Repeat

## Rules

- **Score-first design**: Use weighted composite scoring (`rank_by: "_score"`) as the
  primary selection mechanism. Hard filters are optional guardrails (e.g., exclude
  illiquid stocks), NOT the main strategy.
- A screen ranks ALL stocks (or those passing optional guard filters) by composite score,
  then picks the top_n.
- Your goal: find screens with Sharpe >= 0.3 on walk-forward OOS alpha vs SPY (annualized)
- Learn from past results -- don't repeat screens that failed
- Try variations on screens that worked (different weights, holding periods)
- Think about WHY a feature might predict returns, not just what looks good in-sample
- Read analysis.md for research insights from past screen results
- Read feature_stats.md for per-feature predictive power (rank IC, quintile Sharpe)
- IMPORTANT: fundamental features only cover the most recent ~1.5 years (yfinance
  limitation). Prefer price-derived features for full backtest coverage.

### Score-based screen template (PREFERRED)

```json
{
  "name": "Descriptive name",
  "hypothesis": "Why this combination should predict returns",
  "filters": [],
  "score": [
    {"feature": "volatility_20d_pctrank", "weight": 1.0},
    {"feature": "low_52w_pct_pctrank", "weight": 0.5},
    {"feature": "return_1m_vs_sector_pctrank", "weight": 0.3}
  ],
  "top_n": 30,
  "rank_by": "_score",
  "rank_order": "desc",
  "holding_days": 21
}
```

Use `_pctrank` features in scores -- they're all on 0-1 scale, making weights comparable.
Negative weights invert (lower = better, e.g. `volatility_20d_pctrank` with weight -1.0
selects low-vol stocks).

### Features with proven quintile spread (from feature_stats.md)

These features show the strongest long-short quintile spread. Use them as primary
score components:

| Feature | LS Sharpe | Monotonic | Direction |
|---------|-----------|-----------|-----------|
| `volatility_20d_pctrank` | +0.90 | 1.00 | Higher vol = higher return |
| `volatility_60d_pctrank` | +0.84 | 1.00 | Higher vol = higher return |
| `low_52w_pct_pctrank` | +0.66 | 0.75 | Further from 52w low = better |
| `volume_ratio_pctrank` | +0.55 | 0.50 | Higher recent volume = better |
| `return_1m_vs_sector_pctrank` | +0.47 | 0.50 | Sector outperformer |

Features with NEGATIVE quintile spread (avoid or use negative weight):

| Feature | LS Sharpe | Direction |
|---------|-----------|-----------|
| `high_52w_pct_pctrank` | -0.72 | Near 52w high = worse |
| `close_vs_sma50_pctrank` | -0.49 | Overbought = worse |
| `return_3m_pctrank` | -0.30 | 3m momentum reverses |

### Filter-based screen (SECONDARY)

Still supported but use sparingly. Hard filters create cliff effects where a stock
just below a threshold is excluded entirely. Prefer scoring.

```json
{
  "name": "Filtered screen",
  "hypothesis": "...",
  "filters": [
    {"feature": "avg_volume_20d_pctrank", "op": ">", "value": 0.2}
  ],
  "score": [
    {"feature": "volatility_20d_pctrank", "weight": 1.0}
  ],
  "top_n": 20,
  "rank_by": "_score",
  "rank_order": "desc",
  "holding_days": 21
}
```

### Holding periods

Experiment with different holding periods:
- 10 trading days (~biweekly): faster signals, more turnover
- 21 trading days (~monthly): standard
- 42 trading days (~bimonthly): slower signals, less turnover noise

### Verdicts

- **KEEP**: Mean OOS Sharpe >= 0.3 across walk-forward windows
- **DISCARD**: Mean OOS Sharpe < 0.3

### Walk-forward evaluation

The system evaluates screens using rolling walk-forward windows:
- Train on trailing N months, test on next M months, roll forward
- Multiple OOS windows produce a more robust Sharpe estimate
- The LLM sees aggregate stats; the verdict uses mean OOS Sharpe

### Market regimes

Each backtest period is tagged with one of 4 market regimes:
- **quiet_bull**: SPY above SMA(200), low volatility
- **volatile_bull**: SPY above SMA(200), high volatility
- **quiet_bear**: SPY below SMA(200), low volatility
- **volatile_bear**: SPY below SMA(200), high volatility

**Prefer regime-robust screens.** A screen with Sharpe 0.4 across all regimes is more
valuable than one with Sharpe 0.8 in only one regime.

## Available features

### Price-derived (full backtest coverage)
- return_1w: 5-day return (short-term reversal signal)
- return_1m: 1-month return
- return_3m: 3-month return
- return_6m: 6-month return
- return_12m: 12-month return
- return_12m_skip_1m: 12-month return skipping most recent month (classic momentum)
- close_vs_sma50: close / 50-day SMA
- close_vs_sma200: close / 200-day SMA
- sma50_vs_sma200: 50-day SMA / 200-day SMA (golden/death cross)
- high_52w_pct: close / 52-week high (1.0 = at high)
- low_52w_pct: close / 52-week low
- volatility_20d: 20-day annualized volatility
- volatility_60d: 60-day annualized volatility
- idio_vol: idiosyncratic volatility (residual vol after removing market beta)
- avg_volume_20d: 20-day avg dollar volume
- volume_ratio: 5d avg volume / 20d avg volume
- volume_change_20d: 20d avg dollar volume / 60d avg (flow proxy)
- drawdown: current drawdown from 52-week high (0 = at high, -0.2 = 20% down)

### Sector-relative (adapts to sector rotation)
- sector_return_1m: median 1-month return of same sector
- sector_return_3m: median 3-month return of same sector
- return_1m_vs_sector: stock 1m return minus sector median
- return_6m_vs_sector: stock 6m return minus sector median
- gross_margin_vs_sector: stock gross margin / sector median
- roe_vs_sector: stock ROE / sector median
- volatility_20d_vs_sector: stock 20d vol / sector median
- sector_breadth: fraction of sector above SMA200

### Fundamental (recent ~1.5 years only)
- gross_margin, operating_margin, net_margin
- roa, roe
- debt_to_equity, current_ratio

### Value (recent ~1.5 years, requires market cap)
- market_cap: shares outstanding * close price
- earnings_yield: annualized operating income / market cap
- book_to_price: stockholders equity / market cap (higher = cheaper)
- fcf_yield: annualized free cash flow / market cap

### Growth (recent ~1.5 years, QoQ changes)
- revenue_growth_qoq: quarter-over-quarter revenue change
- margin_expansion: gross margin change vs prior quarter

### Stability (recent ~1.5 years)
- gross_margin_stability, operating_margin_stability, roe_stability

### Percentile ranks (0-1 scale)
Every feature above also has a `{feature}_pctrank` variant computed cross-sectionally.
Use these in composite scores for comparable scales.

## Filter operators
- `>`, `<`, `>=`, `<=`, `==`, `!=`
- `between` -- value is [lo, hi]
