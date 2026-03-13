import json

import numpy as np
import pandas as pd

from screen_report import (
    load_keep_screens,
    select_diverse_screens,
    run_screen_today,
    render_report,
)


def test_load_keep_screens(tmp_path):
    """Load only KEEP screens (Sharpe >= 0.3) with their index."""
    results = [
        {"name": "good", "sharpe": 0.5, "filters": [], "hypothesis": "x",
         "alpha_monthly_mean": 0.01, "alpha_annual": 0.12, "win_rate": 0.6,
         "n_months": 12, "n_avg_stocks": 15, "holding_days": 21,
         "monthly_details": []},
        {"name": "bad", "sharpe": 0.1, "filters": [], "hypothesis": "y",
         "alpha_monthly_mean": 0.001, "alpha_annual": 0.01, "win_rate": 0.4,
         "n_months": 12, "n_avg_stocks": 10, "holding_days": 21,
         "monthly_details": []},
        {"name": "great", "sharpe": 1.2, "filters": [], "hypothesis": "z",
         "alpha_monthly_mean": 0.03, "alpha_annual": 0.36, "win_rate": 0.7,
         "n_months": 12, "n_avg_stocks": 18, "holding_days": 42,
         "monthly_details": []},
    ]
    jsonl = tmp_path / "results.jsonl"
    with open(jsonl, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    keeps = load_keep_screens(jsonl)
    assert len(keeps) == 2
    # Sorted by sharpe desc
    assert keeps[0]["name"] == "great"
    assert keeps[1]["name"] == "good"
    # Each has an 'idx' field for stock_details lookup
    assert keeps[0]["idx"] == 2
    assert keeps[1]["idx"] == 0


def test_select_diverse_screens_prefers_diversity(tmp_path):
    """When two screens have similar Sharpe but different stocks, pick diverse."""
    details_dir = tmp_path / "details"
    details_dir.mkdir()

    # Screen 0: stocks A, B, C
    with open(details_dir / "0.json", "w") as f:
        json.dump([{"month": "2025-06-01", "stocks": {"A": 0.01, "B": 0.02, "C": 0.03}}], f)
    # Screen 1: stocks A, B, C — identical to 0 (Jaccard=1.0)
    with open(details_dir / "1.json", "w") as f:
        json.dump([{"month": "2025-06-01", "stocks": {"A": 0.01, "B": 0.02, "C": 0.03}}], f)
    # Screen 2: stocks X, Y, Z — zero overlap with 0
    with open(details_dir / "2.json", "w") as f:
        json.dump([{"month": "2025-06-01", "stocks": {"X": 0.01, "Y": 0.02, "Z": 0.03}}], f)

    screens = [
        {"name": "best", "sharpe": 1.0, "idx": 0, "filters": []},
        {"name": "similar", "sharpe": 0.9, "idx": 1, "filters": []},
        {"name": "diverse", "sharpe": 0.85, "idx": 2, "filters": []},
    ]

    selected = select_diverse_screens(screens, k=2, details_dir=details_dir)
    assert len(selected) == 2
    assert selected[0]["name"] == "best"
    # Should prefer "diverse" over "similar" despite lower Sharpe
    assert selected[1]["name"] == "diverse"


def test_select_diverse_screens_k_larger_than_available(tmp_path):
    """If K > available screens, return all."""
    details_dir = tmp_path / "details"
    details_dir.mkdir()
    with open(details_dir / "0.json", "w") as f:
        json.dump([{"month": "2025-06-01", "stocks": {"A": 0.01}}], f)

    screens = [{"name": "only", "sharpe": 0.5, "idx": 0, "filters": []}]
    selected = select_diverse_screens(screens, k=3, details_dir=details_dir)
    assert len(selected) == 1


def test_run_screen_today_synthetic():
    """Run a screen on synthetic feature data, get back selected tickers + features."""
    dates = pd.date_range("2025-01-01", periods=5, freq="B")
    tickers = ["AAPL", "GOOG", "MSFT", "AMZN", "META"]
    ret = pd.DataFrame(
        [[0.1, 0.2, -0.05, 0.15, 0.3]] * 5,
        index=dates, columns=tickers,
    )
    vol = pd.DataFrame(
        [[0.2, 0.15, 0.3, 0.25, 0.1]] * 5,
        index=dates, columns=tickers,
    )
    features = pd.concat({"return_6m": ret, "volatility_20d": vol}, axis=1)

    screen_def = {
        "name": "test",
        "hypothesis": "test",
        "filters": [{"feature": "return_6m", "op": ">", "value": 0.05}],
        "top_n": 3,
        "rank_by": "return_6m",
        "rank_order": "desc",
    }

    result = run_screen_today(screen_def, features)
    assert "tickers" in result
    assert "date" in result
    assert "ticker_features" in result
    # META (0.3), GOOG (0.2), AMZN (0.15) — top 3 by return_6m
    assert result["tickers"] == ["META", "GOOG", "AMZN"]
    # Each ticker has feature values
    assert "META" in result["ticker_features"]
    assert "return_6m" in result["ticker_features"]["META"]


def test_render_report_structure():
    """Report should contain key sections."""
    screens = [
        {
            "name": "Test Screen",
            "hypothesis": "testing hypothesis",
            "sharpe": 0.8,
            "holding_days": 21,
            "filters": [{"feature": "return_6m", "op": ">", "value": 0.1}],
        }
    ]
    screen_results = [
        {
            "date": "2025-03-13",
            "tickers": ["AAPL", "MSFT"],
            "ticker_features": {
                "AAPL": {"return_6m": 0.15, "return_6m_pctrank": 0.85},
                "MSFT": {"return_6m": 0.12, "return_6m_pctrank": 0.78},
            },
        }
    ]
    company_writeups = {
        "AAPL": "Apple is a tech company...",
        "MSFT": "Microsoft is a software company...",
    }
    company_infos = {
        "AAPL": {"name": "Apple Inc.", "sector": "Technology",
                 "industry": "Consumer Electronics", "market_cap": 3e12},
        "MSFT": {"name": "Microsoft", "sector": "Technology",
                 "industry": "Software", "market_cap": 2.8e12},
    }
    ticker_screen_counts = {"AAPL": 1, "MSFT": 1}

    md = render_report(
        screens, screen_results, company_writeups,
        company_infos, ticker_screen_counts,
    )

    assert "# Screen Report" in md
    assert "Test Screen" in md
    assert "AAPL" in md
    assert "Apple is a tech company" in md
    assert "Consensus Picks" in md
