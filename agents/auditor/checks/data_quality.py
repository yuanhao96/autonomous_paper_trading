"""Data quality checks for OHLCV market data.

Validates that a market-data DataFrame is complete and plausible before
it is used for backtesting or live signal generation.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from agents.auditor.checks.look_ahead_bias import Finding

logger = logging.getLogger(__name__)

# Maximum allowed gap between consecutive trading dates (in business days).
_MAX_GAP_BUSINESS_DAYS: int = 3

# Threshold for a single-day price move to be considered suspicious.
_PRICE_JUMP_THRESHOLD: float = 0.50  # 50 %


def check_data_quality(data: pd.DataFrame) -> list[Finding]:
    """Run data-quality checks on an OHLCV DataFrame.

    Parameters
    ----------
    data:
        A DataFrame with a ``DatetimeIndex`` and columns that should
        include ``Open``, ``High``, ``Low``, ``Close``, and ``Volume``.

    Returns
    -------
    list[Finding]
        All data-quality findings.
    """
    findings: list[Finding] = []

    if data.empty:
        findings.append(
            Finding(
                check_name="data_quality",
                severity="critical",
                description="Data is empty — no rows to check.",
                evidence="DataFrame has 0 rows.",
            )
        )
        return findings

    # ------------------------------------------------------------------
    # 1. Missing dates (gaps > 3 business days)
    # ------------------------------------------------------------------
    findings.extend(_check_date_gaps(data))

    # ------------------------------------------------------------------
    # 2. NaN values in OHLCV columns
    # ------------------------------------------------------------------
    findings.extend(_check_nan_values(data))

    # ------------------------------------------------------------------
    # 3. Zero-volume days
    # ------------------------------------------------------------------
    findings.extend(_check_zero_volume(data))

    # ------------------------------------------------------------------
    # 4. Price jumps > 50 % in one day
    # ------------------------------------------------------------------
    findings.extend(_check_price_jumps(data))

    # ------------------------------------------------------------------
    # 5. Negative prices
    # ------------------------------------------------------------------
    findings.extend(_check_negative_prices(data))

    logger.info(
        "data_quality check complete: %d finding(s)",
        len(findings),
    )
    return findings


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _check_date_gaps(data: pd.DataFrame) -> list[Finding]:
    """Detect gaps in the DatetimeIndex larger than 3 business days."""
    findings: list[Finding] = []

    if not isinstance(data.index, pd.DatetimeIndex):
        findings.append(
            Finding(
                check_name="data_quality",
                severity="warning",
                description="Index is not a DatetimeIndex; date-gap check skipped.",
                evidence=f"Index type: {type(data.index).__name__}",
            )
        )
        return findings

    if len(data.index) < 2:
        return findings

    index_sorted = data.index.sort_values()
    diffs = pd.Series(index_sorted).diff().dropna()

    for i, gap in enumerate(diffs):
        if gap > pd.Timedelta(days=0):
            bdays = int(np.busday_count(
                index_sorted[i].date(),
                index_sorted[i + 1].date(),
            ))
            if bdays > _MAX_GAP_BUSINESS_DAYS:
                findings.append(
                    Finding(
                        check_name="data_quality",
                        severity="warning",
                        description=(
                            f"Gap of {bdays} business days detected between "
                            f"{index_sorted[i].date()} and "
                            f"{index_sorted[i + 1].date()}."
                        ),
                        evidence=f"gap_business_days={bdays}",
                    )
                )

    return findings


def _check_nan_values(data: pd.DataFrame) -> list[Finding]:
    """Report NaN counts in OHLCV columns."""
    findings: list[Finding] = []

    ohlcv_cols = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in data.columns]

    for col in ohlcv_cols:
        nan_count = int(data[col].isna().sum())
        if nan_count > 0:
            findings.append(
                Finding(
                    check_name="data_quality",
                    severity="warning",
                    description=(
                        f"Column '{col}' contains {nan_count} NaN value(s) "
                        f"out of {len(data)} rows."
                    ),
                    evidence=f"column={col}, nan_count={nan_count}",
                )
            )

    return findings


def _check_zero_volume(data: pd.DataFrame) -> list[Finding]:
    """Flag days where trading volume is zero."""
    findings: list[Finding] = []

    if "Volume" not in data.columns:
        return findings

    zero_vol = data[data["Volume"] == 0]
    if len(zero_vol) > 0:
        sample_dates = (
            zero_vol.index[:5].strftime("%Y-%m-%d").tolist()
            if isinstance(zero_vol.index, pd.DatetimeIndex)
            else list(zero_vol.index[:5])
        )
        findings.append(
            Finding(
                check_name="data_quality",
                severity="warning",
                description=(
                    f"{len(zero_vol)} day(s) have zero trading volume, "
                    f"which may indicate missing data or non-trading days "
                    f"incorrectly included."
                ),
                evidence=(
                    f"zero_volume_count={len(zero_vol)}, "
                    f"sample_dates={sample_dates}"
                ),
            )
        )

    return findings


def _check_price_jumps(data: pd.DataFrame) -> list[Finding]:
    """Detect single-day price moves exceeding the threshold."""
    findings: list[Finding] = []

    if "Close" not in data.columns:
        return findings

    close = data["Close"].dropna()
    if len(close) < 2:
        return findings

    pct_change = close.pct_change().dropna().abs()
    jumps = pct_change[pct_change > _PRICE_JUMP_THRESHOLD]

    for date, change in jumps.items():
        findings.append(
            Finding(
                check_name="data_quality",
                severity="warning",
                description=(
                    f"Price jump of {change:.1%} detected on "
                    f"{date}. This may indicate a stock split, "
                    f"data error, or extreme event."
                ),
                evidence=f"date={date}, pct_change={change:.4f}",
            )
        )

    return findings


def _check_negative_prices(data: pd.DataFrame) -> list[Finding]:
    """Flag any negative prices in OHLC columns."""
    findings: list[Finding] = []

    price_cols = [c for c in ("Open", "High", "Low", "Close") if c in data.columns]

    for col in price_cols:
        neg_count = int((data[col] < 0).sum())
        if neg_count > 0:
            findings.append(
                Finding(
                    check_name="data_quality",
                    severity="critical",
                    description=(
                        f"Column '{col}' contains {neg_count} negative "
                        f"price value(s). Prices should never be negative."
                    ),
                    evidence=f"column={col}, negative_count={neg_count}",
                )
            )

    return findings
