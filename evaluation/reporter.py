"""Report generation for human consumption.

Produces Markdown-formatted daily and weekly performance summaries that
are concise enough for iMessage delivery while still conveying the key
numbers a human needs to supervise the paper trading system.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from evaluation.metrics import PerformanceSummary

# ---------------------------------------------------------------------------
# Type protocols for Portfolio (avoids hard dependency on paper_broker)
# ---------------------------------------------------------------------------


class _Position:
    """Duck-type for a single position within a Portfolio."""

    ticker: str
    quantity: int
    market_value: float
    unrealized_pnl: float


class Portfolio:
    """Duck-type for the portfolio object produced by ``trading.paper_broker``.

    Attributes expected:
        total_value (float): Net liquidation value.
        cash (float): Available cash.
        daily_pnl (float): Today's P&L.
        positions (list): Each item exposes ticker, quantity, market_value,
            unrealized_pnl.
    """

    total_value: float
    cash: float
    daily_pnl: float
    positions: list[Any]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_currency(value: float) -> str:
    """Format a dollar value with sign and comma separators."""
    sign = "+" if value >= 0 else ""
    return f"{sign}${value:,.2f}"


def _fmt_pct(value: float) -> str:
    """Format a fraction as a percentage string (e.g. 0.15 -> '15.00%')."""
    return f"{value * 100:.2f}%"


def _positions_table(positions: list[Any]) -> str:
    """Build a Markdown table of current positions."""
    if not positions:
        return "_No open positions._"

    lines: list[str] = [
        "| Ticker | Qty | Market Value | Unrealized P&L |",
        "|--------|----:|-------------:|---------------:|",
    ]
    for pos in positions:
        ticker = getattr(pos, "ticker", getattr(pos, "symbol", "???"))
        qty = getattr(pos, "quantity", getattr(pos, "qty", 0))
        mv = getattr(pos, "market_value", 0.0)
        upnl = getattr(pos, "unrealized_pnl", 0.0)
        lines.append(
            f"| {ticker} | {qty} | ${float(mv):,.2f} | {_fmt_currency(float(upnl))} |"
        )
    return "\n".join(lines)


def _trades_section(trades: list[dict]) -> str:
    """Format today's trades (if any) as a Markdown list."""
    if not trades:
        return "_No trades today._"

    lines: list[str] = []
    for t in trades:
        ticker = t.get("ticker", "???")
        side = t.get("side", "???")
        pnl = t.get("pnl", 0.0)
        entry = t.get("entry_price", 0.0)
        exit_ = t.get("exit_price", 0.0)
        lines.append(
            f"- **{ticker}** {side} | "
            f"entry ${entry:,.2f} -> exit ${exit_:,.2f} | "
            f"P&L {_fmt_currency(pnl)}"
        )
    return "\n".join(lines)


def _metrics_section(metrics: PerformanceSummary) -> str:
    """Key metrics formatted as a compact Markdown block."""
    return (
        f"- Sharpe Ratio: **{metrics.sharpe_ratio:.2f}**\n"
        f"- Max Drawdown: **{_fmt_pct(metrics.max_drawdown)}**\n"
        f"- Win Rate: **{_fmt_pct(metrics.win_rate)}** "
        f"({metrics.num_trades} trades)\n"
        f"- Total P&L: **{_fmt_currency(metrics.total_pnl)}**\n"
        f"- Avg P&L per trade: {_fmt_currency(metrics.avg_pnl)}\n"
        f"- Best trade: {_fmt_currency(metrics.best_trade)} | "
        f"Worst trade: {_fmt_currency(metrics.worst_trade)}"
    )


# ---------------------------------------------------------------------------
# Public report generators
# ---------------------------------------------------------------------------


def generate_daily_report(
    portfolio: Portfolio,
    trades: list[dict],
    metrics: PerformanceSummary,
) -> str:
    """Generate a Markdown daily performance summary.

    Parameters
    ----------
    portfolio:
        Current portfolio state (duck-typed; see ``Portfolio`` above).
    trades:
        List of trade dicts executed today.
    metrics:
        Aggregated performance metrics to date.

    Returns
    -------
    str
        Markdown-formatted report suitable for iMessage delivery.
    """
    today_str = date.today().isoformat()
    total_value = getattr(portfolio, "total_value", 0.0)
    daily_pnl = getattr(portfolio, "daily_pnl", 0.0)
    positions = getattr(portfolio, "positions", [])

    sections: list[str] = [
        f"# Daily Report -- {today_str}",
        "",
        f"**Portfolio Value:** ${total_value:,.2f}  ",
        f"**Daily P&L:** {_fmt_currency(daily_pnl)}",
        "",
        "## Positions",
        "",
        _positions_table(positions),
        "",
        "## Today's Trades",
        "",
        _trades_section(trades),
        "",
        "## Key Metrics",
        "",
        _metrics_section(metrics),
    ]

    return "\n".join(sections)


def generate_weekly_report(
    portfolio: Portfolio,
    trades: list[dict],
    metrics: PerformanceSummary,
    curriculum_progress: dict,
) -> str:
    """Generate a Markdown weekly performance summary.

    Includes everything from the daily report plus a weekly comparison
    and a learning/curriculum progress section.

    Parameters
    ----------
    portfolio:
        Current portfolio state.
    trades:
        All trades executed during the week.
    metrics:
        Aggregated performance metrics for the week.
    curriculum_progress:
        Dict with keys such as ``current_stage`` (str), ``stage_progress``
        (float 0-1), ``topics_mastered`` (list[str]), ``total_topics`` (int),
        ``mastered_count`` (int).

    Returns
    -------
    str
        Markdown-formatted report suitable for iMessage delivery.
    """
    today_str = date.today().isoformat()
    total_value = getattr(portfolio, "total_value", 0.0)
    daily_pnl = getattr(portfolio, "daily_pnl", 0.0)
    positions = getattr(portfolio, "positions", [])

    # -- Curriculum / learning section ------------------------------------
    current_stage = curriculum_progress.get("current_stage", "Unknown")
    stage_progress = curriculum_progress.get("stage_progress", 0.0)
    topics_mastered: list[str] = curriculum_progress.get("topics_mastered", [])
    total_topics: int = curriculum_progress.get("total_topics", 0)
    mastered_count: int = curriculum_progress.get("mastered_count", len(topics_mastered))

    learning_lines: list[str] = [
        f"- Current Stage: **{current_stage}**",
        f"- Stage Progress: **{_fmt_pct(stage_progress)}**",
        f"- Topics Mastered: **{mastered_count} / {total_topics}**",
    ]
    if topics_mastered:
        learning_lines.append("- Recently mastered:")
        for topic in topics_mastered[-5:]:  # Show last 5 at most
            learning_lines.append(f"  - {topic}")

    sections: list[str] = [
        f"# Weekly Report -- week ending {today_str}",
        "",
        f"**Portfolio Value:** ${total_value:,.2f}  ",
        f"**Daily P&L (latest):** {_fmt_currency(daily_pnl)}",
        "",
        "## Positions",
        "",
        _positions_table(positions),
        "",
        "## Weekly Trades",
        "",
        _trades_section(trades),
        "",
        "## Weekly Performance",
        "",
        _metrics_section(metrics),
        "",
        "## Learning Progress",
        "",
        *learning_lines,
    ]

    return "\n".join(sections)
