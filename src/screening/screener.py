"""Screening pipeline — backtesting.py integration for Phase 1."""

from __future__ import annotations

import logging
import time
import warnings
from dataclasses import replace
from datetime import date
from typing import Any

import pandas as pd
from backtesting import Backtest

# backtesting.py emits a RuntimeWarning about spawn-based multiprocessing on every
# optimize() call.  It falls back to threads automatically — the warning is noise.
warnings.filterwarnings("ignore", message=".*multi-process optimization.*", module="backtesting")

from src.core.config import Settings
from src.data.manager import DataManager
from src.screening.filters import ScreeningFilters
from src.screening.translator import get_optimization_bounds, translate
from src.strategies.spec import StrategyResult, StrategySpec

logger = logging.getLogger(__name__)


class Screener:
    """Phase 1 screening pipeline using backtesting.py.

    Flow:
    1. Resolve universe → get OHLCV data
    2. Translate StrategySpec → backtesting.py Strategy
    3. Run backtest with default parameters
    4. Optionally optimize parameters
    5. Run walk-forward analysis
    6. Apply pass/fail filters
    7. Return StrategyResult with rich diagnostics
    """

    def __init__(
        self,
        data_manager: DataManager | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._dm = data_manager or DataManager()
        self._settings = settings or Settings()
        self._filters = ScreeningFilters(self._settings)

    def screen(
        self,
        spec: StrategySpec,
        symbols: list[str],
        start: date | None = None,
        end: date | None = None,
        optimize: bool = True,
    ) -> StrategyResult:
        """Screen a strategy against provided symbols.

        Args:
            spec: Strategy specification to screen.
            symbols: List of symbols to test against.
            start: Backtest start date.
            end: Backtest end date.
            optimize: Whether to run parameter optimization.

        Returns:
            StrategyResult with metrics and pass/fail status.
        """
        t0 = time.time()

        # Aggregate results across all symbols
        all_results: list[dict] = []

        for symbol in symbols:
            try:
                df = self._dm.get_ohlcv(symbol, start=start, end=end)
                if df.empty or len(df) < 100:
                    continue

                if optimize:
                    # Walk-forward analysis: train→optimize→test OOS
                    result = self._run_walk_forward(spec, df, symbol)
                    if result is None:
                        # Fall back if data too short or no bounds
                        result = self._run_single(spec, df, symbol, optimize=False)
                else:
                    result = self._run_single(spec, df, symbol, optimize=False)

                if result is not None:
                    all_results.append(result)
            except Exception as e:
                logger.warning("Screening failed for %s: %s", symbol, e)
                continue

        if not all_results:
            return StrategyResult(
                spec_id=spec.id,
                phase="screen",
                passed=False,
                failure_reason="no_data",
                failure_details="No valid data for any symbols in the universe",
                run_duration_seconds=time.time() - t0,
                symbols_requested=len(symbols),
                symbols_with_data=0,
            )

        # Average metrics across symbols
        avg_result = self._aggregate_results(spec.id, all_results)
        avg_result.run_duration_seconds = time.time() - t0
        avg_result.symbols_requested = len(symbols)
        avg_result.symbols_with_data = len(all_results)
        avg_result.backtest_start = str(start or "")
        avg_result.backtest_end = str(end or "")

        # Apply pass/fail filters
        filter_result = self._filters.apply(avg_result)
        avg_result.passed = filter_result.passed
        if not filter_result.passed:
            avg_result.failure_reason = filter_result.failure_reason
            avg_result.failure_details = "; ".join(
                f"{k}: {v}" for k, v in filter_result.details.items()
            )

        return avg_result

    def _run_single(
        self,
        spec: StrategySpec,
        data: pd.DataFrame,
        symbol: str,
        optimize: bool,
    ) -> dict | None:
        """Run backtest for a single symbol."""
        try:
            strategy_cls = translate(spec, data)
            initial_cash = self._settings.get("screening.initial_cash", 100000)
            commission = self._settings.get("screening.commission", 0.002)

            bt = Backtest(
                data,
                strategy_cls,
                cash=initial_cash,
                commission=commission,
                exclusive_orders=True,
                trade_on_close=True,
                finalize_trades=True,
            )

            # Run with default parameters first
            stats = bt.run()

            # Optionally optimize
            optimized_params: dict[str, Any] = {}
            if optimize:
                bounds = get_optimization_bounds(spec)
                if bounds:
                    try:
                        opt_stats = bt.optimize(
                            **bounds,
                            maximize="Sharpe Ratio",
                            max_tries=100,
                        )
                        # Use optimized results if better
                        opt_sharpe = opt_stats.get("Sharpe Ratio", 0) or 0
                        default_sharpe = stats.get("Sharpe Ratio", 0) or 0
                        if opt_sharpe > default_sharpe:
                            stats = opt_stats
                            optimized_params = {
                                k: getattr(stats._strategy, k, None)
                                for k in bounds.keys()
                            }
                    except Exception:
                        pass

            return _extract_metrics(stats, symbol, optimized_params)

        except Exception as e:
            logger.warning("Backtest failed for %s: %s", symbol, e)
            return None

    def _run_walk_forward(
        self,
        spec: StrategySpec,
        data: pd.DataFrame,
        symbol: str,
    ) -> dict | None:
        """Rolling walk-forward analysis for a single symbol.

        Train → optimize on IS window → test on OOS window → step forward.
        Returns averaged OOS metrics with IS Sharpe for gap detection.
        Returns None if data too short or no optimization bounds.
        """
        bounds = get_optimization_bounds(spec)
        if not bounds:
            return None

        train_days = self._settings.get("screening.walk_forward.train_days", 252)
        test_days = self._settings.get("screening.walk_forward.test_days", 63)
        step_days = self._settings.get("screening.walk_forward.step_days", 21)

        min_required = train_days + test_days
        if len(data) < min_required:
            return None

        initial_cash = self._settings.get("screening.initial_cash", 100000)
        commission = self._settings.get("screening.commission", 0.002)

        is_sharpes: list[float] = []
        oos_metrics_list: list[dict] = []
        best_params: dict[str, Any] = {}

        i = 0
        while i + train_days + test_days <= len(data):
            train_data = data.iloc[i : i + train_days]
            test_data = data.iloc[i + train_days : i + train_days + test_days]

            if len(train_data) < 100 or len(test_data) < 20:
                i += step_days
                continue

            try:
                # Step 1: Optimize on training window
                train_cls = translate(spec, train_data)
                train_bt = Backtest(
                    train_data,
                    train_cls,
                    cash=initial_cash,
                    commission=commission,
                    exclusive_orders=True,
                    trade_on_close=True,
                    finalize_trades=True,
                )

                opt_stats = train_bt.optimize(
                    **bounds,
                    maximize="Sharpe Ratio",
                    max_tries=100,
                )

                is_sharpe = opt_stats.get("Sharpe Ratio", 0) or 0
                is_sharpes.append(is_sharpe)

                # Step 2: Extract optimized params
                opt_params: dict[str, Any] = {
                    k: getattr(opt_stats._strategy, k, None)
                    for k in bounds.keys()
                }
                best_params = opt_params

                # Step 3: Run OOS with optimized params baked into spec
                merged_params = {**spec.parameters, **opt_params}
                oos_spec = replace(spec, parameters=merged_params)

                test_cls = translate(oos_spec, test_data)
                test_bt = Backtest(
                    test_data,
                    test_cls,
                    cash=initial_cash,
                    commission=commission,
                    exclusive_orders=True,
                    trade_on_close=True,
                    finalize_trades=True,
                )

                oos_stats = test_bt.run()
                oos_metrics = _extract_metrics(oos_stats, symbol, opt_params)
                oos_metrics_list.append(oos_metrics)

            except Exception as e:
                logger.debug("Walk-forward window %d failed for %s: %s", i, symbol, e)

            i += step_days

        if not oos_metrics_list:
            return None

        result = _average_walk_forward_metrics(oos_metrics_list, symbol, best_params)
        result["in_sample_sharpe"] = (
            sum(is_sharpes) / len(is_sharpes) if is_sharpes else 0.0
        )
        return result

    def _aggregate_results(self, spec_id: str, results: list[dict]) -> StrategyResult:
        """Average metrics across multiple symbol backtests."""
        n = len(results)
        if n == 0:
            return StrategyResult(spec_id=spec_id, phase="screen")

        def avg(key: str) -> float:
            vals = [r.get(key, 0.0) for r in results]
            return sum(vals) / len(vals) if vals else 0.0

        return StrategyResult(
            spec_id=spec_id,
            phase="screen",
            total_return=avg("total_return"),
            annual_return=avg("annual_return"),
            sharpe_ratio=avg("sharpe_ratio"),
            sortino_ratio=avg("sortino_ratio"),
            max_drawdown=avg("max_drawdown"),
            win_rate=avg("win_rate"),
            profit_factor=avg("profit_factor"),
            total_trades=int(avg("total_trades")),
            total_fees=avg("total_fees"),
            equity_curve=results[0].get("equity_curve", []) if results else [],
            drawdown_series=results[0].get("drawdown_series", []) if results else [],
            optimized_parameters=results[0].get("optimized_parameters", {}),
            in_sample_sharpe=avg("in_sample_sharpe"),
        )


def _extract_metrics(
    stats: Any, symbol: str, optimized_params: dict[str, Any]
) -> dict[str, Any]:
    """Extract metrics from backtesting.py stats object."""
    equity = stats.get("_equity_curve")
    equity_list: list[float] = []
    dd_list: list[float] = []
    if equity is not None and hasattr(equity, "Equity"):
        equity_list = equity["Equity"].tolist()[-100:]  # Last 100 points
        dd_list = equity["DrawdownPct"].tolist()[-100:] if "DrawdownPct" in equity.columns else []

    total_return = (stats.get("Return [%]", 0) or 0) / 100
    sharpe = stats.get("Sharpe Ratio", 0) or 0
    sortino = stats.get("Sortino Ratio", 0) or 0
    max_dd = (stats.get("Max. Drawdown [%]", 0) or 0) / 100
    win_rate = (stats.get("Win Rate [%]", 0) or 0) / 100
    n_trades = stats.get("# Trades", 0) or 0

    # Compute profit factor from win rate and avg win/loss
    avg_win = stats.get("Avg. Trade [%]", 0) or 0
    profit_factor = 0.0
    if n_trades > 0 and win_rate > 0:
        # Approximate profit factor
        if win_rate < 1.0:
            if avg_win != 0:
                profit_factor = (
                    (win_rate * max(avg_win, 0.01))
                    / ((1 - win_rate) * max(-avg_win, 0.01))
                )
            else:
                profit_factor = 0
        else:
            profit_factor = 10.0  # Cap

    # Annualize return
    duration_days = stats.get("Duration", pd.Timedelta(days=252))
    if hasattr(duration_days, "days"):
        years = max(duration_days.days / 365.25, 0.1)
    else:
        years = 1.0
    annual_return = (1 + total_return) ** (1 / years) - 1

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
        "total_fees": 0.0,
        "equity_curve": equity_list,
        "drawdown_series": dd_list,
        "optimized_parameters": optimized_params,
        "in_sample_sharpe": 0.0,
    }


def _average_walk_forward_metrics(
    metrics_list: list[dict[str, Any]], symbol: str, params: dict[str, Any]
) -> dict[str, Any]:
    """Average metrics across walk-forward OOS test windows."""
    numeric_keys = [
        k
        for k in metrics_list[0]
        if k not in ("symbol", "equity_curve", "drawdown_series", "optimized_parameters")
    ]
    result: dict[str, Any] = {}
    for k in numeric_keys:
        vals = [m.get(k, 0.0) for m in metrics_list]
        result[k] = sum(vals) / len(vals) if vals else 0.0
    result["symbol"] = symbol
    result["equity_curve"] = metrics_list[-1].get("equity_curve", [])
    result["drawdown_series"] = metrics_list[-1].get("drawdown_series", [])
    result["optimized_parameters"] = params
    return result
