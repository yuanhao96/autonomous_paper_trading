"""NautilusTrader translator: StrategySpec → NautilusTrader Strategy class.

This module translates strategy specifications into NautilusTrader strategies
for realistic backtesting with full execution simulation.

NautilusTrader is an optional dependency. If unavailable, import will fail
gracefully and the validator falls back to backtesting.py with enhanced
cost modeling.

9 category-based NT strategy classes cover all 46 template slugs:
  1. MomentumNTStrategy      — 10 momentum templates
  2. MACrossoverNTStrategy    — 4 MA/trend templates
  3. RSIMeanRevNTStrategy     — 2 RSI/bollinger templates
  4. PairsStatArbNTStrategy   — 5 pairs/reversal templates
  5. TechnicalNTStrategy      — 3 breakout/technical templates
  6. FactorNTStrategy         — 10 factor + value templates
  7. CalendarNTStrategy       — 5 calendar anomaly templates
  8. VolatilityNTStrategy     — 4 volatility templates
  9. ForexCommodityNTStrategy — 4 forex + commodity templates

Requires: nautilus_trader >= 1.200.0, Python >= 3.11
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

from src.strategies.spec import StrategySpec

logger = logging.getLogger(__name__)

# Lazy import guard — NautilusTrader Cython extensions may not be available
_NT_AVAILABLE = False
try:
    from nautilus_trader.config import StrategyConfig
    from nautilus_trader.model.enums import OrderSide, TimeInForce
    from nautilus_trader.model.identifiers import InstrumentId

    # Test if the Cython backtest engine works (macOS binary issue on Py3.10)
    from nautilus_trader.trading.strategy import Strategy as NTStrategy

    _NT_AVAILABLE = True
except (ImportError, OSError) as e:
    logger.info("NautilusTrader not available: %s. Using backtesting.py fallback.", e)
    NTStrategy = None  # type: ignore[assignment, misc]
    StrategyConfig = None  # type: ignore[assignment, misc]


def is_nautilus_available() -> bool:
    """Check if NautilusTrader is importable and functional."""
    return _NT_AVAILABLE


def translate_nautilus(spec: StrategySpec) -> tuple[type, dict] | None:
    """Translate a StrategySpec into a NautilusTrader Strategy class + config.

    Returns None if NautilusTrader is not available.

    Args:
        spec: Strategy specification.

    Returns:
        Tuple of (NTStrategy subclass, config kwargs dict), or None.
    """
    if not _NT_AVAILABLE:
        logger.warning("NautilusTrader not available — cannot translate.")
        return None

    template = spec.template.split("/")[-1] if "/" in spec.template else spec.template
    params = spec.parameters

    entry = _BUILDERS.get(template)
    if entry is None:
        # Default to momentum
        logger.warning("No NT builder for '%s', defaulting to MomentumNTStrategy", template)
        entry = _BUILDERS["time-series-momentum"]

    strategy_cls, config_cls, default_kwargs = entry
    # Merge spec params into config kwargs (spec params override defaults)
    config_kwargs = {**default_kwargs}
    fields = getattr(config_cls, "__dataclass_fields__", {})
    for k, v in params.items():
        if k in fields:
            config_kwargs[k] = v
    config_kwargs["position_pct"] = spec.risk.max_position_pct

    return (strategy_cls, config_kwargs)


# ── Data conversion helpers ──────────────────────────────────────────


def dataframe_to_bars(
    df: pd.DataFrame, instrument_id: Any
) -> list:
    """Convert pandas OHLCV DataFrame to NautilusTrader Bar objects.

    Args:
        df: OHLCV DataFrame with DatetimeIndex.
        instrument_id: NT InstrumentId instance.

    Returns:
        List of NT Bar objects.
    """
    if not _NT_AVAILABLE:
        return []

    from nautilus_trader.model.data import Bar, BarType
    from nautilus_trader.model.objects import Price, Quantity

    bar_type = BarType.from_str(f"{instrument_id}-1-DAY-LAST-EXTERNAL")
    bars = []
    for ts, row in df.iterrows():
        ts_ns = int(pd.Timestamp(ts).timestamp() * 1_000_000_000)
        bar = Bar(
            bar_type=bar_type,
            open=Price.from_str(f"{row['Open']:.2f}"),
            high=Price.from_str(f"{row['High']:.2f}"),
            low=Price.from_str(f"{row['Low']:.2f}"),
            close=Price.from_str(f"{row['Close']:.2f}"),
            volume=Quantity.from_int(int(row.get("Volume", 0))),
            ts_event=ts_ns,
            ts_init=ts_ns,
        )
        bars.append(bar)
    return bars


def create_equity_instrument(
    symbol: str, venue: str = "XNAS"
) -> Any:
    """Create a NautilusTrader Equity instrument for backtesting.

    Args:
        symbol: Ticker symbol (e.g., "SPY").
        venue: Exchange venue (default "XNAS" for NASDAQ).

    Returns:
        NT Equity instrument, or None if NT unavailable.
    """
    if not _NT_AVAILABLE:
        return None

    from nautilus_trader.model.currencies import USD
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
    from nautilus_trader.model.instruments import Equity
    from nautilus_trader.model.objects import Price, Quantity

    instrument_id = InstrumentId(Symbol(symbol), Venue(venue))
    return Equity(
        instrument_id=instrument_id,
        raw_symbol=Symbol(symbol),
        currency=USD,
        price_precision=2,
        price_increment=Price.from_str("0.01"),
        lot_size=Quantity.from_int(1),
        max_quantity=Quantity.from_int(1_000_000),
        min_quantity=Quantity.from_int(1),
        margin_init=Decimal("0"),
        margin_maint=Decimal("0"),
        maker_fee=Decimal("0.001"),
        taker_fee=Decimal("0.002"),
        ts_event=0,
        ts_init=0,
    )


# ── NautilusTrader Strategy Classes ─────────────────────────────────
#
# 9 category-based classes, each handling multiple template slugs via
# config params. Only defined when NautilusTrader is importable.

if _NT_AVAILABLE:

    # ── Shared helpers ───────────────────────────────────────────

    def _calc_quantity_from_portfolio(strategy, instrument_id, position_pct: float):
        """Account-balance-aware position sizing."""
        from nautilus_trader.model.objects import Quantity

        try:
            account = strategy.portfolio.account(instrument_id.venue)
            if account is not None:
                balance = float(account.balance_total().as_double())
                prices = getattr(strategy, "_prices", [])
                last_price = prices[-1] if prices else 100.0
                target_value = balance * position_pct
                shares = int(target_value / max(last_price, 0.01))
                return Quantity.from_int(max(shares, 1))
        except Exception:
            pass
        return Quantity.from_int(100)

    def _bar_type_for(instrument_id):
        from nautilus_trader.model.data import BarType

        return BarType.from_str(f"{instrument_id}-1-DAY-LAST-EXTERNAL")

    # ── 1. MomentumNTStrategy ────────────────────────────────────

    class MomentumConfig(StrategyConfig, frozen=True):
        instrument_id: str = "SPY.XNAS"
        lookback: int = 252
        threshold: float = 0.0
        position_pct: float = 0.10

    class MomentumNTStrategy(NTStrategy):
        """Time-series / cross-sectional momentum for NautilusTrader.

        Covers: momentum-effect-in-stocks, time-series-momentum,
        time-series-momentum-effect, dual-momentum, sector-momentum,
        asset-class-momentum, asset-class-trend-following,
        momentum-and-reversal-combined-with-volatility-effect-in-stocks,
        residual-momentum, combining-momentum-effect-with-volume
        """

        def __init__(self, config: MomentumConfig) -> None:
            super().__init__(config)
            self.instrument_id = InstrumentId.from_str(config.instrument_id)
            self.lookback = config.lookback
            self.threshold = config.threshold
            self.position_pct = config.position_pct
            self._prices: list[float] = []

        def on_start(self) -> None:
            self.subscribe_bars(_bar_type_for(self.instrument_id))

        def on_bar(self, bar) -> None:
            self._prices.append(float(bar.close))
            if len(self._prices) < self.lookback + 1:
                return

            momentum = self._prices[-1] / self._prices[-self.lookback] - 1

            if momentum > self.threshold and not self.portfolio.is_net_long(
                self.instrument_id
            ):
                self._enter_long()
            elif momentum < -self.threshold and self.portfolio.is_net_long(
                self.instrument_id
            ):
                self._close_position()

        def _enter_long(self) -> None:
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=OrderSide.BUY,
                quantity=self._calc_quantity(),
                time_in_force=TimeInForce.IOC,
            )
            self.submit_order(order)

        def _close_position(self) -> None:
            for position in self.cache.positions(instrument_id=self.instrument_id):
                if position.is_open:
                    self.close_position(position)

        def _calc_quantity(self):
            return _calc_quantity_from_portfolio(
                self, self.instrument_id, self.position_pct
            )

    # ── 2. MACrossoverNTStrategy ─────────────────────────────────

    class MACrossoverConfig(StrategyConfig, frozen=True):
        instrument_id: str = "SPY.XNAS"
        fast_period: int = 10
        slow_period: int = 50
        position_pct: float = 0.10

    class MACrossoverNTStrategy(NTStrategy):
        """Moving average crossover / trend following for NautilusTrader.

        Covers: moving-average-crossover, trend-following,
        ichimoku-clouds-in-energy-sector, paired-switching
        """

        def __init__(self, config: MACrossoverConfig) -> None:
            super().__init__(config)
            self.instrument_id = InstrumentId.from_str(config.instrument_id)
            self.fast_period = config.fast_period
            self.slow_period = config.slow_period
            self.position_pct = config.position_pct
            self._prices: list[float] = []

        def on_start(self) -> None:
            self.subscribe_bars(_bar_type_for(self.instrument_id))

        def on_bar(self, bar) -> None:
            self._prices.append(float(bar.close))
            if len(self._prices) < self.slow_period + 1:
                return

            fast_ma = np.mean(self._prices[-self.fast_period :])
            slow_ma = np.mean(self._prices[-self.slow_period :])
            prev_fast = np.mean(self._prices[-self.fast_period - 1 : -1])
            prev_slow = np.mean(self._prices[-self.slow_period - 1 : -1])

            if prev_fast <= prev_slow and fast_ma > slow_ma:
                if not self.portfolio.is_net_long(self.instrument_id):
                    self._enter_long()
            elif prev_fast >= prev_slow and fast_ma < slow_ma:
                if self.portfolio.is_net_long(self.instrument_id):
                    self._close_position()

        def _enter_long(self) -> None:
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=OrderSide.BUY,
                quantity=self._calc_quantity(),
                time_in_force=TimeInForce.IOC,
            )
            self.submit_order(order)

        def _close_position(self) -> None:
            for position in self.cache.positions(instrument_id=self.instrument_id):
                if position.is_open:
                    self.close_position(position)

        def _calc_quantity(self):
            return _calc_quantity_from_portfolio(
                self, self.instrument_id, self.position_pct
            )

    # ── 3. RSIMeanRevNTStrategy ──────────────────────────────────

    class RSIMeanRevConfig(StrategyConfig, frozen=True):
        instrument_id: str = "SPY.XNAS"
        rsi_period: int = 14
        oversold: float = 30.0
        overbought: float = 70.0
        position_pct: float = 0.10

    class RSIMeanRevNTStrategy(NTStrategy):
        """RSI / Bollinger mean reversion for NautilusTrader.

        Covers: mean-reversion-rsi, mean-reversion-bollinger
        """

        def __init__(self, config: RSIMeanRevConfig) -> None:
            super().__init__(config)
            self.instrument_id = InstrumentId.from_str(config.instrument_id)
            self.rsi_period = config.rsi_period
            self.oversold = config.oversold
            self.overbought = config.overbought
            self.position_pct = config.position_pct
            self._prices: list[float] = []

        def on_start(self) -> None:
            self.subscribe_bars(_bar_type_for(self.instrument_id))

        def on_bar(self, bar) -> None:
            self._prices.append(float(bar.close))
            if len(self._prices) < self.rsi_period + 2:
                return

            rsi = self._calc_rsi()

            if rsi < self.oversold and not self.portfolio.is_net_long(
                self.instrument_id
            ):
                self._enter_long()
            elif rsi > self.overbought and self.portfolio.is_net_long(
                self.instrument_id
            ):
                self._close_position()

        def _calc_rsi(self) -> float:
            prices = pd.Series(self._prices)
            delta = prices.diff().dropna()
            gain = delta.clip(lower=0).rolling(self.rsi_period).mean()
            loss = (-delta.clip(upper=0)).rolling(self.rsi_period).mean()
            if loss.iloc[-1] == 0:
                return 100.0
            rs = gain.iloc[-1] / loss.iloc[-1]
            return 100.0 - (100.0 / (1.0 + rs))

        def _enter_long(self) -> None:
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=OrderSide.BUY,
                quantity=self._calc_quantity(),
                time_in_force=TimeInForce.IOC,
            )
            self.submit_order(order)

        def _close_position(self) -> None:
            for position in self.cache.positions(instrument_id=self.instrument_id):
                if position.is_open:
                    self.close_position(position)

        def _calc_quantity(self):
            return _calc_quantity_from_portfolio(
                self, self.instrument_id, self.position_pct
            )

    # ── 4. PairsStatArbNTStrategy ────────────────────────────────

    class PairsStatArbConfig(StrategyConfig, frozen=True):
        instrument_id: str = "SPY.XNAS"
        lookback: int = 60
        entry_z: float = 2.0
        exit_z: float = 0.5
        position_pct: float = 0.10

    class PairsStatArbNTStrategy(NTStrategy):
        """Z-score mean reversion for pairs / stat arb templates.

        Covers: pairs-trading, pairs-trading-with-stocks,
        mean-reversion-statistical-arbitrage-in-stocks,
        short-term-reversal, short-term-reversal-strategy-in-stocks
        """

        def __init__(self, config: PairsStatArbConfig) -> None:
            super().__init__(config)
            self.instrument_id = InstrumentId.from_str(config.instrument_id)
            self.lookback = config.lookback
            self.entry_z = config.entry_z
            self.exit_z = config.exit_z
            self.position_pct = config.position_pct
            self._prices: list[float] = []

        def on_start(self) -> None:
            self.subscribe_bars(_bar_type_for(self.instrument_id))

        def on_bar(self, bar) -> None:
            self._prices.append(float(bar.close))
            if len(self._prices) < self.lookback + 1:
                return

            window = self._prices[-self.lookback :]
            mean = np.mean(window)
            std = np.std(window)
            if std < 1e-8:
                return

            z = (self._prices[-1] - mean) / std

            # Buy when z-score is very negative (price is low)
            if z < -self.entry_z and not self.portfolio.is_net_long(
                self.instrument_id
            ):
                self._enter_long()
            # Exit when z-score reverts to near zero
            elif z > -self.exit_z and self.portfolio.is_net_long(self.instrument_id):
                self._close_position()

        def _enter_long(self) -> None:
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=OrderSide.BUY,
                quantity=self._calc_quantity(),
                time_in_force=TimeInForce.IOC,
            )
            self.submit_order(order)

        def _close_position(self) -> None:
            for position in self.cache.positions(instrument_id=self.instrument_id):
                if position.is_open:
                    self.close_position(position)

        def _calc_quantity(self):
            return _calc_quantity_from_portfolio(
                self, self.instrument_id, self.position_pct
            )

    # ── 5. TechnicalNTStrategy ───────────────────────────────────

    class TechnicalConfig(StrategyConfig, frozen=True):
        instrument_id: str = "SPY.XNAS"
        lookback: int = 20
        k1: float = 0.5
        k2: float = 0.5
        position_pct: float = 0.10

    class TechnicalNTStrategy(NTStrategy):
        """Breakout / channel-based technical strategies for NautilusTrader.

        Covers: breakout, dual-thrust-trading-algorithm,
        dual-thrust-trading-algorithm (alternate)
        """

        def __init__(self, config: TechnicalConfig) -> None:
            super().__init__(config)
            self.instrument_id = InstrumentId.from_str(config.instrument_id)
            self.lookback = config.lookback
            self.k1 = config.k1
            self.k2 = config.k2
            self.position_pct = config.position_pct
            self._highs: list[float] = []
            self._lows: list[float] = []
            self._prices: list[float] = []

        def on_start(self) -> None:
            self.subscribe_bars(_bar_type_for(self.instrument_id))

        def on_bar(self, bar) -> None:
            self._highs.append(float(bar.high))
            self._lows.append(float(bar.low))
            self._prices.append(float(bar.close))
            if len(self._prices) < self.lookback + 1:
                return

            # Channel breakout: buy above upper channel
            recent_high = max(self._highs[-self.lookback :])
            recent_low = min(self._lows[-self.lookback :])
            channel_range = recent_high - recent_low
            upper = recent_low + self.k1 * channel_range
            lower = recent_high - self.k2 * channel_range

            price = self._prices[-1]
            if price > upper and not self.portfolio.is_net_long(self.instrument_id):
                self._enter_long()
            elif price < lower and self.portfolio.is_net_long(self.instrument_id):
                self._close_position()

        def _enter_long(self) -> None:
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=OrderSide.BUY,
                quantity=self._calc_quantity(),
                time_in_force=TimeInForce.IOC,
            )
            self.submit_order(order)

        def _close_position(self) -> None:
            for position in self.cache.positions(instrument_id=self.instrument_id):
                if position.is_open:
                    self.close_position(position)

        def _calc_quantity(self):
            return _calc_quantity_from_portfolio(
                self, self.instrument_id, self.position_pct
            )

    # ── 6. FactorNTStrategy ──────────────────────────────────────

    class FactorConfig(StrategyConfig, frozen=True):
        instrument_id: str = "SPY.XNAS"
        lookback: int = 126
        position_pct: float = 0.10

    class FactorNTStrategy(NTStrategy):
        """Factor / value investing proxy for NautilusTrader.

        Uses price-based momentum as a proxy for factor exposure,
        since fundamental data isn't available in the NT backtest engine.

        Covers: fama-french-five-factors, beta-factors-in-stocks,
        liquidity-effect-in-stocks, accrual-anomaly, earnings-quality-factor,
        value-factor, price-earnings-anomaly, book-to-market-value-anomaly,
        small-capitalization-stocks-premium-anomaly, g-score-investing
        """

        def __init__(self, config: FactorConfig) -> None:
            super().__init__(config)
            self.instrument_id = InstrumentId.from_str(config.instrument_id)
            self.lookback = config.lookback
            self.position_pct = config.position_pct
            self._prices: list[float] = []

        def on_start(self) -> None:
            self.subscribe_bars(_bar_type_for(self.instrument_id))

        def on_bar(self, bar) -> None:
            self._prices.append(float(bar.close))
            if len(self._prices) < self.lookback + 1:
                return

            # Trend-based factor proxy: positive momentum = long
            ret = self._prices[-1] / self._prices[-self.lookback] - 1
            if ret > 0 and not self.portfolio.is_net_long(self.instrument_id):
                self._enter_long()
            elif ret < 0 and self.portfolio.is_net_long(self.instrument_id):
                self._close_position()

        def _enter_long(self) -> None:
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=OrderSide.BUY,
                quantity=self._calc_quantity(),
                time_in_force=TimeInForce.IOC,
            )
            self.submit_order(order)

        def _close_position(self) -> None:
            for position in self.cache.positions(instrument_id=self.instrument_id):
                if position.is_open:
                    self.close_position(position)

        def _calc_quantity(self):
            return _calc_quantity_from_portfolio(
                self, self.instrument_id, self.position_pct
            )

    # ── 7. CalendarNTStrategy ────────────────────────────────────

    class CalendarConfig(StrategyConfig, frozen=True):
        instrument_id: str = "SPY.XNAS"
        entry_day: int = -2  # Days relative to month-end (negative = before)
        exit_day: int = 3  # Days into new month
        position_pct: float = 0.10

    class CalendarNTStrategy(NTStrategy):
        """Calendar anomaly strategies for NautilusTrader.

        Covers: turn-of-the-month-in-equity-indexes, january-effect-in-stocks,
        pre-holiday-effect, overnight-anomaly,
        seasonality-effect-same-calendar-month
        """

        def __init__(self, config: CalendarConfig) -> None:
            super().__init__(config)
            self.instrument_id = InstrumentId.from_str(config.instrument_id)
            self.entry_day = config.entry_day
            self.exit_day = config.exit_day
            self.position_pct = config.position_pct
            self._bar_count = 0
            self._prices: list[float] = []

        def on_start(self) -> None:
            self.subscribe_bars(_bar_type_for(self.instrument_id))

        def on_bar(self, bar) -> None:
            self._prices.append(float(bar.close))
            self._bar_count += 1

            # Approximate calendar logic using bar timestamps
            ts = pd.Timestamp(bar.ts_event, unit="ns")
            day_of_month = ts.day
            days_in_month = ts.days_in_month

            # Entry: near month-end
            days_to_end = days_in_month - day_of_month
            if days_to_end <= abs(self.entry_day) and not self.portfolio.is_net_long(
                self.instrument_id
            ):
                self._enter_long()
            # Exit: early in new month
            elif day_of_month <= self.exit_day and self.portfolio.is_net_long(
                self.instrument_id
            ):
                self._close_position()

        def _enter_long(self) -> None:
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=OrderSide.BUY,
                quantity=self._calc_quantity(),
                time_in_force=TimeInForce.IOC,
            )
            self.submit_order(order)

        def _close_position(self) -> None:
            for position in self.cache.positions(instrument_id=self.instrument_id):
                if position.is_open:
                    self.close_position(position)

        def _calc_quantity(self):
            return _calc_quantity_from_portfolio(
                self, self.instrument_id, self.position_pct
            )

    # ── 8. VolatilityNTStrategy ──────────────────────────────────

    class VolatilityConfig(StrategyConfig, frozen=True):
        instrument_id: str = "SPY.XNAS"
        lookback: int = 20
        vol_threshold: float = 0.20  # Annualized vol threshold
        position_pct: float = 0.10

    class VolatilityNTStrategy(NTStrategy):
        """Volatility-based strategies for NautilusTrader.

        Covers: volatility-effect-in-stocks, volatility-risk-premium-effect,
        vix-predicts-stock-index-returns,
        leveraged-etfs-with-systematic-risk-management
        """

        def __init__(self, config: VolatilityConfig) -> None:
            super().__init__(config)
            self.instrument_id = InstrumentId.from_str(config.instrument_id)
            self.lookback = config.lookback
            self.vol_threshold = config.vol_threshold
            self.position_pct = config.position_pct
            self._prices: list[float] = []

        def on_start(self) -> None:
            self.subscribe_bars(_bar_type_for(self.instrument_id))

        def on_bar(self, bar) -> None:
            self._prices.append(float(bar.close))
            if len(self._prices) < self.lookback + 2:
                return

            # Calculate realized volatility
            returns = np.diff(np.log(self._prices[-self.lookback - 1 :]))
            realized_vol = float(np.std(returns) * np.sqrt(252))

            # Low vol regime: go long (volatility risk premium)
            if realized_vol < self.vol_threshold and not self.portfolio.is_net_long(
                self.instrument_id
            ):
                self._enter_long()
            elif realized_vol > self.vol_threshold * 1.5 and self.portfolio.is_net_long(
                self.instrument_id
            ):
                self._close_position()

        def _enter_long(self) -> None:
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=OrderSide.BUY,
                quantity=self._calc_quantity(),
                time_in_force=TimeInForce.IOC,
            )
            self.submit_order(order)

        def _close_position(self) -> None:
            for position in self.cache.positions(instrument_id=self.instrument_id):
                if position.is_open:
                    self.close_position(position)

        def _calc_quantity(self):
            return _calc_quantity_from_portfolio(
                self, self.instrument_id, self.position_pct
            )

    # ── 9. ForexCommodityNTStrategy ──────────────────────────────

    class ForexCommodityConfig(StrategyConfig, frozen=True):
        instrument_id: str = "SPY.XNAS"
        lookback: int = 63
        position_pct: float = 0.10

    class ForexCommodityNTStrategy(NTStrategy):
        """Momentum/mean-reversion for forex & commodity templates.

        Covers: forex-carry-trade, combining-mean-reversion-and-momentum-in-forex,
        term-structure-effect-in-commodities, gold-market-timing
        """

        def __init__(self, config: ForexCommodityConfig) -> None:
            super().__init__(config)
            self.instrument_id = InstrumentId.from_str(config.instrument_id)
            self.lookback = config.lookback
            self.position_pct = config.position_pct
            self._prices: list[float] = []

        def on_start(self) -> None:
            self.subscribe_bars(_bar_type_for(self.instrument_id))

        def on_bar(self, bar) -> None:
            self._prices.append(float(bar.close))
            if len(self._prices) < self.lookback + 1:
                return

            # Trend following: positive return over lookback → long
            ret = self._prices[-1] / self._prices[-self.lookback] - 1
            if ret > 0 and not self.portfolio.is_net_long(self.instrument_id):
                self._enter_long()
            elif ret < 0 and self.portfolio.is_net_long(self.instrument_id):
                self._close_position()

        def _enter_long(self) -> None:
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=OrderSide.BUY,
                quantity=self._calc_quantity(),
                time_in_force=TimeInForce.IOC,
            )
            self.submit_order(order)

        def _close_position(self) -> None:
            for position in self.cache.positions(instrument_id=self.instrument_id):
                if position.is_open:
                    self.close_position(position)

        def _calc_quantity(self):
            return _calc_quantity_from_portfolio(
                self, self.instrument_id, self.position_pct
            )


# ── Builder registry: template slug → (strategy_cls, config_cls, default_kwargs)


def _build_registry() -> dict[str, tuple[type, type, dict]]:
    """Build the full 46-entry template → NT strategy mapping."""
    if not _NT_AVAILABLE:
        return {}

    mom = (
        MomentumNTStrategy, MomentumConfig,
        {"lookback": 252, "threshold": 0.0},
    )
    ma = (
        MACrossoverNTStrategy, MACrossoverConfig,
        {"fast_period": 10, "slow_period": 50},
    )
    rsi = (
        RSIMeanRevNTStrategy, RSIMeanRevConfig,
        {"rsi_period": 14, "oversold": 30.0, "overbought": 70.0},
    )
    pairs = (
        PairsStatArbNTStrategy, PairsStatArbConfig,
        {"lookback": 60, "entry_z": 2.0, "exit_z": 0.5},
    )
    tech = (
        TechnicalNTStrategy, TechnicalConfig,
        {"lookback": 20, "k1": 0.5, "k2": 0.5},
    )
    factor = (FactorNTStrategy, FactorConfig, {"lookback": 126})
    cal = (
        CalendarNTStrategy, CalendarConfig,
        {"entry_day": -2, "exit_day": 3},
    )
    vol = (
        VolatilityNTStrategy, VolatilityConfig,
        {"lookback": 20, "vol_threshold": 0.20},
    )
    fxcom = (
        ForexCommodityNTStrategy, ForexCommodityConfig,
        {"lookback": 63},
    )

    # Short aliases for inline overrides
    mom_126 = (
        MomentumNTStrategy, MomentumConfig,
        {"lookback": 126, "threshold": 0.0},
    )
    pairs_short = (
        PairsStatArbNTStrategy, PairsStatArbConfig,
        {"lookback": 10, "entry_z": 1.5, "exit_z": 0.5},
    )

    return {
        # ── Momentum (10) ──────────────────────────────────────
        "momentum-effect-in-stocks": mom,
        "time-series-momentum": mom,
        "time-series-momentum-effect": mom,
        "dual-momentum": mom,
        "sector-momentum": mom,
        "asset-class-momentum": mom,
        "asset-class-trend-following": (
            MACrossoverNTStrategy, MACrossoverConfig,
            {"fast_period": 20, "slow_period": 200},
        ),
        "momentum-and-reversal-combined-with-volatility"
        "-effect-in-stocks": mom_126,
        "residual-momentum": mom_126,
        "combining-momentum-effect-with-volume": mom,
        # ── Mean Reversion (2) ─────────────────────────────────
        "mean-reversion-rsi": rsi,
        "mean-reversion-bollinger": (
            RSIMeanRevNTStrategy, RSIMeanRevConfig,
            {"rsi_period": 20, "oversold": 30.0, "overbought": 70.0},
        ),
        # ── Pairs / Stat Arb (5) ───────────────────────────────
        "pairs-trading": pairs,
        "pairs-trading-with-stocks": pairs,
        "mean-reversion-statistical-arbitrage-in-stocks": pairs,
        "short-term-reversal": pairs_short,
        "short-term-reversal-strategy-in-stocks": pairs_short,
        # ── Technical (6) ──────────────────────────────────────
        "moving-average-crossover": ma,
        "breakout": (
            TechnicalNTStrategy, TechnicalConfig,
            {"lookback": 20, "k1": 0.7, "k2": 0.7},
        ),
        "trend-following": ma,
        "ichimoku-clouds-in-energy-sector": (
            MACrossoverNTStrategy, MACrossoverConfig,
            {"fast_period": 9, "slow_period": 26},
        ),
        "dual-thrust-trading-algorithm": tech,
        "paired-switching": (
            MACrossoverNTStrategy, MACrossoverConfig,
            {"fast_period": 20, "slow_period": 120},
        ),
        # ── Factor (5) ─────────────────────────────────────────
        "fama-french-five-factors": factor,
        "beta-factors-in-stocks": factor,
        "liquidity-effect-in-stocks": factor,
        "accrual-anomaly": factor,
        "earnings-quality-factor": factor,
        # ── Value (5) ──────────────────────────────────────────
        "value-factor": factor,
        "price-earnings-anomaly": factor,
        "book-to-market-value-anomaly": factor,
        "small-capitalization-stocks-premium-anomaly": factor,
        "g-score-investing": factor,
        # ── Calendar (5) ───────────────────────────────────────
        "turn-of-the-month-in-equity-indexes": cal,
        "january-effect-in-stocks": cal,
        "pre-holiday-effect": (
            CalendarNTStrategy, CalendarConfig,
            {"entry_day": -1, "exit_day": 1},
        ),
        "overnight-anomaly": (
            CalendarNTStrategy, CalendarConfig,
            {"entry_day": -1, "exit_day": 1},
        ),
        "seasonality-effect-same-calendar-month": cal,
        # ── Volatility (4) ─────────────────────────────────────
        "volatility-effect-in-stocks": vol,
        "volatility-risk-premium-effect": vol,
        "vix-predicts-stock-index-returns": (
            VolatilityNTStrategy, VolatilityConfig,
            {"lookback": 20, "vol_threshold": 0.25},
        ),
        "leveraged-etfs-with-systematic-risk-management": (
            VolatilityNTStrategy, VolatilityConfig,
            {"lookback": 20, "vol_threshold": 0.15},
        ),
        # ── Forex (2) ──────────────────────────────────────────
        "forex-carry-trade": fxcom,
        "combining-mean-reversion-and-momentum-in-forex": fxcom,
        # ── Commodities (2) ────────────────────────────────────
        "term-structure-effect-in-commodities": fxcom,
        "gold-market-timing": (
            ForexCommodityNTStrategy, ForexCommodityConfig,
            {"lookback": 126},
        ),
    }


_BUILDERS = _build_registry()
