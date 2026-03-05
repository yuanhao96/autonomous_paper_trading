"""Stock screener: filter universe by liquidity, price, and data quality."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ScreenResult:
    """Result of screening a single ticker."""

    ticker: str
    passed: bool
    adv_20d: float  # 20-day average dollar volume
    last_price: float  # most recent close
    data_completeness: float  # fraction of expected trading days with data
    history_days: int  # number of data rows
    sector: str | None = None
    fail_reasons: list[str] = field(default_factory=list)


def screen_universe(
    universe_data: dict[str, pd.DataFrame],
    min_adv: float = 5_000_000,
    min_price: float = 10.0,
    min_completeness: float = 0.95,
    min_history_days: int = 504,
) -> tuple[list[str], list[ScreenResult]]:
    """Screen tickers by liquidity, price, and data quality.

    Returns (passing_tickers, all_results).
    """
    all_results: list[ScreenResult] = []

    # Determine expected trading days from the longest series in the universe
    max_days = max((len(df) for df in universe_data.values()), default=0)

    for ticker, df in sorted(universe_data.items()):
        fail_reasons: list[str] = []

        # History length
        history_days = len(df)
        if history_days < min_history_days:
            fail_reasons.append(
                f"history {history_days} < {min_history_days} days"
            )

        # Last price
        last_price = float(df["Close"].iloc[-1]) if len(df) > 0 else 0.0
        if last_price < min_price:
            fail_reasons.append(f"price ${last_price:.2f} < ${min_price:.2f}")

        # Average dollar volume (20-day)
        if len(df) >= 20:
            dollar_vol = df["Close"] * df["Volume"]
            adv_20d = float(dollar_vol.iloc[-20:].mean())
        else:
            adv_20d = 0.0
        if adv_20d < min_adv:
            fail_reasons.append(
                f"ADV ${adv_20d:,.0f} < ${min_adv:,.0f}"
            )

        # Data completeness
        data_completeness = history_days / max_days if max_days > 0 else 0.0
        if data_completeness < min_completeness:
            fail_reasons.append(
                f"completeness {data_completeness:.1%} < {min_completeness:.1%}"
            )

        passed = len(fail_reasons) == 0

        all_results.append(ScreenResult(
            ticker=ticker,
            passed=passed,
            adv_20d=adv_20d,
            last_price=last_price,
            data_completeness=data_completeness,
            history_days=history_days,
            fail_reasons=fail_reasons,
        ))

    passing = [r.ticker for r in all_results if r.passed]
    return passing, all_results
