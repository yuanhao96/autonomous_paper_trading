#!/usr/bin/env python3
"""
Analyze results.jsonl — reusable script for AutoScreen research.

Usage:
    python analyze.py                  # full report
    python analyze.py --top 5          # top N screens
    python analyze.py --section feat   # specific section
    python analyze.py --screen "name"  # deep-dive one screen

Sections: summary, top, recent, risk, feat, thresh, regime, oos, stocks, overlap, corr, discard, all
"""
import argparse
import json
import sys
import numpy as np
import pandas as pd
from collections import Counter, defaultdict
from pathlib import Path

JSONL = Path(__file__).parent / "results.jsonl"
DETAILS_DIR = Path(__file__).parent / "data" / "details"
SHARPE_THRESHOLD = 0.3
MIN_TRAILING_MONTHS = 3


# ── Trailing / recency helpers ───────────────────────────────────────────────

def compute_trailing_sharpe(alphas, n_months):
    """Annualized Sharpe on the last n_months of a monthly alpha series.

    Returns NaN if fewer than MIN_TRAILING_MONTHS are available.
    """
    tail = alphas[-n_months:] if len(alphas) >= n_months else alphas
    if len(tail) < MIN_TRAILING_MONTHS:
        return float("nan")
    arr = np.array(tail)
    std = arr.std(ddof=1)
    if std == 0:
        return float("nan")
    return float(arr.mean() / std * np.sqrt(12))


def compute_alpha_slope(alphas):
    """OLS slope of monthly alpha over time, annualized.

    Positive = alpha improving, negative = decaying.
    Returns NaN if fewer than MIN_TRAILING_MONTHS months.
    """
    if len(alphas) < MIN_TRAILING_MONTHS:
        return float("nan")
    x = np.arange(len(alphas))
    slope = np.polyfit(x, alphas, 1)[0]
    return float(slope * 12)


def compute_recency_weighted_sharpe(alphas, half_life=12):
    """Exponentially-weighted annualized Sharpe (recent months count more).

    half_life: number of months for weight to halve (default 12).
    Returns NaN if fewer than MIN_TRAILING_MONTHS months.
    """
    n = len(alphas)
    if n < MIN_TRAILING_MONTHS:
        return float("nan")
    arr = np.array(alphas)
    decay = np.log(2) / half_life
    weights = np.exp(decay * np.arange(n))  # oldest=smallest, newest=largest
    w_sum = weights.sum()
    w_mean = (weights * arr).sum() / w_sum
    w_var = (weights * (arr - w_mean) ** 2).sum() / w_sum
    w_std = np.sqrt(w_var)
    if w_std == 0:
        return float("nan")
    return float(w_mean / w_std * np.sqrt(12))


def compute_max_alpha_drawdown(alphas):
    """Worst cumulative peak-to-trough run of negative alpha.

    Returns a non-positive float (0 = no drawdown). NaN if empty.
    """
    if len(alphas) < 1:
        return float("nan")
    cumulative = np.cumsum(alphas)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = cumulative - running_max
    return float(drawdowns.min())


def compute_longest_losing_streak(alphas):
    """Max consecutive months with alpha < 0. Returns 0 if all positive."""
    if not alphas:
        return 0
    max_streak = 0
    current = 0
    for a in alphas:
        if a < 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def compute_alpha_stability(alphas, window=3):
    """Fraction of rolling `window`-month windows with positive mean alpha.

    Higher = more consistent. Returns NaN if fewer than `window` months.
    """
    n = len(alphas)
    if n < window:
        return float("nan")
    arr = np.array(alphas)
    n_windows = n - window + 1
    positive = 0
    for i in range(n_windows):
        if arr[i:i + window].mean() > 0:
            positive += 1
    return float(positive / n_windows)


def classify_verdict(full_sharpe, trail_12m_sharpe):
    """Three-way verdict: KEEP, STALE, or DISCARD."""
    if full_sharpe < SHARPE_THRESHOLD:
        return "DISCARD"
    if np.isnan(trail_12m_sharpe):
        return "KEEP"
    if trail_12m_sharpe < 0.0:
        return "STALE"
    return "KEEP"


# ── Data loading ─────────────────────────────────────────────────────────────

