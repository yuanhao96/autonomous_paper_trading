"""Tests for NT micro-backtest signal extraction."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd

from src.strategies.spec import RiskParams, StrategySpec


def _make_price_df(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV DataFrame."""
    rng = np.random.default_rng(seed)
    close = 100.0 + np.cumsum(rng.normal(0.05, 1.0, n))
    close = np.maximum(close, 10.0)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "Open": close * 0.995,
        "High": close * 1.01,
        "Low": close * 0.99,
        "Close": close,
        "Volume": rng.integers(100_000, 5_000_000, n),
    }, index=idx)


def _make_spec(template: str = "time-series-momentum") -> StrategySpec:
    return StrategySpec(
        template=template,
        parameters={"lookback": 60, "threshold": 0.0},
        universe_id="sector_etfs",
        risk=RiskParams(max_position_pct=0.10, max_positions=5),
    )


class TestComputeNtSignals:
    """Test compute_nt_signals with fallback behaviour."""

    def test_fallback_when_nt_unavailable(self):
        """When NT is not installed, falls back to signal-based path."""
        from src.live.nt_signals import compute_nt_signals

        spec = _make_spec()
        prices = {"SPY": _make_price_df(), "QQQ": _make_price_df(seed=43)}

        with patch(
            "src.validation.translator.is_nautilus_available", return_value=False
        ):
            with patch("src.live.signals.compute_signals") as mock_cs:
                mock_cs.return_value = {"SPY": "long", "QQQ": "flat"}
                signals = compute_nt_signals(spec, prices)

        assert signals == {"SPY": "long", "QQQ": "flat"}
        mock_cs.assert_called_once_with(spec, prices)

    def test_fallback_when_translation_fails(self):
        """When translate_nautilus returns None, falls back."""
        from src.live.nt_signals import compute_nt_signals

        spec = _make_spec()
        prices = {"SPY": _make_price_df()}

        with patch(
            "src.validation.translator.is_nautilus_available", return_value=True
        ):
            with patch(
                "src.validation.translator.translate_nautilus", return_value=None
            ):
                with patch("src.live.signals.compute_signals") as mock_cs:
                    mock_cs.return_value = {"SPY": "long"}
                    signals = compute_nt_signals(spec, prices)

        assert signals == {"SPY": "long"}

    def test_short_data_returns_flat(self):
        """Symbols with < 50 bars get 'flat' without running a backtest."""
        from src.live.nt_signals import compute_nt_signals

        spec = _make_spec()
        short_df = _make_price_df(n=30)
        prices = {"SPY": short_df}

        with patch(
            "src.validation.translator.is_nautilus_available", return_value=True
        ):
            with patch(
                "src.validation.translator.translate_nautilus",
                return_value=(object, {}),
            ):
                signals = compute_nt_signals(spec, prices)

        assert signals["SPY"] == "flat"

    def test_returns_long_or_flat(self):
        """Signal values are always 'long' or 'flat'."""
        from src.live import nt_signals
        from src.live.nt_signals import compute_nt_signals

        spec = _make_spec()
        prices = {"SPY": _make_price_df(), "QQQ": _make_price_df(seed=43)}

        with patch(
            "src.validation.translator.is_nautilus_available", return_value=True
        ):
            with patch(
                "src.validation.translator.translate_nautilus",
                return_value=(object, {}),
            ):
                with patch.object(
                    nt_signals, "_run_micro_backtest", return_value="long"
                ):
                    signals = compute_nt_signals(spec, prices)

        for sig in signals.values():
            assert sig in ("long", "flat")

    def test_per_symbol_fallback_on_backtest_error(self):
        """If micro-backtest raises for one symbol, falls back per-symbol."""
        from src.live import nt_signals
        from src.live.nt_signals import compute_nt_signals

        spec = _make_spec()
        prices = {"SPY": _make_price_df(), "QQQ": _make_price_df(seed=43)}

        with patch(
            "src.validation.translator.is_nautilus_available", return_value=True
        ):
            with patch(
                "src.validation.translator.translate_nautilus",
                return_value=(object, {}),
            ):
                with patch.object(
                    nt_signals,
                    "_run_micro_backtest",
                    side_effect=[RuntimeError("engine crash"), "long"],
                ):
                    with patch("src.core.signals.compute_signal") as mock_cs:
                        mock_cs.return_value = "flat"
                        signals = compute_nt_signals(spec, prices)

        # SPY fell back to signal, QQQ ran micro-backtest
        assert signals["SPY"] == "flat"
        assert signals["QQQ"] == "long"
