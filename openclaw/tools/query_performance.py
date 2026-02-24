"""OpenClaw tool: query performance metrics.

Stub — actual OpenClaw integration happens on the target machine.
"""

from __future__ import annotations

from evaluation.metrics import generate_summary
from trading.paper_broker import PaperBroker

TOOL_SCHEMA: dict = {
    "name": "query_performance",
    "description": "Get performance metrics for a time period",
    "parameters": {
        "period": {
            "type": "str",
            "description": (
                "Time period for metrics"
                " (e.g. '1w', '1m', '3m', 'all')."
                " Defaults to 'all'."
            ),
            "required": False,
        },
    },
}


async def handle(params: dict) -> str:
    """Return a human-readable performance report.

    Fetches order history from the paper broker and computes performance
    metrics.  The *period* parameter is accepted but currently all
    available trade history is used (period filtering is a future
    enhancement).
    """
    try:
        period = params.get("period", "all")
        broker = PaperBroker(mock=True)

        portfolio = broker.get_portfolio()
        orders = broker.get_order_history(limit=500)

        # Build trade records from filled orders for metrics calculation.
        # For a rough summary we pair consecutive buy/sell fills on the same
        # ticker.  A full implementation would use the executor's trade log.
        trades: list[dict] = []
        open_buys: dict[str, dict] = {}

        for order in reversed(orders):  # oldest first
            if order.status != "filled" or order.filled_price is None:
                continue
            if order.side == "buy":
                open_buys[order.ticker] = {
                    "ticker": order.ticker,
                    "entry_price": order.filled_price,
                    "quantity": order.quantity,
                    "entry_date": order.filled_at or order.created_at,
                }
            elif order.side == "sell" and order.ticker in open_buys:
                entry = open_buys.pop(order.ticker)
                pnl = (order.filled_price - entry["entry_price"]) * entry["quantity"]
                trades.append({
                    "ticker": order.ticker,
                    "entry_price": entry["entry_price"],
                    "exit_price": order.filled_price,
                    "pnl": pnl,
                    "return_pct": (
                        (order.filled_price - entry["entry_price"]) / entry["entry_price"]
                        if entry["entry_price"] else 0.0
                    ),
                    "entry_date": entry["entry_date"],
                    "exit_date": order.filled_at or order.created_at,
                })

        lines: list[str] = [
            f"=== Performance Report (period: {period}) ===",
            f"Total Equity: ${portfolio.total_equity:,.2f}",
            f"Cash:         ${portfolio.cash:,.2f}",
            "",
        ]

        if trades:
            import pandas as pd

            # Build a simple equity curve from trade P&L.
            cumulative = 100_000.0
            equity_points: list[float] = [cumulative]
            for t in trades:
                cumulative += t["pnl"]
                equity_points.append(cumulative)
            equity_curve = pd.Series(equity_points, dtype=float)

            summary = generate_summary(equity_curve, trades)
            lines.extend([
                f"Trades:       {summary.num_trades}",
                f"Win Rate:     {summary.win_rate:.1%}",
                f"Total P&L:    ${summary.total_pnl:+,.2f}",
                f"Avg P&L:      ${summary.avg_pnl:+,.2f}",
                f"Best Trade:   ${summary.best_trade:+,.2f}",
                f"Worst Trade:  ${summary.worst_trade:+,.2f}",
                f"Sharpe Ratio: {summary.sharpe_ratio:.2f}",
                f"Max Drawdown: {summary.max_drawdown:.1%}",
            ])
        else:
            lines.append("No completed trades found.")

        return "\n".join(lines)

    except Exception as exc:
        return f"Error querying performance: {exc}"
