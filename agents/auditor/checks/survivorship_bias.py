"""Survivorship bias detection for backtest ticker universes.

Checks whether the ticker list used in a backtest is biased toward
currently-active companies, which inflates historical performance by
excluding firms that failed, delisted, or were acquired.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from agents.auditor.checks.look_ahead_bias import Finding

logger = logging.getLogger(__name__)


def check_survivorship_bias(
    tickers_used: list[str],
    backtest_start_date: str,
) -> list[Finding]:
    """Check a ticker universe for survivorship bias.

    Parameters
    ----------
    tickers_used:
        List of ticker symbols included in the backtest universe.
    backtest_start_date:
        ISO-format date string (e.g. ``"2018-01-01"``) marking the start
        of the backtest period.

    Returns
    -------
    list[Finding]
        Survivorship-bias-related findings.
    """
    findings: list[Finding] = []

    if not tickers_used:
        findings.append(
            Finding(
                check_name="survivorship_bias",
                severity="info",
                description="No tickers provided; survivorship bias check skipped.",
                evidence="tickers_used is empty.",
            )
        )
        return findings

    # ------------------------------------------------------------------
    # 1. Check backtest span length
    # ------------------------------------------------------------------
    try:
        start_dt = datetime.fromisoformat(backtest_start_date)
    except (ValueError, TypeError):
        findings.append(
            Finding(
                check_name="survivorship_bias",
                severity="info",
                description=(
                    "Could not parse backtest_start_date; some survivorship "
                    "checks skipped."
                ),
                evidence=f"backtest_start_date={backtest_start_date!r}",
            )
        )
        start_dt = None

    if start_dt is not None:
        now = datetime.now(tz=timezone.utc)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        years_span = (now - start_dt).days / 365.25

        if years_span > 5.0:
            findings.append(
                Finding(
                    check_name="survivorship_bias",
                    severity="warning",
                    description=(
                        f"Backtest spans {years_span:.1f} years with a fixed "
                        f"ticker list. Over such long periods the universe is "
                        f"likely subject to survivorship bias — companies that "
                        f"failed or delisted during this window are missing."
                    ),
                    evidence=(
                        f"backtest_start_date={backtest_start_date}, "
                        f"span={years_span:.1f} years, "
                        f"tickers={len(tickers_used)}"
                    ),
                )
            )

    # ------------------------------------------------------------------
    # 2. Check if all tickers are currently active
    # ------------------------------------------------------------------
    inactive_tickers: list[str] = []
    active_tickers: list[str] = []
    error_tickers: list[str] = []

    try:
        import yfinance as yf  # noqa: E402
    except ImportError:
        logger.warning("yfinance not installed; skipping active-ticker check.")
        findings.append(
            Finding(
                check_name="survivorship_bias",
                severity="info",
                description=(
                    "yfinance is not installed; cannot verify whether "
                    "tickers are currently active."
                ),
                evidence="ImportError on yfinance",
            )
        )
        return findings

    for ticker_symbol in tickers_used:
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info or {}
            # Heuristic: if yfinance returns meaningful market data the
            # ticker is still active.  Delisted tickers typically have no
            # ``regularMarketPrice`` or an empty ``info`` dict.
            if info.get("regularMarketPrice") or info.get("currentPrice"):
                active_tickers.append(ticker_symbol)
            else:
                inactive_tickers.append(ticker_symbol)
        except Exception as exc:
            logger.debug(
                "yfinance lookup failed for %s: %s",
                ticker_symbol,
                exc,
            )
            error_tickers.append(ticker_symbol)

    if not inactive_tickers and not error_tickers and len(active_tickers) > 0:
        findings.append(
            Finding(
                check_name="survivorship_bias",
                severity="warning",
                description=(
                    "All tickers in the backtest universe are currently "
                    "active. The universe contains no delisted or failed "
                    "companies, which is a hallmark of survivorship bias."
                ),
                evidence=(
                    f"All {len(active_tickers)} tickers are active: "
                    f"{active_tickers}"
                ),
            )
        )

    if inactive_tickers:
        findings.append(
            Finding(
                check_name="survivorship_bias",
                severity="info",
                description=(
                    f"{len(inactive_tickers)} ticker(s) appear to be "
                    f"inactive or delisted, which is healthy for avoiding "
                    f"survivorship bias."
                ),
                evidence=f"inactive_tickers={inactive_tickers}",
            )
        )

    if error_tickers:
        findings.append(
            Finding(
                check_name="survivorship_bias",
                severity="info",
                description=(
                    f"Could not verify status for {len(error_tickers)} "
                    f"ticker(s) due to data fetch errors."
                ),
                evidence=f"error_tickers={error_tickers}",
            )
        )

    logger.info(
        "survivorship_bias check complete: %d finding(s)",
        len(findings),
    )
    return findings
