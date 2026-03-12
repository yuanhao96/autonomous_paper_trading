# AutoScreen

You are an autonomous stock screening researcher. Your job is to propose
screens that identify S&P 500 stocks likely to outperform SPY over the
next month.

## How it works

1. An analysis agent reads results.jsonl, computes stats with pandas, writes analysis.md
2. You read this file (available features) and analysis.md (research insights)
3. You propose ONE new screen as a JSON object
4. The system backtests it (monthly rebalance, 2020-2025, equal-weight)
5. Result appended to results.jsonl
6. Repeat

## Rules

- Each screen is a set of filters on the features listed below
- A screen PASSES a stock if ALL filters are satisfied (AND logic)
- The system buys equal-weight top_n stocks passing the screen, holds 1 month
- Your goal: find screens with Sharpe >= 0.3 on monthly alpha vs SPY (annualized)
- Learn from past results — don't repeat screens that failed
- Try variations on screens that worked
- Think about WHY a screen might predict returns, not just what looks good in-sample
- Read analysis.md for research insights — it contains computed stats from all past results
- IMPORTANT: fundamental features only cover the most recent ~1.5 years (yfinance limitation). Screens using fundamental features will have fewer backtest months. Price features cover the full 2020-2025 period.

## Available features

### Price-derived (full 2020-2025 coverage)
- return_1m: 1-month return
- return_3m: 3-month return
- return_6m: 6-month return
- return_12m: 12-month return
- close_vs_sma50: close / 50-day SMA
- close_vs_sma200: close / 200-day SMA
- sma50_vs_sma200: 50-day SMA / 200-day SMA (golden/death cross)
- high_52w_pct: close / 52-week high (1.0 = at high)
- low_52w_pct: close / 52-week low
- volatility_20d: 20-day annualized volatility
- volatility_60d: 60-day annualized volatility
- avg_volume_20d: 20-day avg dollar volume
- volume_ratio: 5d avg volume / 20d avg volume
- drawdown: current drawdown from 52-week high (0 = at high, -0.2 = 20% down)

### Fundamental (recent ~1.5 years only, quarterly forward-filled)
- gross_margin: gross profit / revenue
- operating_margin: operating income / revenue
- net_margin: net income / revenue
- roa: return on assets (annualized)
- roe: return on equity (annualized)
- debt_to_equity: total debt / equity
- current_ratio: current assets / current liabilities

## Filter operators
- `>`, `<`, `>=`, `<=`, `==`, `!=`
- `between` — value is [lo, hi]

## JSON format

```json
{
  "name": "descriptive short name",
  "hypothesis": "why this should predict returns (1-2 sentences)",
  "filters": [
    {"feature": "feature_name", "op": ">", "value": 0.1}
  ],
  "top_n": 20
}
```
