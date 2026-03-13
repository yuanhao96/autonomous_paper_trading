"""Screen mode: run top screens on today's market and generate reports."""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

from screen import _apply_filters, _rank_and_select, compute_all_features
from run import _claude_call

RESULTS_PATH = Path("results.jsonl")
DETAILS_DIR = Path("data/details")
REPORTS_DIR = Path("reports")
SHARPE_THRESHOLD = 0.3


def load_keep_screens(results_path: Path = RESULTS_PATH) -> list[dict]:
    """Load KEEP screens from results.jsonl, sorted by Sharpe descending.

    Each result gets an 'idx' field (0-based line number) for stock_details lookup.
    """
    keeps = []
    with open(results_path) as f:
        for idx, line in enumerate(f):
            r = json.loads(line.strip())
            if r["sharpe"] >= SHARPE_THRESHOLD:
                r["idx"] = idx
                keeps.append(r)
    keeps.sort(key=lambda r: r["sharpe"], reverse=True)
    return keeps


def _load_last_stocks(idx: int, details_dir: Path = DETAILS_DIR) -> set[str]:
    """Load the last period's stock set from archived details."""
    archive = details_dir / f"{idx}.json"
    if not archive.exists():
        return set()
    with open(archive) as f:
        periods = json.load(f)
    if not periods:
        return set()
    return set(periods[-1].get("stocks", {}).keys())


def _jaccard(a: set, b: set) -> float:
    """Jaccard similarity: |intersection| / |union|. 0 if both empty."""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def select_diverse_screens(
    screens: list[dict], k: int = 3,
    details_dir: Path = DETAILS_DIR, overlap_penalty: float = 0.5,
) -> list[dict]:
    """Greedy selection: best Sharpe first, then maximize Sharpe - penalty * overlap.

    Args:
        screens: KEEP screens sorted by Sharpe desc (from load_keep_screens).
        k: Number of screens to select.
        details_dir: Path to archived stock details.
        overlap_penalty: Weight for Jaccard overlap penalty (0-1).

    Returns:
        List of k selected screens (or fewer if not enough available).
    """
    if len(screens) <= k:
        return list(screens)

    # Pre-load stock sets
    stock_sets = {
        s["idx"]: _load_last_stocks(s["idx"], details_dir)
        for s in screens
    }

    # Normalize Sharpe to [0, 1] for fair comparison with overlap
    max_sharpe = screens[0]["sharpe"]
    min_sharpe = screens[-1]["sharpe"]
    sharpe_range = max_sharpe - min_sharpe if max_sharpe > min_sharpe else 1.0

    selected = [screens[0]]  # Best Sharpe always first
    remaining = list(screens[1:])

    while len(selected) < k and remaining:
        best_score = -float("inf")
        best_idx = 0
        for i, cand in enumerate(remaining):
            norm_sharpe = (cand["sharpe"] - min_sharpe) / sharpe_range
            max_overlap = max(
                _jaccard(stock_sets[cand["idx"]], stock_sets[s["idx"]])
                for s in selected
            )
            score = norm_sharpe - overlap_penalty * max_overlap
            if score > best_score:
                best_score = score
                best_idx = i
        selected.append(remaining.pop(best_idx))

    return selected


def run_screen_today(
    screen_def: dict, features: pd.DataFrame,
) -> dict:
    """Run a screen on the most recent date in features.

    Returns dict with:
        date: str — the screening date
        tickers: list[str] — selected tickers in rank order
        ticker_features: dict[str, dict[str, float]] — feature values per ticker
    """
    last_date = features.index[-1]
    passing = _apply_filters(features, screen_def["filters"], last_date)
    selected = _rank_and_select(passing, features, last_date, screen_def)

    # Gather feature values for selected tickers
    feat_names = features.columns.get_level_values(0).unique()
    ticker_features = {}
    for ticker in selected:
        vals = {}
        for feat in feat_names:
            if ticker in features[feat].columns:
                v = features.loc[last_date, (feat, ticker)]
                if pd.notna(v):
                    vals[feat] = round(float(v), 4)
        ticker_features[ticker] = vals

    return {
        "date": str(last_date.date()),
        "tickers": selected,
        "ticker_features": ticker_features,
    }


def refresh_data():
    """Incrementally update market data (append recent days only)."""
    print("Updating market data...")
    result = subprocess.run(
        [sys.executable, "data.py", "--update"],
        timeout=600,  # 10 min — incremental is fast
    )
    if result.returncode != 0:
        raise RuntimeError("data.py --update failed")
    print("Data update complete.")