def load_results(path=JSONL):
    results = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def load_stock_details(idx):
    """Load archived per-stock details for a result by index.

    Returns list of {"month": ..., "stocks": {...}} dicts.
    Falls back to monthly_details["stocks"] for old-format results.
    """
    archive = DETAILS_DIR / f"{idx}.json"
    if archive.exists():
        with open(archive) as f:
            return json.load(f)
    return None


def get_stock_details(idx, result):
    """Get per-stock details from archive or inline (old format)."""
    details = load_stock_details(idx)
    if details is not None:
        return details
    # Old format: stocks embedded in monthly_details
    md = result.get("monthly_details", [])
    if md and "stocks" in md[0]:
        return [{"month": m["month"], "stocks": m["stocks"]} for m in md]
    return []


def build_df(results):
    rows = []
    for i, r in enumerate(results):
        alphas = [md["alpha"] for md in r.get("monthly_details", [])]
        trail_12m = compute_trailing_sharpe(alphas, 12)
        trail_6m = compute_trailing_sharpe(alphas, 6)
        slope = compute_alpha_slope(alphas)
        rw_sharpe = compute_recency_weighted_sharpe(alphas)
        max_dd = compute_max_alpha_drawdown(alphas)
        lose_streak = compute_longest_losing_streak(alphas)
        stability = compute_alpha_stability(alphas)
        row = {
            "idx": i,
            "name": r["name"],
            "hypothesis": r.get("hypothesis", ""),
            "sharpe": r["sharpe"],
            "trail_12m_sharpe": trail_12m,
            "trail_6m_sharpe": trail_6m,
            "alpha_slope": slope,
            "rw_sharpe": rw_sharpe,
            "max_dd": max_dd,
            "lose_streak": lose_streak,
            "stability": stability,
            "alpha_monthly_mean": r["alpha_monthly_mean"],
            "alpha_annual": r["alpha_annual"],
            "win_rate": r["win_rate"],
            "n_filters": len(r.get("filters", [])),
            "n_months": r.get("n_months", len(r.get("monthly_details", []))),
            "n_avg_stocks": r.get("n_avg_stocks", 0),
            "port_total_return": r.get("port_total_return", 0),
            "spy_total_return": r.get("spy_total_return", 0),
            "holding_days": r.get("holding_days", 21),
            "rank_by": r.get("rank_by") or "alpha",
            "uses_score": bool(r.get("score")),
            "filters_json": json.dumps(r.get("filters", []), sort_keys=True),
            "status": classify_verdict(r["sharpe"], trail_12m),
            # IS/OOS fields (present when split_date was used)
            "sharpe_is": r.get("sharpe_is", float("nan")),
            "sharpe_oos": r.get("sharpe_oos", float("nan")),
            "sharpe_ratio": r.get("sharpe_ratio", float("nan")),
        }
        rows.append(row)
    return pd.DataFrame(rows)


# ── Sections ─────────────────────────────────────────────────────────────────

