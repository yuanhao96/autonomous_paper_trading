"""Validation pipeline — Phase 2 realistic backtesting across market regimes.

When NautilusTrader is available:
  Uses NT engine with full reality modeling (slippage, fees, partial fills).

When NautilusTrader is unavailable (current Python 3.10 environment):
  Falls back to backtesting.py with enhanced cost modeling:
  - Higher commission (simulates spread + slippage)
  - Per-regime backtesting
  - Capacity analysis from volume data

Both paths produce the same StrategyResult format for downstream consumption.
"""

from __future__ import annotations

import logging
import time

import numpy as np
import pandas as pd
from backtesting import Backtest

from src.core.config import Settings
from src.data.manager import DataManager
from src.screening.translator import translate
from src.strategies.spec import RegimeResult, StrategyResult, StrategySpec
from src.validation.capacity import quick_capacity_check
from src.validation.filters import ValidationFilters
from src.validation.regimes import RegimePeriod, select_regime_periods
from src.validation.translator import (
    create_equity_instrument,
    dataframe_to_bars,
    is_nautilus_available,
    translate_nautilus,
)

logger = logging.getLogger(__name__)


class Validator:
    """Phase 2 validation pipeline.

    Flow:
    1. Detect market regimes from a benchmark (SPY)
    2. For each regime period, run backtest with enhanced cost modeling
    3. Aggregate regime results into StrategyResult
    4. Run capacity analysis
    5. Apply validation pass/fail filters
    6. Return StrategyResult with regime breakdown
    """

    def __init__(
        self,
        data_manager: DataManager | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._dm = data_manager or DataManager()
        self._settings = settings or Settings()
        self._filters = ValidationFilters(self._settings)

    def validate(
        self,
        spec: StrategySpec,
        symbols: list[str],
        benchmark: str = "SPY",
    ) -> StrategyResult:
        """Validate a strategy across multiple market regimes.

        Args:
            spec: Strategy specification (should have passed screening).
            symbols: List of symbols to test against.
            benchmark: Symbol to use for regime detection (default SPY).

        Returns:
            StrategyResult with regime breakdown and capacity info.
        """
        t0 = time.time()

        if is_nautilus_available():
            logger.info("Using NautilusTrader for validation")
            return self._validate_nautilus(spec, symbols, benchmark, t0)
        else:
            logger.info("Using backtesting.py fallback for validation")
            return self._validate_backtest_fallback(spec, symbols, benchmark, t0)

    def _validate_backtest_fallback(
        self,
        spec: StrategySpec,
        symbols: list[str],
        benchmark: str,
        t0: float,
    ) -> StrategyResult:
        """Validate using backtesting.py with enhanced cost modeling."""

        # Step 1: Get benchmark data for regime detection (5 years)
        bench_data = self._dm.get_ohlcv(benchmark, period="5y")
        if bench_data.empty:
            return self._fail_result(spec.id, "No benchmark data", t0)

        # Step 2: Detect market regimes
        regimes = select_regime_periods(bench_data["Close"], min_days=30)
        if not regimes:
            return self._fail_result(spec.id, "Could not detect market regimes", t0)

        logger.info("Detected %d regime periods: %s", len(regimes), list(regimes.keys()))

        # Step 3: Get symbol data covering all regime periods
        all_data: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            df = self._dm.get_ohlcv(symbol, period="5y")
            if not df.empty:
                all_data[symbol] = df

        if not all_data:
            return self._fail_result(spec.id, "No data for any symbols", t0)

        # Step 4: Run backtest for each regime with enhanced costs
        regime_results: list[RegimeResult] = []
        all_period_metrics: list[dict] = []

        for regime_name, regime_period in regimes.items():
            period_metrics = self._run_regime_backtest(
                spec, all_data, regime_period, regime_name
            )
            if period_metrics is not None:
                regime_results.append(period_metrics["regime_result"])
                all_period_metrics.append(period_metrics)

        if not regime_results:
            return self._fail_result(spec.id, "All regime backtests failed", t0)

        # Step 5: Aggregate across regimes
        result = self._aggregate_regime_results(spec.id, regime_results, all_period_metrics)
        result.run_duration_seconds = time.time() - t0

        # Step 6: Capacity analysis
        capacity = quick_capacity_check(
            symbols=symbols,
            data=all_data,
            position_pct=spec.risk.max_position_pct,
            max_positions=spec.risk.max_positions,
        )

        # Step 7: Apply validation filters
        filter_result = self._filters.apply(result, capacity=capacity)
        result.passed = filter_result.passed
        if not filter_result.passed:
            result.failure_reason = filter_result.failure_reason
            result.failure_details = "; ".join(
                f"{k}: {v}" for k, v in filter_result.details.items()
            )

        return result

    def _run_regime_backtest(
        self,
        spec: StrategySpec,
        all_data: dict[str, pd.DataFrame],
        regime: RegimePeriod,
        regime_name: str,
    ) -> dict | None:
        """Run backtest for a single market regime period.

        Includes a warmup window before the regime start so strategy
        indicators (e.g., 126-day momentum) have enough history to
        generate signals within the regime period itself.
        """
        initial_cash = self._settings.get("screening.initial_cash", 100000)

        # Enhanced cost model for validation:
        # Base commission + simulated slippage + spread
        base_commission = self._settings.get("screening.commission", 0.002)
        validation_commission = base_commission * 2.5  # ~0.5% total cost per trade

        # Determine warmup needed from strategy parameters
        lookback = spec.parameters.get("lookback", 0)
        slow_period = spec.parameters.get("slow_period", 0)
        warmup_bars = max(lookback, slow_period, 126) + 20  # Extra buffer

        regime_metrics: list[dict] = []

        for symbol, df in all_data.items():
            # Find regime start index and prepend warmup bars
            regime_mask = (df.index >= regime.start) & (df.index <= regime.end)
            regime_only = df[regime_mask]

            if len(regime_only) < 20:
                continue

            # Prepend warmup: take data from (regime.start - warmup_bars) to regime.end
            pre_regime = df[df.index < regime.start]
            if len(pre_regime) >= warmup_bars:
                warmup_data = pre_regime.iloc[-warmup_bars:]
            else:
                warmup_data = pre_regime

            regime_data = pd.concat([warmup_data, regime_only])

            if len(regime_data) < 50:
                continue

            try:
                strategy_cls = translate(spec, regime_data)
                bt = Backtest(
                    regime_data,
                    strategy_cls,
                    cash=initial_cash,
                    commission=validation_commission,
                    exclusive_orders=True,
                    trade_on_close=True,
                    finalize_trades=True,
                )
                stats = bt.run()
                regime_metrics.append(_extract_regime_metrics(stats, symbol))
            except Exception as e:
                logger.warning(
                    "Regime %s backtest failed for %s: %s", regime_name, symbol, e
                )
                continue

        if not regime_metrics:
            return None

        # Average across symbols for this regime
        avg = _average_metrics(regime_metrics)

        regime_result = RegimeResult(
            regime=regime_name,
            period_start=str(regime.start.date()),
            period_end=str(regime.end.date()),
            annual_return=avg["annual_return"],
            sharpe_ratio=avg["sharpe_ratio"],
            max_drawdown=avg["max_drawdown"],
            total_trades=int(avg["total_trades"]),
        )

        return {
            "regime_result": regime_result,
            "avg_metrics": avg,
        }

    def _aggregate_regime_results(
        self,
        spec_id: str,
        regime_results: list[RegimeResult],
        all_metrics: list[dict],
    ) -> StrategyResult:
        """Aggregate regime-level results into an overall StrategyResult."""
        # Weight equally across regimes
        n = len(all_metrics)
        avg_metrics = {k: 0.0 for k in all_metrics[0]["avg_metrics"]}
        for m in all_metrics:
            for k, v in m["avg_metrics"].items():
                avg_metrics[k] += _safe_float(v) / n

        # Total fees = sum of all regime fees
        total_fees = sum(m["avg_metrics"].get("total_fees", 0) for m in all_metrics)

        return StrategyResult(
            spec_id=spec_id,
            phase="validate",
            total_return=avg_metrics.get("total_return", 0),
            annual_return=avg_metrics.get("annual_return", 0),
            sharpe_ratio=avg_metrics.get("sharpe_ratio", 0),
            sortino_ratio=avg_metrics.get("sortino_ratio", 0),
            max_drawdown=avg_metrics.get("max_drawdown", 0),
            win_rate=avg_metrics.get("win_rate", 0),
            profit_factor=avg_metrics.get("profit_factor", 0),
            total_trades=int(avg_metrics.get("total_trades", 0)),
            total_fees=total_fees,
            total_slippage=total_fees * 0.4,  # Estimate 40% of cost is slippage
            regime_results=regime_results,
        )

    def _validate_nautilus(
        self,
        spec: StrategySpec,
        symbols: list[str],
        benchmark: str,
        t0: float,
    ) -> StrategyResult:
        """Validate using NautilusTrader with full reality modeling."""

        # Step 1: Get benchmark data for regime detection
        bench_data = self._dm.get_ohlcv(benchmark, period="5y")
        if bench_data.empty:
            return self._fail_result(spec.id, "No benchmark data", t0)

        regimes = select_regime_periods(bench_data["Close"], min_days=30)
        if not regimes:
            return self._fail_result(spec.id, "Could not detect market regimes", t0)

        logger.info(
            "NT validation: %d regimes: %s", len(regimes), list(regimes.keys())
        )

        # Step 2: Get symbol data
        all_data: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            df = self._dm.get_ohlcv(symbol, period="5y")
            if not df.empty:
                all_data[symbol] = df

        if not all_data:
            return self._fail_result(spec.id, "No data for any symbols", t0)

        # Step 3: Translate spec to NT strategy
        nt_result = translate_nautilus(spec)
        if nt_result is None:
            logger.warning("NT translation failed, falling back to backtesting.py")
            return self._validate_backtest_fallback(spec, symbols, benchmark, t0)

        strategy_cls, config_kwargs = nt_result

        # Step 4: Run backtest for each regime
        regime_results: list[RegimeResult] = []
        all_period_metrics: list[dict] = []

        for regime_name, regime_period in regimes.items():
            period_metrics = self._run_nt_regime_backtest(
                spec, strategy_cls, config_kwargs, all_data,
                regime_period, regime_name,
            )
            if period_metrics is not None:
                regime_results.append(period_metrics["regime_result"])
                all_period_metrics.append(period_metrics)

        if not regime_results:
            logger.warning("All NT regime backtests failed, falling back")
            return self._validate_backtest_fallback(spec, symbols, benchmark, t0)

        # Step 5: Aggregate
        result = self._aggregate_regime_results(
            spec.id, regime_results, all_period_metrics
        )
        result.run_duration_seconds = time.time() - t0

        # Step 6: Capacity analysis
        capacity = quick_capacity_check(
            symbols=symbols,
            data=all_data,
            position_pct=spec.risk.max_position_pct,
            max_positions=spec.risk.max_positions,
        )

        # Step 7: Apply filters
        filter_result = self._filters.apply(result, capacity=capacity)
        result.passed = filter_result.passed
        if not filter_result.passed:
            result.failure_reason = filter_result.failure_reason
            result.failure_details = "; ".join(
                f"{k}: {v}" for k, v in filter_result.details.items()
            )

        return result

    def _run_nt_regime_backtest(
        self,
        spec: StrategySpec,
        strategy_cls: type,
        config_kwargs: dict,
        all_data: dict[str, pd.DataFrame],
        regime: RegimePeriod,
        regime_name: str,
    ) -> dict | None:
        """Run NT backtest for a single regime period across all symbols."""

        initial_cash = self._settings.get("screening.initial_cash", 100000)

        # Determine warmup needed
        lookback = spec.parameters.get("lookback", 0)
        slow_period = spec.parameters.get("slow_period", 0)
        warmup_bars = max(lookback, slow_period, 126) + 20

        regime_metrics: list[dict] = []

        for symbol, df in all_data.items():
            # Slice regime data with warmup
            regime_mask = (df.index >= regime.start) & (df.index <= regime.end)
            regime_only = df[regime_mask]
            if len(regime_only) < 20:
                continue

            pre_regime = df[df.index < regime.start]
            warmup_data = (
                pre_regime.iloc[-warmup_bars:]
                if len(pre_regime) >= warmup_bars
                else pre_regime
            )
            regime_data = pd.concat([warmup_data, regime_only])
            if len(regime_data) < 50:
                continue

            try:
                metrics = self._run_single_nt_backtest(
                    symbol, regime_data, strategy_cls, config_kwargs, initial_cash
                )
                if metrics is not None:
                    regime_metrics.append(metrics)
            except Exception as e:
                logger.warning(
                    "NT regime %s failed for %s: %s", regime_name, symbol, e
                )
                continue

        if not regime_metrics:
            return None

        avg = _average_metrics(regime_metrics)
        regime_result = RegimeResult(
            regime=regime_name,
            period_start=str(regime.start.date()),
            period_end=str(regime.end.date()),
            annual_return=avg["annual_return"],
            sharpe_ratio=avg["sharpe_ratio"],
            max_drawdown=avg["max_drawdown"],
            total_trades=int(avg["total_trades"]),
        )

        return {"regime_result": regime_result, "avg_metrics": avg}

    def _run_single_nt_backtest(
        self,
        symbol: str,
        data: pd.DataFrame,
        strategy_cls: type,
        config_kwargs: dict,
        initial_cash: int,
    ) -> dict | None:
        """Run a single NT backtest for one symbol."""
        from nautilus_trader.backtest.engine import BacktestEngine
        from nautilus_trader.backtest.models import FillModel
        from nautilus_trader.config import BacktestEngineConfig
        from nautilus_trader.model.currencies import USD
        from nautilus_trader.model.enums import AccountType, OmsType
        from nautilus_trader.model.identifiers import Venue
        from nautilus_trader.model.objects import Money

        venue = Venue("XNAS")
        instrument = create_equity_instrument(symbol, "XNAS")
        if instrument is None:
            return None

        # Configure engine with realistic fill model
        engine_config = BacktestEngineConfig(
            logging_config=None,
        )
        engine = BacktestEngine(config=engine_config)

        # Add venue with slippage model
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

        # Add instrument and data
        engine.add_instrument(instrument)
        bars = dataframe_to_bars(data, instrument.id)
        engine.add_data(bars)

        # Configure and add strategy
        instrument_id_str = f"{symbol}.XNAS"
        strategy_config_kwargs = {**config_kwargs, "instrument_id": instrument_id_str}

        # Get the config class from the strategy's __init__ signature
        import inspect

        sig = inspect.signature(strategy_cls.__init__)
        config_param = list(sig.parameters.values())[1]  # First after self
        config_cls = config_param.annotation
        if config_cls is inspect.Parameter.empty:
            # Fall back to matching config class by convention
            return None

        config = config_cls(**strategy_config_kwargs)
        strategy = strategy_cls(config=config)
        engine.add_strategy(strategy)

        # Run
        engine.run()

        # Extract metrics
        metrics = _extract_nt_metrics(engine, strategy, symbol)

        engine.dispose()
        return metrics

    def _fail_result(self, spec_id: str, reason: str, t0: float) -> StrategyResult:
        return StrategyResult(
            spec_id=spec_id,
            phase="validate",
            passed=False,
            failure_reason="validation_error",
            failure_details=reason,
            run_duration_seconds=time.time() - t0,
        )


# ── Helpers ──────────────────────────────────────────────────────────


def _safe_float(val, default: float = 0.0) -> float:
    """Convert to float, replacing None/NaN with default."""
    if val is None:
        return default
    try:
        f = float(val)
        return default if np.isnan(f) else f
    except (TypeError, ValueError):
        return default


def _extract_regime_metrics(stats, symbol: str) -> dict:
    """Extract metrics from backtesting.py stats for a regime period."""
    total_return = _safe_float(stats.get("Return [%]")) / 100
    sharpe = _safe_float(stats.get("Sharpe Ratio"))
    sortino = _safe_float(stats.get("Sortino Ratio"))
    max_dd = _safe_float(stats.get("Max. Drawdown [%]")) / 100
    win_rate = _safe_float(stats.get("Win Rate [%]")) / 100
    n_trades = int(_safe_float(stats.get("# Trades")))

    duration = stats.get("Duration", pd.Timedelta(days=252))
    years = max(getattr(duration, "days", 252) / 365.25, 0.01)
    annual_return = (1 + total_return) ** (1 / years) - 1 if total_return > -1 else -1.0

    avg_trade = stats.get("Avg. Trade [%]", 0) or 0
    profit_factor = 0.0
    if n_trades > 0 and win_rate > 0 and win_rate < 1.0:
        profit_factor = abs(win_rate * max(avg_trade, 0.01)) / abs(
            (1 - win_rate) * max(-avg_trade, 0.01)
        ) if avg_trade != 0 else 0

    return {
        "symbol": symbol,
        "total_return": total_return,
        "annual_return": annual_return,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": max_dd,
        "win_rate": win_rate,
        "profit_factor": max(profit_factor, 0),
        "total_trades": n_trades,
        "total_fees": abs(total_return) * 0.002,  # Approximate fee impact
    }


def _average_metrics(metrics_list: list[dict]) -> dict:
    """Average numeric metrics across a list of dicts, handling NaN."""
    if not metrics_list:
        return {}
    keys = [k for k in metrics_list[0] if k != "symbol"]
    result = {}
    for k in keys:
        vals = [_safe_float(m.get(k, 0)) for m in metrics_list]
        result[k] = sum(vals) / len(vals) if vals else 0.0
    return result


def _extract_nt_metrics(engine, strategy, symbol: str) -> dict:
    """Extract metrics from a completed NautilusTrader backtest engine."""
    try:
        # Get account and portfolio stats
        report = engine.get_result()
        fills = report.get("fills", [])

        # Calculate basic metrics from portfolio
        positions = strategy.cache.positions() if hasattr(strategy, "cache") else []
        n_trades = len(positions)

        # Try to get returns from account balance changes
        total_return = 0.0
        if hasattr(engine, "portfolio"):
            try:

                account = engine.portfolio.account(strategy.instrument_id.venue)
                if account is not None:
                    final_balance = float(account.balance_total().as_double())
                    initial = float(engine.config.venues[0].starting_balances[0])
                    total_return = (final_balance - initial) / initial if initial else 0
            except Exception:
                pass

        # Compute win rate
        wins = sum(
            1 for p in positions if hasattr(p, "realized_pnl") and float(p.realized_pnl) > 0
        )
        win_rate = wins / n_trades if n_trades > 0 else 0

        # Approximate Sharpe from total return and trades
        # (Simplified — real Sharpe needs daily returns series)
        if total_return != 0:
            sharpe = (
                total_return * np.sqrt(252)
                / max(abs(total_return) + 0.01, 0.01)
            )
        else:
            sharpe = 0
        sortino = sharpe * 0.8  # Rough approximation

        # Max drawdown (simplified)
        max_dd = min(total_return, 0)

        # Profit factor
        total_profit = sum(
            float(p.realized_pnl)
            for p in positions
            if hasattr(p, "realized_pnl") and float(p.realized_pnl) > 0
        )
        total_loss = abs(
            sum(
                float(p.realized_pnl)
                for p in positions
                if hasattr(p, "realized_pnl") and float(p.realized_pnl) < 0
            )
        )
        profit_factor = total_profit / max(total_loss, 0.01)

        # Fees from fills
        total_fees = 0.0
        if isinstance(fills, list):
            total_fees = sum(
                float(getattr(f, "commission", 0))
                for f in fills
                if hasattr(f, "commission")
            )

        return {
            "symbol": symbol,
            "total_return": total_return,
            "annual_return": total_return,  # Simplified
            "sharpe_ratio": _safe_float(sharpe),
            "sortino_ratio": _safe_float(sortino),
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "profit_factor": max(profit_factor, 0),
            "total_trades": n_trades,
            "total_fees": total_fees,
        }
    except Exception as e:
        logger.warning("Failed to extract NT metrics for %s: %s", symbol, e)
        return None