def gather_company_info(ticker: str) -> dict:
    """Fetch company info from yfinance. Returns dict with key fields."""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception:
        info = {}

    return {
        "name": info.get("longName") or info.get("shortName") or ticker,
        "sector": info.get("sector", "Unknown"),
        "industry": info.get("industry", "Unknown"),
        "market_cap": info.get("marketCap"),
        "summary": info.get("longBusinessSummary", ""),
        "forward_pe": info.get("forwardPE"),
        "trailing_pe": info.get("trailingPE"),
        "dividend_yield": info.get("dividendYield"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "analyst_target": info.get("targetMeanPrice"),
        "recommendation": info.get("recommendationKey"),
    }


def generate_company_writeup(
    ticker: str, company_info: dict, feature_vals: dict,
    screen_name: str, n_screens_in: int, total_screens: int,
) -> str:
    """Generate a 3-5 sentence company write-up using Claude.

    Provides yfinance info + feature values as grounding, asks Claude
    to add recent context (earnings, news, strategic moves).
    """
    # Format feature highlights (top features by pctrank)
    pctrank_feats = {
        k: v for k, v in feature_vals.items()
        if k.endswith("_pctrank") and v is not None
    }
    top_feats = sorted(
        pctrank_feats.items(), key=lambda x: x[1], reverse=True
    )[:5]
    feat_lines = "\n".join(f"  - {k}: {v:.0%}" for k, v in top_feats)

    market_cap_str = ""
    if company_info.get("market_cap"):
        mc = company_info["market_cap"]
        if mc >= 1e12:
            market_cap_str = f"${mc / 1e12:.1f}T"
        elif mc >= 1e9:
            market_cap_str = f"${mc / 1e9:.0f}B"
        else:
            market_cap_str = f"${mc / 1e6:.0f}M"

    prompt = (
        f"Write a concise investment context paragraph (3-5 sentences) for "
        f"{ticker} ({company_info['name']}).\n\n"
        f"Company: {company_info['name']}\n"
        f"Sector: {company_info['sector']} / {company_info['industry']}\n"
        f"Market cap: {market_cap_str}\n"
        f"Forward P/E: {company_info.get('forward_pe', 'N/A')}\n"
        f"Analyst target: ${company_info.get('analyst_target', 'N/A')}\n"
        f"Recommendation: {company_info.get('recommendation', 'N/A')}\n\n"
        f"This stock was selected by screen '{screen_name}' "
        f"(appears in {n_screens_in}/{total_screens} screens).\n"
        f"Top percentile rank features:\n{feat_lines}\n\n"
        f"Include: what the company does, recent developments (earnings, "
        f"product launches, macro headwinds/tailwinds), and why the screen's "
        f"quantitative signals make sense given the fundamental picture. "
        f"Be factual. If you're unsure about very recent events, say so. "
        f"Output ONLY the paragraph, no headers or preamble."
    )

    try:
        return _claude_call(prompt, timeout=60, allowed_tools=[]).strip()
    except Exception as e:
        return f"(Could not generate write-up: {e})"


def _format_market_cap(mc) -> str:
    if not mc:
        return "N/A"
    if mc >= 1e12:
        return f"${mc / 1e12:.1f}T"
    if mc >= 1e9:
        return f"${mc / 1e9:.0f}B"
    return f"${mc / 1e6:.0f}M"


def render_report(
    screens: list[dict],
    screen_results: list[dict],
    company_writeups: dict[str, str],
    company_infos: dict[str, dict],
    ticker_screen_counts: dict[str, int],
) -> str:
    """Render the full screen report as markdown."""
    today = screen_results[0]["date"] if screen_results else str(date.today())
    lines = [f"# Screen Report — {today}\n"]

    # Screens overview table
    lines.append("## Screens Selected\n")
    lines.append("| # | Screen | Sharpe | Holding | Hypothesis |")
    lines.append("|---|--------|--------|---------|------------|")
    for i, s in enumerate(screens, 1):
        hd = s.get("holding_days", 21)
        lines.append(
            f"| {i} | {s['name']} | {s['sharpe']:.3f} | {hd}d | "
            f"{s.get('hypothesis', '')[:80]} |"
        )
    lines.append("")

    # Per-screen detail
    for i, (screen, result) in enumerate(
        zip(screens, screen_results), 1
    ):
        lines.append(f"## Screen {i}: {screen['name']}\n")
        lines.append(
            f"**Hypothesis:** {screen.get('hypothesis', 'N/A')}\n"
        )
        lines.append(
            f"**Backtest Sharpe:** {screen['sharpe']:.3f} | "
            f"**Holding:** {screen.get('holding_days', 21)}d\n"
        )

        # Filters
        lines.append("**Filters:**")
        for f in screen.get("filters", []):
            val = f["value"]
            if isinstance(val, list):
                val_str = f"[{val[0]}, {val[1]}]"
            else:
                val_str = str(val)
            lines.append(f"- `{f['feature']}` {f['op']} {val_str}")
        lines.append("")

        # Selected stocks table
        lines.append(
            f"**Stocks selected ({len(result['tickers'])}):**\n"
        )
        lines.append(
            "| Ticker | Company | Sector | Mkt Cap | In # Screens |"
        )
        lines.append(
            "|--------|---------|--------|---------|-------------|"
        )
        for ticker in result["tickers"]:
            info = company_infos.get(ticker, {})
            mc = _format_market_cap(info.get("market_cap"))
            n_in = ticker_screen_counts.get(ticker, 0)
            lines.append(
                f"| {ticker} | {info.get('name', ticker)} | "
                f"{info.get('sector', '?')} | {mc} | {n_in} |"
            )
        lines.append("")

        # Per-stock write-ups
        for ticker in result["tickers"]:
            info = company_infos.get(ticker, {})
            lines.append(
                f"### {ticker} — {info.get('name', ticker)}\n"
            )
            writeup = company_writeups.get(
                ticker, "No write-up available."
            )
            lines.append(f"{writeup}\n")

            # Key feature values
            feats = result["ticker_features"].get(ticker, {})
            pctranks = {
                k: v for k, v in feats.items()
                if k.endswith("_pctrank")
            }
            if pctranks:
                top = sorted(
                    pctranks.items(), key=lambda x: x[1], reverse=True
                )[:6]
                feat_str = " | ".join(
                    f"`{k}`: {v:.0%}" for k, v in top
                )
                lines.append(f"**Top features:** {feat_str}\n")
        lines.append("")

    # Consensus picks
    consensus = {
        t: c for t, c in ticker_screen_counts.items() if c >= 2
    }
    if consensus:
        lines.append("## Consensus Picks\n")
        lines.append(
            "Stocks appearing in 2+ screens deserve extra attention.\n"
        )
        lines.append("| Ticker | Company | Screens |")
        lines.append("|--------|---------|---------|")
        for t, c in sorted(consensus.items(), key=lambda x: -x[1]):
            info = company_infos.get(t, {})
            lines.append(f"| {t} | {info.get('name', t)} | {c} |")
        lines.append("")
    else:
        lines.append("## Consensus Picks\n")
        lines.append("No stocks appeared in 2+ screens.\n")

    lines.append("---\n")
    lines.append("*Generated by AutoScreen*\n")

    return "\n".join(lines)


def run_screen_mode(k: int = 3, skip_refresh: bool = False):
    """Full screen mode pipeline: select -> refresh -> screen -> report.

    Args:
        k: Number of top screens to run.
        skip_refresh: If True, skip data refresh (use cached data).
    """
    # Step 1: Load and select screens
    print(f"Loading results from {RESULTS_PATH}...")
    keeps = load_keep_screens()
    if not keeps:
        print(
            "No KEEP screens found in results.jsonl. "
            "Run research mode first."
        )
        return

    selected = select_diverse_screens(keeps, k=k)
    print(f"Selected {len(selected)} screens (of {len(keeps)} KEEP):")
    for i, s in enumerate(selected, 1):
        print(f"  {i}. {s['name']} (Sharpe={s['sharpe']:.3f})")

    # Step 2: Refresh data
    if not skip_refresh:
        refresh_data()

    # Step 3: Compute features and run screens
    print("Computing features...")
    features = compute_all_features()
    print(f"Features ready: {features.shape}")

    screen_results = []
    for s in selected:
        print(f"Running screen: {s['name']}...")
        result = run_screen_today(s, features)
        screen_results.append(result)
        print(f"  Selected {len(result['tickers'])} stocks")

    # Step 4: Count consensus
    ticker_screen_counts = {}
    for result in screen_results:
        for ticker in result["tickers"]:
            ticker_screen_counts[ticker] = (
                ticker_screen_counts.get(ticker, 0) + 1
            )

    # Step 5: Gather company info + write-ups
    all_tickers = sorted(set(
        t for result in screen_results for t in result["tickers"]
    ))
    print(f"Gathering info for {len(all_tickers)} unique tickers...")

    company_infos = {}
    company_writeups = {}
    for ticker in all_tickers:
        print(f"  {ticker}...", end=" ", flush=True)
        company_infos[ticker] = gather_company_info(ticker)

        # Find which screen(s) this ticker appears in
        in_screens = [
            s["name"] for s, r in zip(selected, screen_results)
            if ticker in r["tickers"]
        ]
        # Use first screen for the write-up context
        first_result = next(
            r for r in screen_results if ticker in r["tickers"]
        )
        feat_vals = first_result["ticker_features"].get(ticker, {})

        writeup = generate_company_writeup(
            ticker, company_infos[ticker], feat_vals,
            in_screens[0],
            ticker_screen_counts[ticker],
            len(selected),
        )
        company_writeups[ticker] = writeup
        print("done")

    # Step 6: Render and save report
    report = render_report(
        selected, screen_results, company_writeups,
        company_infos, ticker_screen_counts,
    )

    report_date = (
        screen_results[0]["date"] if screen_results
        else str(date.today())
    )
    report_dir = REPORTS_DIR / report_date
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "report.md"
    report_path.write_text(report)

    # Also save screen definitions for reproducibility
    screens_json = [
        {
            "name": s["name"], "sharpe": s["sharpe"],
            "filters": s["filters"],
            "holding_days": s.get("holding_days", 21),
            "rank_by": s.get("rank_by"),
            "rank_order": s.get("rank_order"),
            "score": s.get("score"),
        }
        for s in selected
    ]
    (report_dir / "screens.json").write_text(
        json.dumps(screens_json, indent=2)
    )

    print(f"\nReport saved to {report_path}")
    print(f"Screens saved to {report_dir / 'screens.json'}")
    return report_path