def section_summary(df, results):
    n_keep = (df["status"] == "KEEP").sum()
    n_stale = (df["status"] == "STALE").sum()
    n_disc = (df["status"] == "DISCARD").sum()
    n_unique = df["filters_json"].nunique()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total screens:  {len(df)}")
    print(f"  KEEP:           {n_keep}")
    print(f"  STALE:          {n_stale}")
    print(f"  DISCARD:        {n_disc}")
    print(f"  Unique filters: {n_unique}")
    print(f"  Best Sharpe:    {df['sharpe'].max():.3f}  ({df.loc[df['sharpe'].idxmax(), 'name']})")
    print(f"  Worst Sharpe:   {df['sharpe'].min():.3f}")
    print(f"  Mean Sharpe:    {df['sharpe'].mean():.3f} (all) / {df.loc[df['status']=='KEEP', 'sharpe'].mean():.3f} (KEEP)")
    print(f"  Best annual α:  {df['alpha_annual'].max():.2%}")
    print(f"  Best win rate:  {df['win_rate'].max():.1%}")

    # Breakdown by holding period
    hd_counts = df.groupby("holding_days").agg(
        n=("sharpe", "size"), keep=("status", lambda s: (s == "KEEP").sum()),
        avg_sharpe=("sharpe", "mean"),
    )
    if len(hd_counts) > 1 or (len(hd_counts) == 1 and hd_counts.index[0] != 21):
        print("\n  By holding period:")
        print(f"    {'Days':>5} {'Total':>5} {'KEEP':>5} {'Avg Sharpe':>11}")
        for hd, row in hd_counts.iterrows():
            print(f"    {hd:>5} {int(row['n']):>5} {int(row['keep']):>5} {row['avg_sharpe']:>11.3f}")

    # Breakdown by rank_by
    rb_counts = df.groupby("rank_by").agg(
        n=("sharpe", "size"), keep=("status", lambda s: (s == "KEEP").sum()),
        avg_sharpe=("sharpe", "mean"),
    )
    if len(rb_counts) > 1 or (len(rb_counts) == 1 and rb_counts.index[0] != "alpha"):
        print("\n  By rank_by:")
        print(f"    {'Feature':<20} {'Total':>5} {'KEEP':>5} {'Avg Sharpe':>11}")
        for rb, row in rb_counts.iterrows():
            print(f"    {rb:<20} {int(row['n']):>5} {int(row['keep']):>5} {row['avg_sharpe']:>11.3f}")

    # Composite score screens
    n_score = df["uses_score"].sum()
    if n_score > 0:
        score_df = df[df["uses_score"]]
        score_keep = (score_df["status"] == "KEEP").sum()
        print(f"\n  Composite score screens: {n_score} "
              f"(KEEP: {score_keep}, Avg Sharpe: {score_df['sharpe'].mean():.3f})")


def section_top(df, results, n=10):
    print("=" * 60)
    print(f"TOP {n} SCREENS BY SHARPE")
    print("=" * 60)
    cols = [
        "name", "sharpe", "trail_12m_sharpe", "alpha_annual",
        "win_rate", "n_months", "n_avg_stocks", "holding_days",
        "rank_by", "status",
    ]
    top = df.nlargest(n, "sharpe")[cols]
    print(top.to_string(index=False, na_rep="N/A"))

    print(f"\nBOTTOM {min(n, len(df))} SCREENS BY SHARPE")
    print("-" * 60)
    bot = df.nsmallest(min(n, len(df)), "sharpe")[cols]
    print(bot.to_string(index=False, na_rep="N/A"))


def section_recent(df, results):
    """Trailing-window metrics for screens with full-period Sharpe >= threshold."""
    print("=" * 60)
    print(f"RECENCY ANALYSIS (full-period Sharpe >= {SHARPE_THRESHOLD})")
    print("=" * 60)
    eligible = df[df["sharpe"] >= SHARPE_THRESHOLD].copy()
    if eligible.empty:
        print("  No screens with full-period Sharpe >= 0.3.")
        return

    eligible = eligible.sort_values("trail_12m_sharpe", ascending=False)
    cols = [
        "name", "sharpe", "trail_12m_sharpe", "trail_6m_sharpe",
        "alpha_slope", "rw_sharpe", "status",
    ]
    print(eligible[cols].to_string(index=False, na_rep="N/A"))

    n_decaying = (eligible["trail_12m_sharpe"] < 0).sum()
    n_stale = (eligible["status"] == "STALE").sum()
    if n_decaying > 0:
        print(f"\n  DECAYING (trail-12m Sharpe < 0): {n_decaying}")
        print(f"  STALE verdict: {n_stale}")
        decaying = eligible[eligible["trail_12m_sharpe"] < 0]
        print("\n  Decaying screens:")
        for _, row in decaying.iterrows():
            print(
                f"    {row['name'][:40]:<42}"
                f"full={row['sharpe']:.3f}  "
                f"trail12={row['trail_12m_sharpe']:.3f}  "
                f"slope={row['alpha_slope']:.4f}"
            )


def section_risk(df, results):
    """Risk and robustness metrics for KEEP screens."""
    print("=" * 60)
    print("RISK & ROBUSTNESS (KEEP screens)")
    print("=" * 60)
    keep = df[df["status"] == "KEEP"].copy()
    if keep.empty:
        print("  No KEEP screens.")
        return

    cols = [
        "name", "sharpe", "max_dd", "lose_streak", "stability",
    ]
    keep = keep.sort_values("stability", ascending=False)
    print(keep[cols].to_string(index=False, na_rep="N/A"))

    # Summary stats
    print(f"\n  Avg max drawdown:      {keep['max_dd'].mean():.4f}")
    print(f"  Avg longest losing streak: {keep['lose_streak'].mean():.1f} months")
    print(f"  Avg alpha stability:   {keep['stability'].mean():.2f}")


