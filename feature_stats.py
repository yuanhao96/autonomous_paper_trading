"""Compute per-feature predictive power stats and write feature_stats.md."""
import numpy as np
import pandas as pd
from scipy import stats

from screen import DATA_DIR, compute_all_features

# Core template for conditional marginal IC analysis.
# These are the features with strongest unconditional quintile spread,
# used as the "base model" to test what additional features help.
CORE_FILTERS = [
    ("volatility_20d_pctrank", ">", 0.5),
    ("low_52w_pct_pctrank", ">", 0.5),
]

HOLDING_DAYS = 21  # Evaluate at monthly frequency


def load_forward_alpha(holding_days: int = HOLDING_DAYS) -> pd.DataFrame:
    """Compute forward alpha (stock return - SPY return) for each rebalance date.

    Returns DataFrame: (rebal_dates x tickers) of forward alpha.
    """
    prices = pd.read_parquet(DATA_DIR / "prices.parquet")
    close = prices["Close"]
    spy = close["SPY"]

    date_range = close.loc["2015-01-01":"2025-12-31"].index
    rebal_indices = list(range(0, len(date_range), holding_days))

    rows = {}
    for i in range(len(rebal_indices) - 1):
        d0 = date_range[rebal_indices[i]]
        d1 = date_range[rebal_indices[i + 1]]

        spy_ret = spy.loc[d1] / spy.loc[d0] - 1 if spy.loc[d0] > 0 else 0.0
        stock_ret = close.loc[d1] / close.loc[d0] - 1
        rows[d0] = stock_ret - spy_ret

    return pd.DataFrame(rows).T.sort_index()


