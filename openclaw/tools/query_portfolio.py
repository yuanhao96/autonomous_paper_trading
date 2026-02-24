"""OpenClaw tool: query current portfolio status.

Stub — actual OpenClaw integration happens on the target machine.
"""

from __future__ import annotations

from trading.paper_broker import PaperBroker

TOOL_SCHEMA: dict = {
    "name": "query_portfolio",
    "description": "Get current portfolio status",
    "parameters": {},
}


async def handle(params: dict) -> str:  # noqa: ARG001
    """Return a human-readable summary of the current portfolio.

    Creates a PaperBroker in mock mode and formats the portfolio snapshot
    as a string suitable for display in an OpenClaw messaging channel.
    """
    try:
        broker = PaperBroker(mock=True)
        portfolio = broker.get_portfolio()

        lines: list[str] = [
            "=== Portfolio Status ===",
            f"Total Equity:  ${portfolio.total_equity:,.2f}",
            f"Cash:          ${portfolio.cash:,.2f}",
            f"Timestamp:     {portfolio.timestamp}",
            "",
        ]

        if portfolio.positions:
            lines.append(f"Positions ({len(portfolio.positions)}):")
            lines.append("-" * 60)
            for pos in portfolio.positions:
                lines.append(
                    f"  {pos.ticker:<6}  "
                    f"qty={pos.quantity:<6}  "
                    f"avg_cost=${pos.avg_cost:,.2f}  "
                    f"mkt_val=${pos.market_value:,.2f}  "
                    f"pnl=${pos.unrealized_pnl:+,.2f}"
                )
        else:
            lines.append("No open positions.")

        return "\n".join(lines)

    except Exception as exc:
        return f"Error querying portfolio: {exc}"