def section_features(df, results):
    print("=" * 60)
    print("FEATURE USAGE: KEEP vs DISCARD (with recency)")
    print("=" * 60)
    keep_feats, disc_feats = Counter(), Counter()
    for r in results:
        bucket = keep_feats if r["sharpe"] >= SHARPE_THRESHOLD else disc_feats
        for filt in r.get("filters", []):
            bucket[filt["feature"]] += 1

    # Build per-result feature sets for recency lookups
    result_feats = []
    for r in results:
        result_feats.append({f["feature"] for f in r.get("filters", [])})

    all_feats = sorted(set(list(keep_feats) + list(disc_feats)))
    print(
        f"\n  {'Feature':<25} {'KEEP':>5} {'DISC':>5}"
        f" {'Keep%':>6}  {'Shp w/':>7} {'w/o':>7}"
        f" {'Rcnt%':>6} {'Trend':>7}"
    )
    for feat in all_feats:
        k, d = keep_feats.get(feat, 0), disc_feats.get(feat, 0)
        pct = k / (k + d) * 100 if (k + d) else 0
        # Rows in df that use this feature
        mask = df.index.map(lambda i: feat in result_feats[i])
        with_df = df[mask]
        wo_df = df[~mask]
        w_avg = with_df["sharpe"].mean() if len(with_df) else float("nan")
        wo_avg = wo_df["sharpe"].mean() if len(wo_df) else float("nan")
        # Recent hit rate: among KEEP screens using this feature,
        # fraction with positive trailing-12m alpha
        keep_with = with_df[with_df["sharpe"] >= SHARPE_THRESHOLD]
        if len(keep_with) > 0:
            valid_trail = keep_with["trail_12m_sharpe"].dropna()
            recent_pct = (
                (valid_trail >= 0).mean() * 100 if len(valid_trail) else float("nan")
            )
        else:
            recent_pct = float("nan")
        # Trend direction: mean alpha_slope of screens using this feature
        slopes = with_df["alpha_slope"].dropna()
        trend = slopes.mean() if len(slopes) else float("nan")
        trend_str = f"{trend:>7.4f}" if not np.isnan(trend) else "    N/A"
        recent_str = f"{recent_pct:>5.1f}%" if not np.isnan(recent_pct) else "   N/A"
        print(
            f"  {feat:<25} {k:>5} {d:>5}"
            f" {pct:>5.1f}%  {w_avg:>7.3f} {wo_avg:>7.3f}"
            f" {recent_str} {trend_str}"
        )


def section_thresholds(df, results):
    print("=" * 60)
    print("THRESHOLD ANALYSIS (KEEP screens)")
    print("=" * 60)
    feat_entries = defaultdict(list)
    for r in results:
        if r["sharpe"] >= SHARPE_THRESHOLD:
            for filt in r.get("filters", []):
                feat_entries[filt["feature"]].append({
                    "op": filt["op"], "value": filt["value"],
                    "sharpe": r["sharpe"], "name": r["name"][:45],
                })

    for feat in sorted(feat_entries):
        entries = sorted(feat_entries[feat], key=lambda e: -e["sharpe"])
        print(f"\n  {feat}:")
        for e in entries[:10]:
            print(f"    {e['op']:>8} {str(e['value']):<18} Sharpe={e['sharpe']:.3f}  {e['name']}")


def tag_regime(spy_return):
    """Classify a month as BULL, BEAR, or FLAT based on SPY return."""
    if spy_return > 0.02:
        return "BULL"
    if spy_return < -0.02:
        return "BEAR"
    return "FLAT"