def get_feature_at_dates(features: pd.DataFrame, feat_name: str,
                         dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Extract a single feature at given dates. Returns (dates x tickers)."""
    if feat_name not in features.columns.get_level_values(0):
        return None
    feat = features[feat_name]
    return feat.reindex(dates)


def compute_rank_ic(features: pd.DataFrame, fwd_alpha: pd.DataFrame) -> dict:
    """Spearman rank IC for each feature vs forward alpha.

    Returns {feature: {ic_mean, ic_std, ic_ir, pct_positive, n_months}}.
    """
    dates = fwd_alpha.index
    feat_names = features.columns.get_level_values(0).unique().tolist()
    # Remove SPY from tickers
    tickers = [t for t in fwd_alpha.columns if t != "SPY"]

    results = {}
    for feat_name in feat_names:
        feat_data = get_feature_at_dates(features, feat_name, dates)
        if feat_data is None:
            continue

        # Use only tickers present in both datasets
        feat_tickers = set(feat_data.columns)
        valid_tickers = [t for t in tickers if t in feat_tickers]
        if len(valid_tickers) < 20:
            continue

        ics = []
        for date in dates:
            f = feat_data.loc[date, valid_tickers].dropna()
            a = fwd_alpha.loc[date].reindex(f.index).dropna()
            common = f.index.intersection(a.index)
            if len(common) < 20:
                continue
            corr, _ = stats.spearmanr(f[common], a[common])
            if not np.isnan(corr):
                ics.append(corr)

        if len(ics) < 6:
            continue

        ic_arr = np.array(ics)
        ic_mean = float(np.mean(ic_arr))
        ic_std = float(np.std(ic_arr))
        results[feat_name] = {
            "ic_mean": round(ic_mean, 4),
            "ic_std": round(ic_std, 4),
            "ic_ir": round(ic_mean / ic_std, 3) if ic_std > 0 else 0.0,
            "pct_positive": round(float(np.mean(ic_arr > 0)), 3),
            "n_months": len(ics),
        }

    return results


def compute_quintile_sharpe(features: pd.DataFrame,
                            fwd_alpha: pd.DataFrame) -> dict:
    """Long-short quintile Sharpe for each feature.

    For each month: sort stocks by feature, buy top quintile, short bottom quintile.
    Returns {feature: {ls_sharpe, q1_alpha, q5_alpha, monotonic}}.
    """
    dates = fwd_alpha.index
    feat_names = features.columns.get_level_values(0).unique().tolist()
    tickers = [t for t in fwd_alpha.columns if t != "SPY"]

    results = {}
    for feat_name in feat_names:
        feat_data = get_feature_at_dates(features, feat_name, dates)
        if feat_data is None:
            continue

        feat_tickers = set(feat_data.columns)
        valid_tickers = [t for t in tickers if t in feat_tickers]
        if len(valid_tickers) < 25:
            continue

        quintile_alphas = {q: [] for q in range(1, 6)}

        for date in dates:
            f = feat_data.loc[date, valid_tickers].dropna()
            a = fwd_alpha.loc[date].reindex(f.index).dropna()
            common = f.index.intersection(a.index)
            if len(common) < 25:  # Need at least 5 per quintile
                continue

            ranked = f[common].rank(pct=True)
            for q in range(1, 6):
                lo = (q - 1) / 5
                hi = q / 5
                if q == 5:
                    mask = ranked > lo
                else:
                    mask = (ranked > lo) & (ranked <= hi)
                q_tickers = mask[mask].index
                if len(q_tickers) > 0:
                    quintile_alphas[q].append(float(a[q_tickers].mean()))

        min_months = 6
        if any(len(v) < min_months for v in quintile_alphas.values()):
            continue

        q_means = {q: np.mean(v) for q, v in quintile_alphas.items()}

        # Long-short: Q5 (top) - Q1 (bottom)
        ls_returns = np.array(quintile_alphas[5]) - np.array(
            quintile_alphas[1][:len(quintile_alphas[5])]
        )
        ls_mean = float(np.mean(ls_returns))
        ls_std = float(np.std(ls_returns))
        periods_per_year = 252 / HOLDING_DAYS
        ls_sharpe = ls_mean / ls_std * np.sqrt(periods_per_year) if ls_std > 0 else 0.0

        # Monotonicity: are quintile returns increasing Q1→Q5?
        q_mean_list = [q_means[q] for q in range(1, 6)]
        diffs = [q_mean_list[i + 1] - q_mean_list[i] for i in range(4)]
        monotonic = sum(1 for d in diffs if d > 0) / 4  # 1.0 = perfectly monotonic

        results[feat_name] = {
            "ls_sharpe": round(ls_sharpe, 3),
            "q1_alpha": round(q_means[1] * 100, 2),
            "q2_alpha": round(q_means[2] * 100, 2),
            "q3_alpha": round(q_means[3] * 100, 2),
            "q4_alpha": round(q_means[4] * 100, 2),
            "q5_alpha": round(q_means[5] * 100, 2),
            "spread": round((q_means[5] - q_means[1]) * 100, 2),
            "monotonic": round(monotonic, 2),
        }

    return results


def compute_conditional_marginal(features: pd.DataFrame,
                                 fwd_alpha: pd.DataFrame) -> dict:
    """Conditional marginal IC: given stocks passing core template, what's the IC of each feature?

    Returns {feature: {cond_ic, cond_n_months}}.
    """
    dates = fwd_alpha.index
    feat_names = features.columns.get_level_values(0).unique().tolist()
    tickers = [t for t in fwd_alpha.columns if t != "SPY"]

    # Core template feature names (skip them in marginal analysis)
    core_feat_names = {f[0] for f in CORE_FILTERS}

    results = {}
    for feat_name in feat_names:
        if feat_name in core_feat_names:
            continue

        feat_data = get_feature_at_dates(features, feat_name, dates)
        if feat_data is None:
            continue

        feat_tickers = set(feat_data.columns)
        valid_tickers = [t for t in tickers if t in feat_tickers]

        ics = []
        for date in dates:
            # Apply core filters to get the "qualified" universe
            qualified = set(valid_tickers)
            for cf_name, cf_op, cf_val in CORE_FILTERS:
                cf_data = get_feature_at_dates(features, cf_name, [date])
                if cf_data is None:
                    continue
                available = [t for t in qualified if t in cf_data.columns]
                series = cf_data.loc[date, available].dropna()
                if cf_op == ">":
                    passing = series[series > cf_val].index
                elif cf_op == ">=":
                    passing = series[series >= cf_val].index
                elif cf_op == "<":
                    passing = series[series < cf_val].index
                else:
                    passing = series.index
                qualified &= set(passing)

            if len(qualified) < 15:
                continue

            qual_list = sorted(qualified)
            available_qual = [t for t in qual_list if t in feat_data.columns]
            f = feat_data.loc[date, available_qual].dropna()
            a = fwd_alpha.loc[date].reindex(f.index).dropna()
            common = f.index.intersection(a.index)
            if len(common) < 10:
                continue

            corr, _ = stats.spearmanr(f[common], a[common])
            if not np.isnan(corr):
                ics.append(corr)

        if len(ics) < 6:
            continue

        ic_arr = np.array(ics)
        ic_mean = float(np.mean(ic_arr))
        ic_std = float(np.std(ic_arr))
        results[feat_name] = {
            "cond_ic": round(ic_mean, 4),
            "cond_ic_ir": round(ic_mean / ic_std, 3) if ic_std > 0 else 0.0,
            "cond_pct_pos": round(float(np.mean(ic_arr > 0)), 3),
            "cond_n_months": len(ics),
        }

    return results


def write_feature_stats(rank_ic: dict, quintile: dict, conditional: dict):
    """Write feature_stats.md with all computed stats."""
    lines = [
        "# Feature Predictive Power Stats",
        "",
        f"Computed on S&P 500 universe, 2015-01 to 2025-12, {HOLDING_DAYS}-day forward alpha vs SPY.",
        "",
        "## 1. Rank IC (Spearman correlation: feature rank vs forward alpha rank)",
        "",
        "Higher |IC mean| = more predictive. IC IR > 0.5 is strong. "
        "Pct positive > 60% means the signal is consistent.",
        "",
        "| Feature | IC Mean | IC Std | IC IR | Pct Positive | Months |",
        "|---------|---------|--------|-------|-------------|--------|",
    ]

    # Sort by abs IC mean descending
    for feat, v in sorted(rank_ic.items(), key=lambda x: abs(x[1]["ic_mean"]), reverse=True):
        lines.append(
            f"| `{feat}` | {v['ic_mean']:+.4f} | {v['ic_std']:.4f} | "
            f"{v['ic_ir']:+.3f} | {v['pct_positive']:.1%} | {v['n_months']} |"
        )

    lines += [
        "",
        "## 2. Quintile Long-Short Sharpe",
        "",
        "Each month: sort stocks by feature, measure alpha of each quintile. "
        "Q5 = top, Q1 = bottom. LS Sharpe = annualized Sharpe of (Q5 - Q1). "
        "Monotonic = fraction of Q1→Q5 steps that increase (1.0 = perfect). "
        "A real edge shows smooth gradient Q1→Q5; non-monotonic suggests noise.",
        "",
        "| Feature | LS Sharpe | Q1% | Q2% | Q3% | Q4% | Q5% | Spread% | Mono |",
        "|---------|-----------|-----|-----|-----|-----|-----|---------|------|",
    ]

    for feat, v in sorted(quintile.items(), key=lambda x: x[1]["ls_sharpe"], reverse=True):
        lines.append(
            f"| `{feat}` | {v['ls_sharpe']:+.3f} | "
            f"{v['q1_alpha']:+.2f} | {v['q2_alpha']:+.2f} | "
            f"{v['q3_alpha']:+.2f} | {v['q4_alpha']:+.2f} | "
            f"{v['q5_alpha']:+.2f} | {v['spread']:+.2f} | "
            f"{v['monotonic']:.2f} |"
        )

    lines += [
        "",
        "## 3. Conditional Marginal IC (given core template)",
        "",
        f"Core template: {', '.join(f'{n} {o} {v}' for n, o, v in CORE_FILTERS)}",
        "",
        "For stocks already passing the core template, which additional features "
        "predict forward alpha? Higher |cond IC| = more useful as an add-on filter.",
        "",
        "| Feature | Cond IC | Cond IC IR | Pct Positive | Months |",
        "|---------|---------|------------|-------------|--------|",
    ]

    for feat, v in sorted(conditional.items(), key=lambda x: abs(x[1]["cond_ic"]), reverse=True):
        lines.append(
            f"| `{feat}` | {v['cond_ic']:+.4f} | {v['cond_ic_ir']:+.3f} | "
            f"{v['cond_pct_pos']:.1%} | {v['cond_n_months']} |"
        )

    lines += [
        "",
        "## Interpretation Guide",
        "",
        "- **rank_by candidates**: Use features with high LS Sharpe + good monotonicity "
        "(top of table 2). These are good for `rank_by` in the screen DSL.",
        "- **Filter candidates**: Use features with high |IC mean| + consistent sign "
        "(pct positive far from 50%). Positive IC → filter for high values; "
        "negative IC → filter for low values.",
        "- **Add-on filters**: Table 3 shows what helps AFTER the core momentum template. "
        "These are the most actionable for improving existing screens.",
        "- **Avoid**: Features with IC near 0, low monotonicity, or inconsistent sign "
        "(pct positive near 50%) — these are noise.",
        "",
    ]

    out = "\n".join(lines)
    with open("feature_stats.md", "w") as f:
        f.write(out)
    print(f"Wrote feature_stats.md ({len(lines)} lines)")


def main():
    print("Computing features...")
    features = compute_all_features()
    print(f"Features: {features.shape}")

    print("Computing forward alpha...")
    fwd_alpha = load_forward_alpha()
    print(f"Forward alpha: {fwd_alpha.shape}")

    print("Computing rank IC...")
    rank_ic = compute_rank_ic(features, fwd_alpha)
    print(f"  {len(rank_ic)} features with sufficient data")

    print("Computing quintile long-short Sharpe...")
    quintile = compute_quintile_sharpe(features, fwd_alpha)
    print(f"  {len(quintile)} features with sufficient data")

    print("Computing conditional marginal IC (given core template)...")
    conditional = compute_conditional_marginal(features, fwd_alpha)
    print(f"  {len(conditional)} features with sufficient data")

    write_feature_stats(rank_ic, quintile, conditional)


if __name__ == "__main__":
    main()
