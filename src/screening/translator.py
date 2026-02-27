"""Deterministic translator: StrategySpec → backtesting.py Strategy class.

This is the core bridge between the LLM-generated strategy specifications
and the backtesting.py framework. The translator is deterministic — given
the same StrategySpec, it always produces the same Strategy class.

Supported strategy categories (maps to knowledge base templates):
- Momentum: Cross-sectional and time-series momentum
- Mean reversion: Bollinger, RSI, pairs
- Factor: Value, quality, size
- Trend following: Moving average crossovers, breakouts
- Calendar: Day-of-week, month-of-year effects
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from backtesting import Strategy
from backtesting.lib import crossover

from src.strategies.spec import StrategySpec


def translate(spec: StrategySpec, data: pd.DataFrame) -> type[Strategy]:
    """Translate a StrategySpec into a backtesting.py Strategy class.

    Args:
        spec: The strategy specification.
        data: OHLCV DataFrame (used only for metadata, not stored).

    Returns:
        A Strategy subclass ready for backtesting.py Backtest.
    """
    template = spec.template.split("/")[-1] if "/" in spec.template else spec.template
    params = spec.parameters

    # Route to the correct strategy builder
    builders = {
        # ── Momentum (10) ─────────────────────────────────────────
        "momentum-effect-in-stocks": _momentum_crosssectional,
        "time-series-momentum": _momentum_timeseries,
        "time-series-momentum-effect": _momentum_timeseries,
        "dual-momentum": _momentum_dual,
        "sector-momentum": _sector_momentum,
        "asset-class-momentum": _asset_class_momentum,
        "asset-class-trend-following": _asset_class_trend_following,
        "momentum-and-reversal-combined-with-volatility-effect-in-stocks": _momentum_volatility,
        "residual-momentum": _residual_momentum,
        "combining-momentum-effect-with-volume": _momentum_volume,
        # ── Mean Reversion & Pairs (7) ────────────────────────────
        "mean-reversion-rsi": _mean_reversion_rsi,
        "mean-reversion-bollinger": _mean_reversion_bollinger,
        "pairs-trading": _pairs_trading,
        "short-term-reversal": _short_term_reversal,
        "short-term-reversal-strategy-in-stocks": _short_term_reversal,
        "mean-reversion-statistical-arbitrage-in-stocks": _stat_arb,
        "pairs-trading-with-stocks": _pairs_trading,
        # ── Technical (6) ─────────────────────────────────────────
        "moving-average-crossover": _ma_crossover,
        "breakout": _breakout,
        "trend-following": _trend_following,
        "ichimoku-clouds-in-energy-sector": _ichimoku,
        "dual-thrust-trading-algorithm": _dual_thrust,
        "paired-switching": _paired_switching,
        # ── Factor Investing (5) ──────────────────────────────────
        "fama-french-five-factors": _fama_french,
        "beta-factors-in-stocks": _low_beta,
        "liquidity-effect-in-stocks": _liquidity_factor,
        "accrual-anomaly": _accrual_anomaly,
        "earnings-quality-factor": _earnings_quality,
        # ── Value & Fundamental (5) ───────────────────────────────
        "value-factor": _value_factor,
        "price-earnings-anomaly": _pe_anomaly,
        "book-to-market-value-anomaly": _book_to_market,
        "small-capitalization-stocks-premium-anomaly": _small_cap,
        "g-score-investing": _g_score,
        # ── Calendar Anomalies (5) ────────────────────────────────
        "turn-of-the-month-in-equity-indexes": _turn_of_month,
        "january-effect-in-stocks": _january_effect,
        "pre-holiday-effect": _pre_holiday,
        "overnight-anomaly": _overnight_anomaly,
        "seasonality-effect-same-calendar-month": _seasonality_monthly,
        # ── Volatility & Options (4) ──────────────────────────────
        "volatility-effect-in-stocks": _low_volatility,
        "volatility-risk-premium-effect": _vol_risk_premium,
        "vix-predicts-stock-index-returns": _vix_mean_reversion,
        "leveraged-etfs-with-systematic-risk-management": _leveraged_etf_risk,
        # ── Forex (2) ─────────────────────────────────────────────
        "forex-carry-trade": _carry_trade,
        "combining-mean-reversion-and-momentum-in-forex": _forex_mr_momentum,
        # ── Commodities (2) ───────────────────────────────────────
        "term-structure-effect-in-commodities": _commodity_term_structure,
        "gold-market-timing": _gold_timing,
        # ── Category A: Reuse existing builders (13) ─────────────
        "momentum-effect-in-country-equity-indexes": _momentum_crosssectional,
        "momentum-effect-in-reits": _momentum_crosssectional,
        "momentum-effect-in-stocks-in-small-portfolios": _momentum_crosssectional,
        "momentum-in-mutual-fund-returns": _momentum_crosssectional,
        "momentum-effect-in-commodities-futures": _momentum_timeseries,
        "commodities-futures-trend-following": _trend_following,
        "forex-momentum": _momentum_timeseries,
        "momentum-strategy-low-frequency-forex": _momentum_timeseries,
        "mean-reversion-effect-in-country-equity-indexes": _mean_reversion_bollinger,
        "pairs-trading-with-country-etfs": _pairs_trading,
        "short-term-reversal-with-futures": _short_term_reversal,
        "beta-factor-in-country-equity-indexes": _low_beta,
        "value-effect-within-countries": _value_factor,
        # ── Category B: Signal-driven builders (28) ──────────────
        "january-barometer": _generic_signal,
        "12-month-cycle-cross-section": _generic_signal,
        "lunar-cycle-in-equity-market": _generic_signal,
        "option-expiration-week-effect": _generic_signal,
        "momentum-and-state-of-market-filters": _generic_signal,
        "momentum-and-style-rotation-effect": _generic_signal,
        "momentum-short-term-reversal-strategy": _generic_signal,
        "improved-momentum-strategy-on-commodities-futures": _generic_signal,
        "momentum-effect-combined-with-term-structure-in-commodities": _generic_signal,
        "intraday-etf-momentum": _generic_signal,
        "price-and-earnings-momentum": _generic_signal,
        "sentiment-and-style-rotation-effect-in-stocks": _generic_signal,
        "intraday-dynamic-pairs-trading": _generic_signal,
        "optimal-pairs-trading": _generic_signal,
        "pairs-trading-copula-vs-cointegration": _generic_signal,
        "intraday-arbitrage-between-index-etfs": _generic_signal,
        "can-crude-oil-predict-equity-returns": _generic_signal,
        "trading-with-wti-brent-spread": _generic_signal,
        "dynamic-breakout-ii-strategy": _generic_signal,
        "capm-alpha-ranking-dow-30": _generic_signal,
        "expected-idiosyncratic-skewness": _generic_signal,
        "asset-growth-effect": _generic_signal,
        "roa-effect-within-stocks": _generic_signal,
        "standardized-unexpected-earnings": _generic_signal,
        "fundamental-factor-long-short-strategy": _generic_signal,
        "stock-selection-based-on-fundamental-factors": _generic_signal,
        "exploiting-term-structure-of-vix-futures": _generic_signal,
        "risk-premia-in-forex-markets": _generic_signal,
    }

    builder = builders.get(template, _generic_momentum)
    return builder(spec, params)


def get_optimization_bounds(spec: StrategySpec) -> dict[str, range | list]:
    """Get parameter optimization bounds for a strategy template.

    Returns a dict suitable for backtesting.py's Backtest.optimize().
    """
    template = spec.template.split("/")[-1] if "/" in spec.template else spec.template

    bounds_map: dict[str, dict[str, Any]] = {
        # Momentum
        "momentum-effect-in-stocks": {"lookback": range(3, 18, 3), "hold_period": range(1, 4)},
        "time-series-momentum": {"lookback": range(20, 260, 20), "threshold": [0.0, 0.01, 0.02, 0.05]},
        "time-series-momentum-effect": {"lookback": range(20, 260, 20), "threshold": [0.0, 0.01, 0.02, 0.05]},
        "sector-momentum": {"lookback": range(20, 260, 20), "hold_period": range(1, 4)},
        "asset-class-momentum": {"lookback": range(20, 260, 20)},
        "asset-class-trend-following": {"fast_period": range(10, 50, 10), "slow_period": range(50, 250, 50)},
        "momentum-and-reversal-combined-with-volatility-effect-in-stocks": {"mom_lookback": range(60, 260, 20), "vol_lookback": range(20, 60, 10)},
        "residual-momentum": {"lookback": range(60, 260, 20), "market_lookback": range(60, 260, 20)},
        "combining-momentum-effect-with-volume": {"mom_lookback": range(20, 260, 20), "vol_ratio": [1.0, 1.5, 2.0]},
        # Mean Reversion
        "mean-reversion-rsi": {"rsi_period": range(7, 28, 7), "oversold": range(20, 40, 5), "overbought": range(60, 85, 5)},
        "mean-reversion-bollinger": {"bb_period": range(10, 30, 5), "bb_std": [1.5, 2.0, 2.5, 3.0]},
        "short-term-reversal": {"lookback": range(3, 21, 3)},
        "mean-reversion-statistical-arbitrage-in-stocks": {"lookback": range(30, 120, 15), "entry_z": [1.5, 2.0, 2.5]},
        # Technical
        "moving-average-crossover": {"fast_period": range(5, 30, 5), "slow_period": range(20, 200, 20)},
        "breakout": {"lookback": range(10, 60, 10)},
        "trend-following": {"fast_period": range(10, 50, 10), "slow_period": range(50, 250, 50)},
        "ichimoku-clouds-in-energy-sector": {"tenkan": range(7, 15, 2), "kijun": range(20, 35, 5)},
        "dual-thrust-trading-algorithm": {"lookback": range(3, 10, 2), "k1": [0.3, 0.5, 0.7], "k2": [0.3, 0.5, 0.7]},
        "paired-switching": {"lookback": range(20, 260, 20)},
        # Factor
        "fama-french-five-factors": {"lookback": range(60, 260, 20)},
        "beta-factors-in-stocks": {"lookback": range(60, 260, 20), "beta_threshold": [0.5, 0.7, 1.0]},
        "liquidity-effect-in-stocks": {"lookback": range(20, 60, 10)},
        "accrual-anomaly": {"lookback": range(60, 260, 20)},
        "earnings-quality-factor": {"lookback": range(60, 260, 20)},
        # Value
        "price-earnings-anomaly": {"lookback": range(60, 260, 20)},
        "book-to-market-value-anomaly": {"lookback": range(60, 260, 20)},
        "small-capitalization-stocks-premium-anomaly": {"lookback": range(60, 260, 20)},
        "g-score-investing": {"lookback": range(60, 260, 20)},
        # Calendar
        "turn-of-the-month-in-equity-indexes": {"entry_day": range(-3, 0), "exit_day": range(1, 5)},
        "january-effect-in-stocks": {},
        "pre-holiday-effect": {"days_before": range(1, 4)},
        "overnight-anomaly": {},
        "seasonality-effect-same-calendar-month": {"lookback_years": range(3, 8)},
        # Volatility
        "volatility-effect-in-stocks": {"vol_lookback": range(20, 60, 10)},
        "volatility-risk-premium-effect": {"lookback": range(20, 60, 10)},
        "vix-predicts-stock-index-returns": {"threshold": [15, 20, 25, 30]},
        "leveraged-etfs-with-systematic-risk-management": {"lookback": range(10, 50, 10), "vol_target": [0.10, 0.15, 0.20]},
        # Forex
        "forex-carry-trade": {"lookback": range(20, 260, 20)},
        "combining-mean-reversion-and-momentum-in-forex": {"mom_lookback": range(20, 260, 20), "mr_lookback": range(5, 30, 5)},
        # Commodities
        "term-structure-effect-in-commodities": {"lookback": range(20, 60, 10)},
        "gold-market-timing": {"lookback": range(20, 260, 20)},
        # ── Category A: Reuse existing bounds ────────────────────
        "momentum-effect-in-country-equity-indexes": {"lookback": range(3, 18, 3)},
        "momentum-effect-in-reits": {"lookback": range(3, 18, 3)},
        "momentum-effect-in-stocks-in-small-portfolios": {"lookback": range(3, 18, 3)},
        "momentum-in-mutual-fund-returns": {"lookback": range(3, 18, 3)},
        "momentum-effect-in-commodities-futures": {"lookback": range(20, 260, 20)},
        "commodities-futures-trend-following": {"fast_period": range(10, 50, 10), "slow_period": range(50, 250, 50)},
        "forex-momentum": {"lookback": range(20, 260, 20)},
        "momentum-strategy-low-frequency-forex": {"lookback": range(20, 260, 20)},
        "mean-reversion-effect-in-country-equity-indexes": {"bb_period": range(10, 30, 5), "bb_std": [1.5, 2.0, 2.5]},
        "pairs-trading-with-country-etfs": {"lookback": range(30, 120, 15), "entry_z": [1.5, 2.0, 2.5]},
        "short-term-reversal-with-futures": {"lookback": range(3, 21, 3)},
        "beta-factor-in-country-equity-indexes": {"lookback": range(60, 260, 20)},
        "value-effect-within-countries": {"lookback": range(60, 260, 20)},
        # ── Category B: New templates ─────────────────────────────
        "january-barometer": {},
        "12-month-cycle-cross-section": {},
        "lunar-cycle-in-equity-market": {},
        "option-expiration-week-effect": {},
        "momentum-and-state-of-market-filters": {"lookback": range(60, 260, 20)},
        "momentum-and-style-rotation-effect": {"lookback": range(60, 260, 20)},
        "momentum-short-term-reversal-strategy": {"lookback": range(60, 260, 20), "short_lookback": range(3, 15, 3)},
        "improved-momentum-strategy-on-commodities-futures": {"lookback": range(20, 260, 20)},
        "momentum-effect-combined-with-term-structure-in-commodities": {"lookback": range(20, 260, 20)},
        "intraday-etf-momentum": {"lookback": range(1, 10, 2)},
        "price-and-earnings-momentum": {"lookback": range(60, 260, 20)},
        "sentiment-and-style-rotation-effect-in-stocks": {"lookback": range(60, 260, 20)},
        "intraday-dynamic-pairs-trading": {"lookback": range(20, 80, 10)},
        "optimal-pairs-trading": {"lookback": range(30, 120, 15), "entry_z": [1.0, 1.5, 2.0]},
        "pairs-trading-copula-vs-cointegration": {"lookback": range(30, 120, 15)},
        "intraday-arbitrage-between-index-etfs": {"lookback": range(10, 40, 5)},
        "can-crude-oil-predict-equity-returns": {"lookback": range(20, 260, 20)},
        "trading-with-wti-brent-spread": {"lookback": range(20, 120, 20)},
        "dynamic-breakout-ii-strategy": {"lookback": range(10, 50, 10)},
        "capm-alpha-ranking-dow-30": {"lookback": range(60, 260, 20)},
        "expected-idiosyncratic-skewness": {"lookback": range(30, 120, 15)},
        "asset-growth-effect": {"lookback": range(60, 260, 20)},
        "roa-effect-within-stocks": {"vol_lookback": range(20, 80, 10)},
        "standardized-unexpected-earnings": {"lookback": range(10, 40, 5)},
        "fundamental-factor-long-short-strategy": {"lookback": range(60, 260, 20)},
        "stock-selection-based-on-fundamental-factors": {"lookback": range(60, 260, 20)},
        "exploiting-term-structure-of-vix-futures": {},
        "risk-premia-in-forex-markets": {"lookback": range(20, 120, 20)},
    }

    return bounds_map.get(template, {"lookback": range(5, 30, 5)})


# ── Strategy Builders ────────────────────────────────────────────────


def _momentum_crosssectional(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 12)  # months
    lookback_days = lookback * 21

    class MomentumStrategy(Strategy):
        n_lookback = lookback_days

        def init(self):
            close = pd.Series(self.data.Close)
            self.momentum = self.I(
                lambda c: c / c.shift(self.n_lookback) - 1,
                close,
                name=f"Momentum_{lookback}m",
            )

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            if self.momentum[-1] > 0 and not self.position:
                self.buy(size=_position_size(spec))
            elif self.momentum[-1] < 0 and self.position.is_long:
                self.position.close()

    MomentumStrategy.__name__ = f"Momentum_{lookback}m"
    return MomentumStrategy


def _momentum_timeseries(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 252)
    threshold = params.get("threshold", 0.0)

    class TSMomentumStrategy(Strategy):
        n_lookback = lookback
        n_threshold = threshold

        def init(self):
            close = pd.Series(self.data.Close)
            self.ret = self.I(
                lambda c: c / c.shift(self.n_lookback) - 1,
                close,
                name=f"Return_{lookback}d",
            )

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            if self.ret[-1] > self.n_threshold and not self.position:
                self.buy(size=_position_size(spec))
            elif self.ret[-1] < -self.n_threshold and self.position.is_long:
                self.position.close()

    TSMomentumStrategy.__name__ = f"TSMomentum_{lookback}d"
    return TSMomentumStrategy


def _momentum_dual(spec: StrategySpec, params: dict) -> type[Strategy]:
    abs_lookback = params.get("absolute_lookback", 252)
    rel_lookback = params.get("relative_lookback", 252)

    class DualMomentumStrategy(Strategy):
        n_abs_lookback = abs_lookback
        n_rel_lookback = rel_lookback

        def init(self):
            close = pd.Series(self.data.Close)
            self.abs_ret = self.I(
                lambda c: c / c.shift(self.n_abs_lookback) - 1,
                close,
                name="AbsReturn",
            )

        def next(self):
            if len(self.data) < max(self.n_abs_lookback, self.n_rel_lookback) + 1:
                return
            # Dual momentum: both absolute and relative must be positive
            if self.abs_ret[-1] > 0 and not self.position:
                self.buy(size=_position_size(spec))
            elif self.abs_ret[-1] <= 0 and self.position.is_long:
                self.position.close()

    DualMomentumStrategy.__name__ = "DualMomentum"
    return DualMomentumStrategy


def _ma_crossover(spec: StrategySpec, params: dict) -> type[Strategy]:
    fast = params.get("fast_period", 10)
    slow = params.get("slow_period", 50)

    class MACrossoverStrategy(Strategy):
        n_fast = fast
        n_slow = slow

        def init(self):
            close = pd.Series(self.data.Close)
            self.sma_fast = self.I(lambda c: c.rolling(self.n_fast).mean(), close, name=f"SMA_{fast}")
            self.sma_slow = self.I(lambda c: c.rolling(self.n_slow).mean(), close, name=f"SMA_{slow}")

        def next(self):
            if crossover(self.sma_fast, self.sma_slow):
                self.buy(size=_position_size(spec))
            elif crossover(self.sma_slow, self.sma_fast):
                if self.position.is_long:
                    self.position.close()

    MACrossoverStrategy.__name__ = f"MA_{fast}_{slow}"
    return MACrossoverStrategy


def _mean_reversion_rsi(spec: StrategySpec, params: dict) -> type[Strategy]:
    period = params.get("rsi_period", 14)
    oversold = params.get("oversold", 30)
    overbought = params.get("overbought", 70)

    class RSIMeanReversionStrategy(Strategy):
        n_period = period
        n_oversold = oversold
        n_overbought = overbought

        def init(self):
            close = pd.Series(self.data.Close)
            self.rsi = self.I(lambda c: _calc_rsi(c, self.n_period), close, name=f"RSI_{period}")

        def next(self):
            if len(self.data) < self.n_period + 1:
                return
            if self.rsi[-1] < self.n_oversold and not self.position:
                self.buy(size=_position_size(spec))
            elif self.rsi[-1] > self.n_overbought and self.position.is_long:
                self.position.close()

    RSIMeanReversionStrategy.__name__ = f"RSI_{period}_{oversold}_{overbought}"
    return RSIMeanReversionStrategy


def _mean_reversion_bollinger(spec: StrategySpec, params: dict) -> type[Strategy]:
    period = params.get("bb_period", 20)
    num_std = params.get("bb_std", 2.0)

    class BollingerMeanReversionStrategy(Strategy):
        n_period = period
        n_std = num_std

        def init(self):
            close = pd.Series(self.data.Close)
            self.sma = self.I(lambda c: c.rolling(self.n_period).mean(), close, name="BB_Mid")
            self.upper = self.I(
                lambda c: c.rolling(self.n_period).mean() + self.n_std * c.rolling(self.n_period).std(),
                close,
                name="BB_Upper",
            )
            self.lower = self.I(
                lambda c: c.rolling(self.n_period).mean() - self.n_std * c.rolling(self.n_period).std(),
                close,
                name="BB_Lower",
            )

        def next(self):
            if len(self.data) < self.n_period + 1:
                return
            if self.data.Close[-1] < self.lower[-1] and not self.position:
                self.buy(size=_position_size(spec))
            elif self.data.Close[-1] > self.upper[-1] and self.position.is_long:
                self.position.close()

    BollingerMeanReversionStrategy.__name__ = f"BB_{period}_{num_std}"
    return BollingerMeanReversionStrategy


def _pairs_trading(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 60)
    entry_z = params.get("entry_z", 2.0)
    exit_z = params.get("exit_z", 0.5)

    class PairsTradingStrategy(Strategy):
        """Simplified pairs trading using z-score of price ratio."""

        n_lookback = lookback
        n_entry_z = entry_z
        n_exit_z = exit_z

        def init(self):
            close = pd.Series(self.data.Close)
            ratio = close / close.rolling(self.n_lookback).mean()
            self.zscore = self.I(
                lambda r: (r - r.rolling(self.n_lookback).mean()) / r.rolling(self.n_lookback).std(),
                ratio,
                name="ZScore",
            )

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            if self.zscore[-1] < -self.n_entry_z and not self.position:
                self.buy(size=_position_size(spec))
            elif self.zscore[-1] > self.n_entry_z and not self.position:
                self.sell(size=_position_size(spec))
            elif abs(self.zscore[-1]) < self.n_exit_z and self.position:
                self.position.close()

    PairsTradingStrategy.__name__ = f"Pairs_{lookback}_{entry_z}"
    return PairsTradingStrategy


def _value_factor(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 252)

    class ValueFactorStrategy(Strategy):
        """Simplified value strategy using price-to-moving-average ratio."""

        n_lookback = lookback

        def init(self):
            close = pd.Series(self.data.Close)
            self.value_signal = self.I(
                lambda c: c.rolling(self.n_lookback).mean() / c - 1,
                close,
                name="ValueSignal",
            )

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            if self.value_signal[-1] > 0.1 and not self.position:
                self.buy(size=_position_size(spec))
            elif self.value_signal[-1] < -0.05 and self.position.is_long:
                self.position.close()

    ValueFactorStrategy.__name__ = f"Value_{lookback}"
    return ValueFactorStrategy


def _breakout(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 20)

    class BreakoutStrategy(Strategy):
        n_lookback = lookback

        def init(self):
            high = pd.Series(self.data.High)
            low = pd.Series(self.data.Low)
            self.upper = self.I(lambda h: h.rolling(self.n_lookback).max(), high, name="Upper")
            self.lower = self.I(lambda l: l.rolling(self.n_lookback).min(), low, name="Lower")

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            if self.data.Close[-1] > self.upper[-2] and not self.position:
                self.buy(size=_position_size(spec))
            elif self.data.Close[-1] < self.lower[-2] and self.position.is_long:
                self.position.close()

    BreakoutStrategy.__name__ = f"Breakout_{lookback}"
    return BreakoutStrategy


def _trend_following(spec: StrategySpec, params: dict) -> type[Strategy]:
    fast = params.get("fast_period", 20)
    slow = params.get("slow_period", 100)

    class TrendFollowingStrategy(Strategy):
        n_fast = fast
        n_slow = slow

        def init(self):
            close = pd.Series(self.data.Close)
            self.ema_fast = self.I(lambda c: c.ewm(span=self.n_fast).mean(), close, name=f"EMA_{fast}")
            self.ema_slow = self.I(lambda c: c.ewm(span=self.n_slow).mean(), close, name=f"EMA_{slow}")

        def next(self):
            if crossover(self.ema_fast, self.ema_slow):
                self.buy(size=_position_size(spec))
            elif crossover(self.ema_slow, self.ema_fast):
                if self.position.is_long:
                    self.position.close()

    TrendFollowingStrategy.__name__ = f"TrendFollow_{fast}_{slow}"
    return TrendFollowingStrategy


# ── Momentum Builders (new) ──────────────────────────────────────────


def _sector_momentum(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 126)

    class SectorMomentumStrategy(Strategy):
        n_lookback = lookback

        def init(self):
            close = pd.Series(self.data.Close)
            self.momentum = self.I(lambda c: c / c.shift(self.n_lookback) - 1, close, name="SectorMom")

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            if self.momentum[-1] > 0 and not self.position:
                self.buy(size=_position_size(spec))
            elif self.momentum[-1] < 0 and self.position.is_long:
                self.position.close()

    SectorMomentumStrategy.__name__ = f"SectorMom_{lookback}"
    return SectorMomentumStrategy


def _asset_class_momentum(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 252)
    return _momentum_timeseries(spec, {"lookback": lookback, "threshold": 0.0})


def _asset_class_trend_following(spec: StrategySpec, params: dict) -> type[Strategy]:
    return _trend_following(spec, params)


def _momentum_volatility(spec: StrategySpec, params: dict) -> type[Strategy]:
    mom_lookback = params.get("mom_lookback", 126)
    vol_lookback = params.get("vol_lookback", 30)

    class MomVolStrategy(Strategy):
        n_mom = mom_lookback
        n_vol = vol_lookback

        def init(self):
            close = pd.Series(self.data.Close)
            self.momentum = self.I(lambda c: c / c.shift(self.n_mom) - 1, close, name="Mom")
            self.vol = self.I(lambda c: c.pct_change().rolling(self.n_vol).std() * (252 ** 0.5), close, name="Vol")

        def next(self):
            if len(self.data) < self.n_mom + 1:
                return
            # Buy when positive momentum and declining volatility
            if self.momentum[-1] > 0 and self.vol[-1] < 0.25 and not self.position:
                self.buy(size=_position_size(spec))
            elif (self.momentum[-1] < 0 or self.vol[-1] > 0.40) and self.position.is_long:
                self.position.close()

    MomVolStrategy.__name__ = f"MomVol_{mom_lookback}_{vol_lookback}"
    return MomVolStrategy


def _residual_momentum(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 126)
    market_lookback = params.get("market_lookback", 126)

    class ResidualMomentumStrategy(Strategy):
        n_lookback = lookback
        n_market = market_lookback

        def init(self):
            close = pd.Series(self.data.Close)
            sma = close.rolling(self.n_market).mean()
            # Residual = price deviation from its own long-term trend
            self.residual_mom = self.I(lambda c: (c / c.rolling(self.n_lookback).mean() - 1), close, name="ResMom")

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            if self.residual_mom[-1] > 0.02 and not self.position:
                self.buy(size=_position_size(spec))
            elif self.residual_mom[-1] < -0.02 and self.position.is_long:
                self.position.close()

    ResidualMomentumStrategy.__name__ = f"ResMom_{lookback}"
    return ResidualMomentumStrategy


def _momentum_volume(spec: StrategySpec, params: dict) -> type[Strategy]:
    mom_lookback = params.get("mom_lookback", 126)
    vol_ratio = params.get("vol_ratio", 1.5)

    class MomVolumeStrategy(Strategy):
        n_mom = mom_lookback
        n_vol_ratio = vol_ratio

        def init(self):
            close = pd.Series(self.data.Close)
            volume = pd.Series(self.data.Volume)
            self.momentum = self.I(lambda c: c / c.shift(self.n_mom) - 1, close, name="Mom")
            self.vol_signal = self.I(lambda v: v / v.rolling(20).mean(), volume, name="VolRatio")

        def next(self):
            if len(self.data) < self.n_mom + 1:
                return
            # Buy when momentum positive and volume confirms (above average)
            if self.momentum[-1] > 0 and self.vol_signal[-1] > self.n_vol_ratio and not self.position:
                self.buy(size=_position_size(spec))
            elif self.momentum[-1] < 0 and self.position.is_long:
                self.position.close()

    MomVolumeStrategy.__name__ = f"MomVol_{mom_lookback}"
    return MomVolumeStrategy


# ── Mean Reversion Builders (new) ────────────────────────────────────


def _short_term_reversal(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 5)

    class ShortTermReversalStrategy(Strategy):
        n_lookback = lookback

        def init(self):
            close = pd.Series(self.data.Close)
            self.ret = self.I(lambda c: c / c.shift(self.n_lookback) - 1, close, name="STRet")

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            # Buy losers (reversal) — buy when recent return is very negative
            if self.ret[-1] < -0.03 and not self.position:
                self.buy(size=_position_size(spec))
            elif self.ret[-1] > 0.02 and self.position.is_long:
                self.position.close()

    ShortTermReversalStrategy.__name__ = f"STReversal_{lookback}"
    return ShortTermReversalStrategy


def _stat_arb(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 60)
    entry_z = params.get("entry_z", 2.0)
    return _pairs_trading(spec, {"lookback": lookback, "entry_z": entry_z, "exit_z": 0.5})


# ── Technical Builders (new) ─────────────────────────────────────────


def _ichimoku(spec: StrategySpec, params: dict) -> type[Strategy]:
    tenkan = params.get("tenkan", 9)
    kijun = params.get("kijun", 26)

    class IchimokuStrategy(Strategy):
        n_tenkan = tenkan
        n_kijun = kijun

        def init(self):
            high = pd.Series(self.data.High)
            low = pd.Series(self.data.Low)
            self.tenkan_sen = self.I(
                lambda h, l: (h.rolling(self.n_tenkan).max() + l.rolling(self.n_tenkan).min()) / 2,
                high, low, name="Tenkan",
            )
            self.kijun_sen = self.I(
                lambda h, l: (h.rolling(self.n_kijun).max() + l.rolling(self.n_kijun).min()) / 2,
                high, low, name="Kijun",
            )

        def next(self):
            if len(self.data) < self.n_kijun + 1:
                return
            if crossover(self.tenkan_sen, self.kijun_sen):
                self.buy(size=_position_size(spec))
            elif crossover(self.kijun_sen, self.tenkan_sen):
                if self.position.is_long:
                    self.position.close()

    IchimokuStrategy.__name__ = f"Ichimoku_{tenkan}_{kijun}"
    return IchimokuStrategy


def _dual_thrust(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 5)
    k1 = params.get("k1", 0.5)
    k2 = params.get("k2", 0.5)

    class DualThrustStrategy(Strategy):
        n_lookback = lookback
        n_k1 = k1
        n_k2 = k2

        def init(self):
            high = pd.Series(self.data.High)
            low = pd.Series(self.data.Low)
            close = pd.Series(self.data.Close)
            hh = high.rolling(self.n_lookback).max()
            ll = low.rolling(self.n_lookback).min()
            hc = close.rolling(self.n_lookback).max()
            lc = close.rolling(self.n_lookback).min()
            self.range_val = self.I(
                lambda: np.maximum(hh - lc, hc - ll),
                name="Range",
            )
            self.open_price = self.I(lambda c: c, pd.Series(self.data.Open), name="Open")

        def next(self):
            if len(self.data) < self.n_lookback + 2:
                return
            upper = self.open_price[-1] + self.n_k1 * self.range_val[-2]
            lower = self.open_price[-1] - self.n_k2 * self.range_val[-2]
            if self.data.Close[-1] > upper and not self.position:
                self.buy(size=_position_size(spec))
            elif self.data.Close[-1] < lower and self.position.is_long:
                self.position.close()

    DualThrustStrategy.__name__ = f"DualThrust_{lookback}"
    return DualThrustStrategy


def _paired_switching(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 126)

    class PairedSwitchingStrategy(Strategy):
        n_lookback = lookback

        def init(self):
            close = pd.Series(self.data.Close)
            self.momentum = self.I(lambda c: c / c.shift(self.n_lookback) - 1, close, name="PairMom")

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            # Switch to asset when momentum is positive (relative strength approach)
            if self.momentum[-1] > 0 and not self.position:
                self.buy(size=_position_size(spec))
            elif self.momentum[-1] <= 0 and self.position.is_long:
                self.position.close()

    PairedSwitchingStrategy.__name__ = f"PairedSwitch_{lookback}"
    return PairedSwitchingStrategy


# ── Factor Investing Builders (new) ──────────────────────────────────


def _fama_french(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 252)
    # Proxy: uses price-to-MA ratio as value + momentum combination
    class FamaFrenchStrategy(Strategy):
        n_lookback = lookback

        def init(self):
            close = pd.Series(self.data.Close)
            self.value = self.I(lambda c: c.rolling(self.n_lookback).mean() / c - 1, close, name="Value")
            self.momentum = self.I(lambda c: c / c.shift(self.n_lookback) - 1, close, name="Mom")

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            # Combined signal: buy when value is high AND momentum is positive
            if self.value[-1] > 0.05 and self.momentum[-1] > 0 and not self.position:
                self.buy(size=_position_size(spec))
            elif (self.value[-1] < -0.1 or self.momentum[-1] < -0.1) and self.position.is_long:
                self.position.close()

    FamaFrenchStrategy.__name__ = f"FamaFrench_{lookback}"
    return FamaFrenchStrategy


def _low_beta(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 252)
    beta_threshold = params.get("beta_threshold", 0.7)

    class LowBetaStrategy(Strategy):
        n_lookback = lookback

        def init(self):
            close = pd.Series(self.data.Close)
            # Use realized volatility as a beta proxy
            self.vol = self.I(lambda c: c.pct_change().rolling(self.n_lookback).std() * (252 ** 0.5), close, name="Vol")

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            # Buy low-volatility (low-beta proxy) assets
            if self.vol[-1] < 0.20 and not self.position:
                self.buy(size=_position_size(spec))
            elif self.vol[-1] > 0.35 and self.position.is_long:
                self.position.close()

    LowBetaStrategy.__name__ = f"LowBeta_{lookback}"
    return LowBetaStrategy


def _liquidity_factor(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 20)

    class LiquidityStrategy(Strategy):
        n_lookback = lookback

        def init(self):
            volume = pd.Series(self.data.Volume)
            close = pd.Series(self.data.Close)
            # Amihud illiquidity: |return| / volume
            self.illiq = self.I(
                lambda c, v: (c.pct_change().abs() / v.replace(0, np.nan)).rolling(self.n_lookback).mean(),
                close, volume, name="Illiq",
            )

        def next(self):
            if len(self.data) < self.n_lookback + 2:
                return
            # Buy liquid (low illiquidity) stocks when they exist
            if not np.isnan(self.illiq[-1]) and not self.position:
                self.buy(size=_position_size(spec))

    LiquidityStrategy.__name__ = f"Liquidity_{lookback}"
    return LiquidityStrategy


def _accrual_anomaly(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 252)
    # Price-based proxy for accruals: mean-reversion on price/revenue (using MA as proxy)
    return _value_factor(spec, {"lookback": lookback})


def _earnings_quality(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 252)
    # Proxy: low-volatility + value combination
    class EarningsQualityStrategy(Strategy):
        n_lookback = lookback

        def init(self):
            close = pd.Series(self.data.Close)
            self.vol = self.I(lambda c: c.pct_change().rolling(60).std() * (252 ** 0.5), close, name="Vol")
            self.value = self.I(lambda c: c.rolling(self.n_lookback).mean() / c - 1, close, name="Value")

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            if self.vol[-1] < 0.25 and self.value[-1] > 0.05 and not self.position:
                self.buy(size=_position_size(spec))
            elif (self.vol[-1] > 0.40 or self.value[-1] < -0.1) and self.position.is_long:
                self.position.close()

    EarningsQualityStrategy.__name__ = f"EarningsQuality_{lookback}"
    return EarningsQualityStrategy


# ── Value & Fundamental Builders (new) ───────────────────────────────


def _pe_anomaly(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 252)
    return _value_factor(spec, {"lookback": lookback})


def _book_to_market(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 252)
    return _value_factor(spec, {"lookback": lookback})


def _small_cap(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 252)
    # Small-cap premium proxy: buy and hold with momentum filter
    class SmallCapStrategy(Strategy):
        n_lookback = lookback

        def init(self):
            close = pd.Series(self.data.Close)
            self.momentum = self.I(lambda c: c / c.shift(self.n_lookback) - 1, close, name="Mom")

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            if self.momentum[-1] > -0.1 and not self.position:
                self.buy(size=_position_size(spec))
            elif self.momentum[-1] < -0.2 and self.position.is_long:
                self.position.close()

    SmallCapStrategy.__name__ = f"SmallCap_{lookback}"
    return SmallCapStrategy


def _g_score(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 126)
    # G-Score proxy: combination of value + low vol + positive momentum
    class GScoreStrategy(Strategy):
        n_lookback = lookback

        def init(self):
            close = pd.Series(self.data.Close)
            self.value = self.I(lambda c: c.rolling(self.n_lookback).mean() / c - 1, close, name="Value")
            self.vol = self.I(lambda c: c.pct_change().rolling(30).std() * (252 ** 0.5), close, name="Vol")

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            score = 0
            if self.value[-1] > 0:
                score += 1
            if self.vol[-1] < 0.25:
                score += 1
            if self.data.Close[-1] > self.data.Close[-21]:
                score += 1

            if score >= 2 and not self.position:
                self.buy(size=_position_size(spec))
            elif score < 1 and self.position.is_long:
                self.position.close()

    GScoreStrategy.__name__ = f"GScore_{lookback}"
    return GScoreStrategy


# ── Calendar Anomaly Builders (new) ──────────────────────────────────


def _turn_of_month(spec: StrategySpec, params: dict) -> type[Strategy]:
    entry_day = params.get("entry_day", -2)
    exit_day = params.get("exit_day", 3)

    class TurnOfMonthStrategy(Strategy):
        n_entry = entry_day
        n_exit = exit_day

        def init(self):
            dates = pd.Series(self.data.index)
            self.day_of_month = self.I(lambda d: pd.DatetimeIndex(d).day, dates, name="DOM")

        def next(self):
            dom = int(self.day_of_month[-1])
            # Buy near end of month (day >= 27), sell after first few days
            if dom >= 27 and not self.position:
                self.buy(size=_position_size(spec))
            elif dom >= self.n_exit and dom < 15 and self.position.is_long:
                self.position.close()

    TurnOfMonthStrategy.__name__ = "TurnOfMonth"
    return TurnOfMonthStrategy


def _january_effect(spec: StrategySpec, params: dict) -> type[Strategy]:

    class JanuaryEffectStrategy(Strategy):
        def init(self):
            dates = pd.Series(self.data.index)
            self.month = self.I(lambda d: pd.DatetimeIndex(d).month, dates, name="Month")

        def next(self):
            m = int(self.month[-1])
            # Buy in January, sell in February
            if m == 1 and not self.position:
                self.buy(size=_position_size(spec))
            elif m == 2 and self.position.is_long:
                self.position.close()

    JanuaryEffectStrategy.__name__ = "JanuaryEffect"
    return JanuaryEffectStrategy


def _pre_holiday(spec: StrategySpec, params: dict) -> type[Strategy]:
    days_before = params.get("days_before", 1)

    class PreHolidayStrategy(Strategy):
        """Buy day before weekends (Fridays as proxy for pre-holiday)."""
        n_days = days_before

        def init(self):
            dates = pd.Series(self.data.index)
            self.dow = self.I(lambda d: pd.DatetimeIndex(d).dayofweek, dates, name="DOW")

        def next(self):
            dow = int(self.dow[-1])
            # Friday = 4
            if dow == 4 and not self.position:
                self.buy(size=_position_size(spec))
            elif dow == 0 and self.position.is_long:
                self.position.close()

    PreHolidayStrategy.__name__ = "PreHoliday"
    return PreHolidayStrategy


def _overnight_anomaly(spec: StrategySpec, params: dict) -> type[Strategy]:

    class OvernightAnomalyStrategy(Strategy):
        def init(self):
            o = pd.Series(self.data.Open)
            c = pd.Series(self.data.Close)
            # Overnight return = Open / previous Close - 1
            self.overnight_ret = self.I(lambda op, cl: op / cl.shift(1) - 1, o, c, name="OvernightRet")

        def next(self):
            if len(self.data) < 5:
                return
            # Trend-follow on overnight returns
            avg_on = np.mean([self.overnight_ret[-i] for i in range(1, min(6, len(self.data)))])
            if avg_on > 0.001 and not self.position:
                self.buy(size=_position_size(spec))
            elif avg_on < -0.001 and self.position.is_long:
                self.position.close()

    OvernightAnomalyStrategy.__name__ = "OvernightAnomaly"
    return OvernightAnomalyStrategy


def _seasonality_monthly(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback_years = params.get("lookback_years", 5)

    class SeasonalityStrategy(Strategy):
        def init(self):
            close = pd.Series(self.data.Close)
            self.monthly_ret = self.I(lambda c: c / c.shift(21) - 1, close, name="MonthlyRet")
            dates = pd.Series(self.data.index)
            self.month = self.I(lambda d: pd.DatetimeIndex(d).month, dates, name="Month")

        def next(self):
            if len(self.data) < 252:
                return
            # Buy in historically strong months (Nov-Apr "sell in May" inverse)
            m = int(self.month[-1])
            if m in (11, 12, 1, 2, 3, 4) and not self.position:
                self.buy(size=_position_size(spec))
            elif m in (5, 6, 7, 8, 9, 10) and self.position.is_long:
                self.position.close()

    SeasonalityStrategy.__name__ = "Seasonality"
    return SeasonalityStrategy


# ── Volatility & Options Builders (new) ──────────────────────────────


def _low_volatility(spec: StrategySpec, params: dict) -> type[Strategy]:
    vol_lookback = params.get("vol_lookback", 30)

    class LowVolStrategy(Strategy):
        n_vol = vol_lookback

        def init(self):
            close = pd.Series(self.data.Close)
            self.vol = self.I(lambda c: c.pct_change().rolling(self.n_vol).std() * (252 ** 0.5), close, name="Vol")

        def next(self):
            if len(self.data) < self.n_vol + 1:
                return
            if self.vol[-1] < 0.20 and not self.position:
                self.buy(size=_position_size(spec))
            elif self.vol[-1] > 0.35 and self.position.is_long:
                self.position.close()

    LowVolStrategy.__name__ = f"LowVol_{vol_lookback}"
    return LowVolStrategy


def _vol_risk_premium(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 30)

    class VolRiskPremiumStrategy(Strategy):
        n_lookback = lookback

        def init(self):
            close = pd.Series(self.data.Close)
            # Realized vol vs implied vol proxy (using short-term vs long-term realized)
            self.short_vol = self.I(lambda c: c.pct_change().rolling(10).std() * (252 ** 0.5), close, name="ShortVol")
            self.long_vol = self.I(lambda c: c.pct_change().rolling(self.n_lookback).std() * (252 ** 0.5), close, name="LongVol")

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            # Buy when short-term vol < long-term vol (vol risk premium is being harvested)
            if self.short_vol[-1] < self.long_vol[-1] and not self.position:
                self.buy(size=_position_size(spec))
            elif self.short_vol[-1] > self.long_vol[-1] * 1.3 and self.position.is_long:
                self.position.close()

    VolRiskPremiumStrategy.__name__ = f"VolRP_{lookback}"
    return VolRiskPremiumStrategy


def _vix_mean_reversion(spec: StrategySpec, params: dict) -> type[Strategy]:
    threshold = params.get("threshold", 25)

    class VIXMeanReversionStrategy(Strategy):
        """Buy equities when VIX proxy is high (mean-reverts down)."""
        n_threshold = threshold

        def init(self):
            close = pd.Series(self.data.Close)
            # VIX proxy: 20-day realized vol * 100
            self.vix_proxy = self.I(lambda c: c.pct_change().rolling(20).std() * (252 ** 0.5) * 100, close, name="VIXProxy")

        def next(self):
            if len(self.data) < 21:
                return
            if self.vix_proxy[-1] > self.n_threshold and not self.position:
                self.buy(size=_position_size(spec))
            elif self.vix_proxy[-1] < self.n_threshold * 0.6 and self.position.is_long:
                self.position.close()

    VIXMeanReversionStrategy.__name__ = f"VIXMeanRev_{threshold}"
    return VIXMeanReversionStrategy


def _leveraged_etf_risk(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 20)
    vol_target = params.get("vol_target", 0.15)

    class LeveragedETFRiskStrategy(Strategy):
        n_lookback = lookback
        n_vol_target = vol_target

        def init(self):
            close = pd.Series(self.data.Close)
            self.vol = self.I(lambda c: c.pct_change().rolling(self.n_lookback).std() * (252 ** 0.5), close, name="RealVol")
            self.momentum = self.I(lambda c: c / c.shift(self.n_lookback) - 1, close, name="Mom")

        def next(self):
            if len(self.data) < self.n_lookback + 1:
                return
            # Only invest when vol is below target and momentum is positive
            if self.vol[-1] < self.n_vol_target and self.momentum[-1] > 0 and not self.position:
                self.buy(size=_position_size(spec))
            elif (self.vol[-1] > self.n_vol_target * 1.5 or self.momentum[-1] < -0.05) and self.position.is_long:
                self.position.close()

    LeveragedETFRiskStrategy.__name__ = f"LevETF_{lookback}"
    return LeveragedETFRiskStrategy


# ── Forex Builders (new) ─────────────────────────────────────────────


def _carry_trade(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 126)
    # Carry trade proxy: trend-following (carry currencies tend to trend)
    return _momentum_timeseries(spec, {"lookback": lookback, "threshold": 0.0})


def _forex_mr_momentum(spec: StrategySpec, params: dict) -> type[Strategy]:
    mom_lookback = params.get("mom_lookback", 126)
    mr_lookback = params.get("mr_lookback", 10)

    class ForexMRMomStrategy(Strategy):
        n_mom = mom_lookback
        n_mr = mr_lookback

        def init(self):
            close = pd.Series(self.data.Close)
            self.momentum = self.I(lambda c: c / c.shift(self.n_mom) - 1, close, name="Mom")
            self.mr_signal = self.I(lambda c: c.rolling(self.n_mr).mean() / c - 1, close, name="MR")

        def next(self):
            if len(self.data) < self.n_mom + 1:
                return
            # Buy when long-term momentum positive AND short-term oversold
            if self.momentum[-1] > 0 and self.mr_signal[-1] > 0.01 and not self.position:
                self.buy(size=_position_size(spec))
            elif self.momentum[-1] < 0 and self.position.is_long:
                self.position.close()

    ForexMRMomStrategy.__name__ = f"ForexMRMom_{mom_lookback}"
    return ForexMRMomStrategy


# ── Commodity Builders (new) ─────────────────────────────────────────


def _commodity_term_structure(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 30)
    # Term structure proxy: short-term vs long-term MA slope
    class TermStructureStrategy(Strategy):
        n_lookback = lookback

        def init(self):
            close = pd.Series(self.data.Close)
            self.short_ma = self.I(lambda c: c.rolling(self.n_lookback).mean(), close, name="ShortMA")
            self.long_ma = self.I(lambda c: c.rolling(self.n_lookback * 3).mean(), close, name="LongMA")

        def next(self):
            if len(self.data) < self.n_lookback * 3 + 1:
                return
            # Backwardation proxy: short MA > long MA → go long
            if self.short_ma[-1] > self.long_ma[-1] and not self.position:
                self.buy(size=_position_size(spec))
            elif self.short_ma[-1] < self.long_ma[-1] and self.position.is_long:
                self.position.close()

    TermStructureStrategy.__name__ = f"TermStruct_{lookback}"
    return TermStructureStrategy


def _gold_timing(spec: StrategySpec, params: dict) -> type[Strategy]:
    lookback = params.get("lookback", 126)
    return _momentum_timeseries(spec, {"lookback": lookback, "threshold": 0.0})


# ── Fallback ─────────────────────────────────────────────────────────


def _generic_signal(spec: StrategySpec, params: dict) -> type[Strategy]:
    """Signal-driven builder — delegates signal decision to the shared layer."""
    template = spec.template.split("/")[-1] if "/" in spec.template else spec.template
    lookback = max(params.get("lookback", 126), params.get("mom_lookback", 126), 126)

    class SignalDrivenStrategy(Strategy):
        n_lookback = lookback

        def init(self):
            close = pd.Series(self.data.Close)
            self.momentum = self.I(
                lambda c: c / c.shift(self.n_lookback) - 1, close, name="Mom"
            )

        def next(self):
            from src.core.signals import compute_signal

            if len(self.data) < self.n_lookback + 1:
                return
            # Build a mini-DataFrame for the signal function
            idx = self.data.index[: len(self.data)]
            df = pd.DataFrame(
                {
                    "Open": self.data.Open,
                    "High": self.data.High,
                    "Low": self.data.Low,
                    "Close": self.data.Close,
                    "Volume": self.data.Volume,
                },
                index=idx,
            )
            signal = compute_signal(template, df, params)
            if signal == "long" and not self.position:
                self.buy(size=_position_size(spec))
            elif signal == "flat" and self.position.is_long:
                self.position.close()

    SignalDrivenStrategy.__name__ = f"Signal_{template[:20]}"
    return SignalDrivenStrategy


def _generic_momentum(spec: StrategySpec, params: dict) -> type[Strategy]:
    """Fallback for unknown templates — uses simple momentum."""
    lookback = params.get("lookback", 252)
    return _momentum_timeseries(spec, {"lookback": lookback, "threshold": 0.0})


# ── Helpers ──────────────────────────────────────────────────────────


def _position_size(spec: StrategySpec) -> float:
    """Calculate position size fraction from spec risk params."""
    return spec.risk.max_position_pct


def _calc_rsi(series: pd.Series, period: int) -> pd.Series:
    """Calculate RSI indicator."""
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("inf"))
    return 100 - (100 / (1 + rs))