def compute_regime_robustness(regime_alphas):
    """Fraction of regimes (BULL/BEAR/FLAT) with positive mean alpha."""
    regimes_with_data = 0
    regimes_positive = 0
    for regime in ("BULL", "BEAR", "FLAT"):
        vals = regime_alphas.get(regime, [])
        if vals:
            regimes_with_data += 1
            if np.mean(vals) > 0:
                regimes_positive += 1
    if regimes_with_data == 0:
        return float("nan")
    return float(regimes_positive / regimes_with_data)


REGIME_LABELS = [
    "quiet_bull", "volatile_bull", "quiet_bear", "volatile_bear",
]


def compute_regime_robustness_4(regime_stats):
    """Fraction of 4-label regimes with positive mean alpha."""
    with_data = 0
    positive = 0
    for label in REGIME_LABELS:
        stats = regime_stats.get(label)
        if stats and stats["n_months"] > 0:
            with_data += 1
            if stats["alpha_mean"] > 0:
                positive += 1
    if with_data == 0:
        return float("nan")
    return float(positive / with_data)


def section_regime(df, results):
    print("=" * 60)
    print("REGIME ANALYSIS (KEEP screens)")
    print("=" * 60)
    keep = [r for r in results if r["sharpe"] >= SHARPE_THRESHOLD]
    if not keep:
        print("  No KEEP screens.")
        return

    # Check if results have 4-label regime_stats (new format)
    has_regime_stats = any(r.get("regime_stats") for r in keep)

    if has_regime_stats:
        # Aggregate across all KEEP screens with regime_stats
        regime_all = defaultdict(list)
        for r in keep:
            for label, stats in r.get("regime_stats", {}).items():
                regime_all[label].extend(
                    [stats["alpha_mean"]] * stats["n_months"]
                )

        print("\n  Aggregate (all KEEP screens, 4-label regime):")
        hdr = f"    {'Regime':<16} {'Mean α':>8} {'Win%':>6} {'N':>6}"
        print(hdr)
        for label in REGIME_LABELS:
            arr = np.array(regime_all.get(label, []))
            if len(arr) == 0:
                continue
            print(
                f"    {label:<16} {arr.mean():>8.4f}"
                f" {(arr > 0).mean() * 100:>5.1f}% {len(arr):>6}"
            )

        # Per-screen regime breakdown (top 15)
        top_keep = sorted(
            [r for r in keep if r.get("regime_stats")],
            key=lambda r: r["sharpe"], reverse=True,
        )[:15]
        if top_keep:
            print(f"\n  Per-screen regime stats (top {len(top_keep)}):")
            hdr = (
                f"    {'Screen':<35} {'Sharpe':>6}"
                f"  {'Q.Bull':>7} {'V.Bull':>7}"
                f" {'Q.Bear':>7} {'V.Bear':>7}"
                f" {'Robust':>6}"
            )
            print(hdr)
            for r in top_keep:
                rs = r["regime_stats"]
                robustness = compute_regime_robustness_4(rs)
                parts = [
                    f"    {r['name'][:35]:<35} {r['sharpe']:>6.3f}"
                ]
                for label in REGIME_LABELS:
                    s = rs.get(label)
                    if s and s["n_months"] > 0:
                        parts.append(f"  {s['alpha_mean']:>7.4f}")
                    else:
                        parts.append(f"  {'N/A':>7}")
                parts.append(f" {robustness:>6.2f}")
                print("".join(parts))
    else:
        # Fallback: BULL/BEAR/FLAT from monthly SPY return
        regime_all = defaultdict(list)
        for r in keep:
            for md in r.get("monthly_details", []):
                regime = tag_regime(md["spy_return"])
                regime_all[regime].append(md["alpha"])

        print("\n  Aggregate (all KEEP, monthly SPY regime):")
        hdr = f"    {'Regime':<6} {'Mean α':>8} {'Win%':>6} {'N':>6}"
        print(hdr)
        for regime in ("BULL", "BEAR", "FLAT"):
            arr = np.array(regime_all.get(regime, []))
            if len(arr) == 0:
                continue
            print(
                f"    {regime:<6} {arr.mean():>8.4f}"
                f" {(arr > 0).mean() * 100:>5.1f}%"
                f" {len(arr):>6}"
            )

    # Year-by-year breakdown (always shown)
    year_alphas = defaultdict(list)
    for r in keep:
        for md in r.get("monthly_details", []):
            year_alphas[md["month"][:4]].append(md["alpha"])

    print("\n  Year-by-year:")
    print(
        f"    {'Year':>6} {'Mean α':>8} {'Median':>8}"
        f" {'Std':>8} {'N':>5} {'Win%':>6}"
    )
    for yr in sorted(year_alphas):
        arr = np.array(year_alphas[yr])
        print(
            f"    {yr:>6} {arr.mean():>8.4f}"
            f" {np.median(arr):>8.4f}"
            f" {arr.std():>8.4f} {len(arr):>5}"
            f" {(arr > 0).mean() * 100:>5.1f}%"
        )


