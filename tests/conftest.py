"""Shared pytest fixtures for the autonomou_evolving_investment test suite."""

from __future__ import annotations

import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Sample OHLCV DataFrame
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_ohlcv_data() -> pd.DataFrame:
    """Return a synthetic OHLCV DataFrame with 400 trading days.

    Prices follow a gentle upward random walk so that strategies can
    produce meaningful backtest results.
    """
    np.random.seed(42)
    n = 400
    dates = pd.bdate_range(start="2023-01-03", periods=n, freq="B")
    close = 100.0 + np.cumsum(np.random.normal(0.05, 1.0, n))
    # Ensure no negative prices.
    close = np.maximum(close, 1.0)

    df = pd.DataFrame(
        {
            "Open": close * (1 + np.random.uniform(-0.01, 0.01, n)),
            "High": close * (1 + np.random.uniform(0.0, 0.02, n)),
            "Low": close * (1 - np.random.uniform(0.0, 0.02, n)),
            "Close": close,
            "Volume": np.random.randint(100_000, 10_000_000, n),
        },
        index=dates,
    )
    df.index.name = "Date"
    return df


# ---------------------------------------------------------------------------
# Sample preferences YAML
# ---------------------------------------------------------------------------

_VALID_PREFERENCES_YAML = textwrap.dedent(
    """\
    risk_tolerance: moderate
    max_drawdown_pct: 15
    trading_horizon: swing
    target_annual_return_pct: 20
    allowed_asset_classes:
      - us_equities
    max_position_pct: 10
    max_daily_loss_pct: 3
    max_sector_concentration_pct: 30
    evolution_permissions:
      modify_strategies: true
      modify_backtester: true
      modify_indicators: true
      modify_risk_engine: false
      modify_ui: true
      modify_core_agent: false
    """
)


@pytest.fixture
def sample_preferences_yaml(tmp_path: Path) -> Path:
    """Write a valid preferences YAML to a temp file and return its path."""
    p = tmp_path / "preferences.yaml"
    p.write_text(_VALID_PREFERENCES_YAML, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Sample trades list
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_trades() -> list[dict]:
    """Return a list of trade dicts with known P&L values."""
    return [
        {
            "ticker": "AAPL", "pnl": 150.0,
            "entry_date": "2023-06-01",
            "exit_date": "2023-06-10",
            "entry_price": 170.0, "exit_price": 175.0,
            "return_pct": 0.0294, "side": "long",
        },
        {
            "ticker": "GOOG", "pnl": -50.0,
            "entry_date": "2023-07-01",
            "exit_date": "2023-07-08",
            "entry_price": 120.0, "exit_price": 118.0,
            "return_pct": -0.0167, "side": "long",
        },
        {
            "ticker": "MSFT", "pnl": 200.0,
            "entry_date": "2023-08-01",
            "exit_date": "2023-08-15",
            "entry_price": 330.0, "exit_price": 340.0,
            "return_pct": 0.0303, "side": "long",
        },
        {
            "ticker": "TSLA", "pnl": -30.0,
            "entry_date": "2023-09-01",
            "exit_date": "2023-09-05",
            "entry_price": 250.0, "exit_price": 248.0,
            "return_pct": -0.008, "side": "long",
        },
        {
            "ticker": "AMZN", "pnl": 80.0,
            "entry_date": "2023-10-01",
            "exit_date": "2023-10-12",
            "entry_price": 130.0, "exit_price": 134.0,
            "return_pct": 0.0308, "side": "long",
        },
    ]
