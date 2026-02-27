"""NT micro-backtest signal extraction for live deployment.

Runs a short backtest on trailing bar data using the same NautilusTrader
strategy classes validated in Phase 2. This ensures the live deployer uses
the exact same signal logic as the validated backtest — closing the gap
between the signal-based path (src.core.signals) and the stateful NT
strategy classes.

Falls back to the existing signal-based path when NautilusTrader is
unavailable.
"""

from __future__ import annotations

import logging

import pandas as pd

from src.strategies.spec import StrategySpec

logger = logging.getLogger(__name__)


def compute_nt_signals(
    spec: StrategySpec,
    prices: dict[str, pd.DataFrame],
    initial_cash: int = 100_000,
) -> dict[str, str]:
    """Compute signals by running micro-backtest per symbol using NT strategy.

    Uses the exact same BacktestEngine + strategy classes as
    validation/translator.py.  Falls back to src.live.signals if NT
    is unavailable or translation fails.

    Args:
        spec: Strategy specification.
        prices: {symbol: OHLCV DataFrame} with DatetimeIndex.
        initial_cash: Starting cash for the micro-backtest.

    Returns:
        {symbol: "long" | "flat"} for each symbol.
    """
    from src.validation.translator import is_nautilus_available, translate_nautilus

    if not is_nautilus_available():
        from src.live.signals import compute_signals
        return compute_signals(spec, prices)

    nt_result = translate_nautilus(spec)
    if nt_result is None:
        from src.live.signals import compute_signals
        return compute_signals(spec, prices)

    strategy_cls, config_kwargs = nt_result
    signals: dict[str, str] = {}

    for symbol, df in prices.items():
        if len(df) < 50:
            signals[symbol] = "flat"
            continue
        try:
            signals[symbol] = _run_micro_backtest(
                strategy_cls, config_kwargs, symbol, df, initial_cash,
            )
        except Exception as e:
            logger.warning(
                "NT micro-backtest failed for %s, falling back to signal: %s",
                symbol, e,
            )
            # Per-symbol fallback
            from src.core.signals import compute_signal
            template = spec.template.split("/")[-1] if "/" in spec.template else spec.template
            signals[symbol] = compute_signal(template, df, spec.parameters)

    return signals


def _run_micro_backtest(
    strategy_cls: type,
    config_kwargs: dict,
    symbol: str,
    df: pd.DataFrame,
    initial_cash: int,
) -> str:
    """Run NT BacktestEngine on trailing bars, return "long" or "flat".

    Setup mirrors validator.py _run_single_nt_backtest() — same venue,
    instrument, fill model, and strategy config.
    """
    import inspect

    from nautilus_trader.backtest.engine import BacktestEngine
    from nautilus_trader.backtest.models import FillModel
    from nautilus_trader.config import BacktestEngineConfig
    from nautilus_trader.model.currencies import USD
    from nautilus_trader.model.enums import AccountType, OmsType
    from nautilus_trader.model.identifiers import Venue
    from nautilus_trader.model.objects import Money

    from src.validation.translator import create_equity_instrument, dataframe_to_bars

    venue = Venue("XNAS")
    instrument = create_equity_instrument(symbol, "XNAS")
    if instrument is None:
        return "flat"

    engine_config = BacktestEngineConfig(logging_config=None)
    engine = BacktestEngine(config=engine_config)

    fill_model = FillModel(
        prob_fill_on_limit=0.95,
        prob_fill_on_stop=0.95,
        prob_slippage=0.5,
        random_seed=42,
    )
    engine.add_venue(
        venue=venue,
        oms_type=OmsType.HEDGING,
        account_type=AccountType.CASH,
        base_currency=USD,
        starting_balances=[Money(initial_cash, USD)],
        fill_model=fill_model,
    )

    engine.add_instrument(instrument)
    bars = dataframe_to_bars(df, instrument.id)
    engine.add_data(bars)

    # Build strategy config using same pattern as validator
    instrument_id_str = f"{symbol}.XNAS"
    strategy_config_kwargs = {**config_kwargs, "instrument_id": instrument_id_str}

    sig = inspect.signature(strategy_cls.__init__)
    config_param = list(sig.parameters.values())[1]  # First after self
    config_cls = config_param.annotation
    if config_cls is inspect.Parameter.empty:
        return "flat"

    config = config_cls(**strategy_config_kwargs)
    strategy = strategy_cls(config=config)
    engine.add_strategy(strategy)

    engine.run()

    # Check if strategy ended with an open position
    has_position = any(p.is_open for p in engine.cache.positions())

    engine.dispose()
    return "long" if has_position else "flat"