def section_oos(df, results):
    """IS vs OOS performance analysis."""
    print("=" * 60)
    print("OUT-OF-SAMPLE ANALYSIS")
    print("=" * 60)
    has_oos = df["sharpe_oos"].notna().any()
    if not has_oos:
        print("  No IS/OOS data. Run with --split-date to enable.")
        return

    oos_df = df[df["sharpe_oos"].notna()].copy()
    if oos_df.empty:
        print("  No screens with OOS data.")
        return

    # Summary stats
    is_mean = oos_df["sharpe_is"].mean()
    oos_mean = oos_df["sharpe_oos"].mean()
    shrinkage = is_mean - oos_mean if is_mean != 0 else 0
    print(f"\n  Screens with OOS data: {len(oos_df)}")
    print(f"  Mean IS Sharpe:  {is_mean:.3f}")
    print(f"  Mean OOS Sharpe: {oos_mean:.3f}")
    print(f"  Mean shrinkage:  {shrinkage:.3f}")

    # Per-screen IS vs OOS table
    cols = [
        "name", "sharpe", "sharpe_is", "sharpe_oos",
        "sharpe_ratio", "status",
    ]
    sorted_df = oos_df.sort_values("sharpe_oos", ascending=False)
    print(f"\n  {'IS vs OOS':}")
    print(sorted_df[cols].to_string(index=False, na_rep="N/A"))

    # Overfit warnings
    overfit = oos_df[oos_df["sharpe_ratio"] > 3.0]
    if len(overfit) > 0:
        print(f"\n  OVERFIT WARNING (IS/OOS ratio > 3.0): "
              f"{len(overfit)} screens")
        for _, row in overfit.iterrows():
            ratio_str = (
                f"{row['sharpe_ratio']:.1f}"
                if np.isfinite(row["sharpe_ratio"]) else "inf"
            )
            print(
                f"    {row['name'][:40]:<42}"
                f"IS={row['sharpe_is']:.3f}  "
                f"OOS={row['sharpe_oos']:.3f}  "
                f"ratio={ratio_str}"
            )


def section_stocks(df, results):
    print("=" * 60)
    print("STOCK-LEVEL ANALYSIS (KEEP screens)")
    print("=" * 60)
    stock_rets = defaultdict(list)
    stock_counts = Counter()
    for i, r in enumerate(results):
        if r["sharpe"] >= SHARPE_THRESHOLD:
            for md in get_stock_details(i, r):
                for ticker, ret in md.get("stocks", {}).items():
                    stock_rets[ticker].append(ret)
                    stock_counts[ticker] += 1

    print(f"\n  Unique stocks: {len(stock_counts)}")
    print("\n  Top 20 most frequent:")
    print(f"    {'Ticker':<7} {'Count':>5} {'Mean Ret':>9} {'Std':>8}")
    for t, c in stock_counts.most_common(20):
        arr = np.array(stock_rets[t])
        print(f"    {t:<7} {c:>5} {arr.mean():>9.4f} {arr.std():>8.4f}")

    # Best/worst by mean return (min 5 appearances)
    qualified = [(t, np.mean(stock_rets[t]), len(stock_rets[t]), np.std(stock_rets[t]))
                 for t in stock_rets if len(stock_rets[t]) >= 5]
    qualified.sort(key=lambda x: -x[1])

    print("\n  Top 15 alpha contributors (min 5 picks):")
    print(f"    {'Ticker':<7} {'Mean':>8} {'N':>5} {'Std':>8}")
    for t, m, n, s in qualified[:15]:
        print(f"    {t:<7} {m:>8.4f} {n:>5} {s:>8.4f}")

    print("\n  Bottom 15 alpha destroyers:")
    for t, m, n, s in qualified[-15:]:
        print(f"    {t:<7} {m:>8.4f} {n:>5} {s:>8.4f}")


