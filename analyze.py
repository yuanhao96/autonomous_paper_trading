#!/usr/bin/env python3
"""
Analyze results.jsonl — reusable script for AutoScreen research.

Usage:
    python analyze.py                  # full report
    python analyze.py --top 5          # top N screens
    python analyze.py --section feat   # specific section
    python analyze.py --screen "name"  # deep-dive one screen

Sections: summary, top, feat, thresh, regime, stocks, overlap, corr, discard, all
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
        rows.append({
            "idx": i,
            "name": r["name"],
            "hypothesis": r.get("hypothesis", ""),
            "sharpe": r["sharpe"],
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
            "status": "KEEP" if r["sharpe"] >= SHARPE_THRESHOLD else "DISCARD",
        })
    return pd.DataFrame(rows)


# ── Sections ─────────────────────────────────────────────────────────────────

def section_summary(df, results):
    n_keep = (df["status"] == "KEEP").sum()
    n_disc = (df["status"] == "DISCARD").sum()
    n_unique = df["filters_json"].nunique()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total screens:  {len(df)}")
    print(f"  KEEP (Sharpe >= {SHARPE_THRESHOLD}):  {n_keep}")
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
    cols = ["name", "sharpe", "alpha_annual", "win_rate", "n_months", "n_avg_stocks", "holding_days", "rank_by", "status"]
    top = df.nlargest(n, "sharpe")[cols]
    print(top.to_string(index=False))

    print(f"\nBOTTOM {min(n, len(df))} SCREENS BY SHARPE")
    print("-" * 60)
    bot = df.nsmallest(min(n, len(df)), "sharpe")[cols]
    print(bot.to_string(index=False))


def section_features(df, results):
    print("=" * 60)
    print("FEATURE USAGE: KEEP vs DISCARD")
    print("=" * 60)
    keep_feats, disc_feats = Counter(), Counter()
    for r in results:
        bucket = keep_feats if r["sharpe"] >= SHARPE_THRESHOLD else disc_feats
        for filt in r.get("filters", []):
            bucket[filt["feature"]] += 1

    all_feats = sorted(set(list(keep_feats) + list(disc_feats)))
    print(f"\n  {'Feature':<25} {'KEEP':>5} {'DISC':>5} {'Keep%':>6}  {'Avg Sharpe w/':>14} {'w/o':>7}")
    for feat in all_feats:
        k, d = keep_feats.get(feat, 0), disc_feats.get(feat, 0)
        pct = k / (k + d) * 100 if (k + d) else 0
        # avg sharpe with/without feature
        with_s = [r["sharpe"] for r in results if any(f["feature"] == feat for f in r.get("filters", []))]
        wo_s = [r["sharpe"] for r in results if not any(f["feature"] == feat for f in r.get("filters", []))]
        w_avg = np.mean(with_s) if with_s else float("nan")
        wo_avg = np.mean(wo_s) if wo_s else float("nan")
        print(f"  {feat:<25} {k:>5} {d:>5} {pct:>5.1f}%  {w_avg:>14.3f} {wo_avg:>7.3f}")


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


def section_regime(df, results):
    print("=" * 60)
    print("REGIME: ALPHA BY YEAR (KEEP screens)")
    print("=" * 60)
    year_alphas = defaultdict(list)
    for r in results:
        if r["sharpe"] >= SHARPE_THRESHOLD:
            for md in r.get("monthly_details", []):
                year_alphas[md["month"][:4]].append(md["alpha"])

    print(f"\n  {'Year':>6} {'Mean α':>8} {'Median':>8} {'Std':>8} {'N':>5} {'Win%':>6}")
    for yr in sorted(year_alphas):
        arr = np.array(year_alphas[yr])
        print(f"  {yr:>6} {arr.mean():>8.4f} {np.median(arr):>8.4f} {arr.std():>8.4f} {len(arr):>5} {(arr>0).mean()*100:>5.1f}%")

    # Best screen half-life decay
    best_r = max(results, key=lambda r: r["sharpe"])
    alphas = [md["alpha"] for md in best_r.get("monthly_details", [])]
    if alphas:
        mid = len(alphas) // 2
        h1, h2 = np.array(alphas[:mid]), np.array(alphas[mid:])
        print(f"\n  Best screen decay ({best_r['name'][:40]}):")
        print(f"    First half:  mean={h1.mean():.4f}  std={h1.std():.4f}")
        print(f"    Second half: mean={h2.mean():.4f}  std={h2.std():.4f}")


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
    "feat": section_features,
    "thresh": section_thresholds,
    "regime": section_regime,
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
