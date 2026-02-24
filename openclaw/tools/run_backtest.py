"""OpenClaw tool: run a backtest for a named strategy.

Stub — actual OpenClaw integration happens on the target machine.
"""

from __future__ import annotations

from evaluation.backtester import Backtester
from strategies.registry import registry
from trading.data import get_ohlcv

TOOL_SCHEMA: dict = {
    "name": "run_backtest",
    "description": "Run backtest for a strategy",
    "parameters": {
        "strategy_name": {
            "type": "str",
            "description": "Name of the registered strategy to backtest (e.g. 'sma_crossover')",
            "required": True,
        },
        "ticker": {
            "type": "str",
            "description": "Stock ticker to backtest against (default: 'SPY')",
            "required": False,
        },
        "period": {
            "type": "str",
            "description": "Historical data period (e.g. '1y', '2y', '6mo'). Default: '2y'",
            "required": False,
        },
    },
}


async def handle(params: dict) -> str:
    """Run a walk-forward backtest and return a metrics summary.

    Looks up the strategy by name in the global registry, fetches
    historical OHLCV data, runs the backtester, and formats the
    results as a readable string.
    """
    strategy_name = params.get("strategy_name")
    if not strategy_name:
        return "Error: 'strategy_name' parameter is required."

    ticker = params.get("ticker", "SPY")
    period = params.get("period", "2y")

    try:
        strategy = registry.get(strategy_name)
        if strategy is None:
            available = registry.list_strategies()
            return (
                f"Error: Strategy '{strategy_name}' not found in registry. "
                f"Available strategies: {available}"
            )

        data = get_ohlcv(ticker=ticker, period=period, interval="1d")
        if data.empty:
            return f"Error: No OHLCV data available for {ticker} (period={period})."

        backtester = Backtester()
        result = backtester.run(strategy=strategy, data=data)

        metrics = result.metrics
        lines: list[str] = [
            "=== Backtest Results ===",
            f"Strategy:     {strategy_name}",
            f"Ticker:       {ticker}",
            f"Period:       {period}",
            f"Windows Used: {result.windows_used}",
            "",
            "--- Metrics ---",
            f"Trades:       {metrics.num_trades}",
            f"Win Rate:     {metrics.win_rate:.1%}",
            f"Total P&L:    ${metrics.total_pnl:+,.2f}",
            f"Avg P&L:      ${metrics.avg_pnl:+,.2f}",
            f"Best Trade:   ${metrics.best_trade:+,.2f}",
            f"Worst Trade:  ${metrics.worst_trade:+,.2f}",
            f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}",
            f"Max Drawdown: {metrics.max_drawdown:.1%}",
        ]

        return "\n".join(lines)

    except Exception as exc:
        return f"Error running backtest: {exc}"