def section_overlap(df, results):
    print("=" * 60)
    print("SCREEN OVERLAP")
    print("=" * 60)
    keep = [r for r in results if r["sharpe"] >= SHARPE_THRESHOLD]
    if len(keep) < 2:
        print("  Need >= 2 KEEP screens for overlap analysis.")
        return

    month_tickers = defaultdict(lambda: defaultdict(int))
    for i, r in enumerate(results):
        if r["sharpe"] < SHARPE_THRESHOLD:
            continue
        for md in get_stock_details(i, r):
            for t in md.get("stocks", {}):
                month_tickers[md["month"]][t] += 1

    overlaps = []
    for m, tickers in month_tickers.items():
        multi = sum(1 for c in tickers.values() if c > 1)
        overlaps.append(multi / len(tickers) if tickers else 0)

    print(f"\n  Avg fraction of stocks in >1 screen/month: {np.mean(overlaps):.1%}")
    print(f"  Min: {min(overlaps):.1%}  Max: {max(overlaps):.1%}")


def section_correlation(df, results, max_screens=10):
    print("=" * 60)
    print("ALPHA CORRELATION (unique KEEP screens, grouped by holding period)")
    print("=" * 60)
    seen, unique = set(), []
    for r in results:
        if r["sharpe"] < SHARPE_THRESHOLD:
            continue
        key = json.dumps(sorted(json.dumps(f, sort_keys=True) for f in r.get("filters", [])))
        hd = r.get("holding_days", 21)
        rb = r.get("rank_by") or "alpha"
        dedup_key = f"{key}|{hd}|{rb}"
        if dedup_key not in seen:
            seen.add(dedup_key)
            unique.append(r)

    # Cap to top screens by Sharpe to avoid O(n²) blowup
    if len(unique) > max_screens:
        unique = sorted(unique, key=lambda r: r["sharpe"], reverse=True)[:max_screens]

    print(f"\n  Unique KEEP screens: {len(unique)} (capped to top {max_screens})")
    if len(unique) < 2:
        return

    # Group by holding_days — only correlate screens with same period
    by_hd = defaultdict(list)
    for r in unique:
        by_hd[r.get("holding_days", 21)].append(r)

    for hd in sorted(by_hd):
        group = by_hd[hd]
        if len(group) < 2:
            continue
        print(f"\n  --- holding_days={hd} ({len(group)} screens) ---")

        series = {}
        for r in group:
            s = {md["month"]: md["alpha"] for md in r.get("monthly_details", [])}
            series[r["name"][:35]] = s

        names = list(series)
        print(f"  {'Screen A':>35}  {'Screen B':>35}  {'Corr':>6}")
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                common = sorted(set(series[names[i]]) & set(series[names[j]]))
                if len(common) < 10:
                    continue
                a = [series[names[i]][m] for m in common]
                b = [series[names[j]][m] for m in common]
                corr = np.corrcoef(a, b)[0, 1]
                print(f"  {names[i]:>35}  {names[j]:>35}  {corr:>6.3f}")


def section_discard(df, results, max_show=10):
    discards = [r for r in results if r["sharpe"] < SHARPE_THRESHOLD]
    print("=" * 60)
    print(f"DISCARD SCREENS — WHAT FAILED (showing last {max_show} of {len(discards)})")
    print("=" * 60)
    for r in discards[-max_show:]:
        print(f"\n  {r['name']} (Sharpe={r['sharpe']:.3f})")
        print(f"    Hypothesis: {r.get('hypothesis', 'n/a')}")
        for filt in r.get("filters", []):
            print(f"    {filt['feature']:>20} {filt['op']} {filt['value']}")


def section_screen_detail(results, name_query):
    """Deep-dive into a single screen by name substring."""
    matches = [(i, r) for i, r in enumerate(results)
               if name_query.lower() in r["name"].lower()]
    if not matches:
        print(f"No screen matching '{name_query}'")
        return
    idx, r = matches[0]
    print("=" * 60)
    print(f"SCREEN: {r['name']}")
    print("=" * 60)
    print(f"  Hypothesis: {r.get('hypothesis', 'n/a')}")
    print(f"  Sharpe: {r['sharpe']:.3f}  |  Annual α: {r['alpha_annual']:.2%}  |  Win rate: {r['win_rate']:.1%}")
    print(f"  Months: {r.get('n_months', '?')}  |  Avg stocks: {r.get('n_avg_stocks', '?')}")
    print(f"  Verdict: {r.get('verdict', 'KEEP' if r['sharpe'] >= SHARPE_THRESHOLD else 'DISCARD')}")
    print("\n  Filters:")
    for filt in r.get("filters", []):
        print(f"    {filt['feature']:>20} {filt['op']} {filt['value']}")

    # Per-year breakdown
    year_data = defaultdict(list)
    for md in r.get("monthly_details", []):
        year_data[md["month"][:4]].append(md)

    print(f"\n  {'Year':>6} {'Mean α':>8} {'Port Ret':>9} {'SPY Ret':>8} {'Win%':>6} {'Months':>7}")
    for yr in sorted(year_data):
        alphas = [m["alpha"] for m in year_data[yr]]
        ports = [m["port_return"] for m in year_data[yr]]
        spys = [m["spy_return"] for m in year_data[yr]]
        arr = np.array(alphas)
        print(f"  {yr:>6} {arr.mean():>8.4f} {np.mean(ports):>9.4f} {np.mean(spys):>8.4f} {(arr>0).mean()*100:>5.1f}% {len(arr):>7}")

    # Top/bottom months
    details = sorted(r.get("monthly_details", []), key=lambda m: m["alpha"])
    # Build month→n_stocks lookup from stock_details archive or inline
    stock_data = get_stock_details(idx, r)
    month_n_stocks = {md["month"]: len(md.get("stocks", {})) for md in stock_data}
    print("\n  Best 5 months:")
    for md in details[-5:][::-1]:
        n_stocks = md.get("n_stocks", month_n_stocks.get(md["month"], 0))
        print(f"    {md['month']}  α={md['alpha']:>+.4f}  port={md['port_return']:>+.4f}  spy={md['spy_return']:>+.4f}  stocks={n_stocks}")
    print("\n  Worst 5 months:")
    for md in details[:5]:
        n_stocks = md.get("n_stocks", month_n_stocks.get(md["month"], 0))
        print(f"    {md['month']}  α={md['alpha']:>+.4f}  port={md['port_return']:>+.4f}  spy={md['spy_return']:>+.4f}  stocks={n_stocks}")


# ── Main ─────────────────────────────────────────────────────────────────────

SECTIONS = {
    "summary": section_summary,
    "top": section_top,
    "recent": section_recent,
    "risk": section_risk,
    "feat": section_features,
    "thresh": section_thresholds,
    "regime": section_regime,
    "oos": section_oos,
    "stocks": section_stocks,
    "overlap": section_overlap,
    "corr": section_correlation,
    "discard": section_discard,
}


def main():
    parser = argparse.ArgumentParser(description="Analyze AutoScreen results")
    parser.add_argument("--top", type=int, default=10, help="Number of top/bottom screens to show")
    parser.add_argument("--section", type=str, default="all",
                        help=f"Section to show: {', '.join(SECTIONS.keys())}, all")
    parser.add_argument("--screen", type=str, default=None,
                        help="Deep-dive a screen by name substring")
    parser.add_argument("--file", type=str, default=str(JSONL), help="Path to results.jsonl")
    args = parser.parse_args()

    results = load_results(args.file)
    df = build_df(results)

    if args.screen:
        section_screen_detail(results, args.screen)
        return

    if args.section == "all":
        for name, fn in SECTIONS.items():
            if name == "top":
                fn(df, results, n=args.top)
            else:
                fn(df, results)
            print()
    elif args.section in SECTIONS:
        fn = SECTIONS[args.section]
        if args.section == "top":
            fn(df, results, n=args.top)
        else:
            fn(df, results)
    else:
        print(f"Unknown section: {args.section}")
        print(f"Available: {', '.join(SECTIONS.keys())}, all")
        sys.exit(1)


if __name__ == "__main__":
    main()
