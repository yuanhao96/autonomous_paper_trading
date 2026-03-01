"""Spec extraction: knowledge doc → StrategySpec via LLM."""

from pathlib import Path
from textwrap import dedent

import yfinance as yf

from stratgen.core import StrategySpec, llm_call, parse_llm_json
from stratgen.paths import KNOWLEDGE_DIR, PROJECT_ROOT


# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------

SPEC_SYSTEM_PROMPT = dedent("""\
    You are a trading strategy analyst. You read strategy documentation and extract
    a structured StrategySpec for backtesting.

    CONSTRAINTS — the backtesting system has these hard limits:
    - Single ticker only (no multi-asset portfolios, no universe ranking)
    - OHLCV price data only (no fundamental data, no sentiment, no alternative data)
    - Daily timeframe (no intraday)
    - Long-only or long/short on ONE asset
    - Library: backtesting.py (supports technical indicators computed from OHLCV)

    YOUR JOB:
    1. Read the strategy document carefully
    2. If the strategy CAN work within the constraints → produce a StrategySpec
    3. If it NEEDS adaptation → adapt it and document what you changed in "adaptations"
       Examples of valid adaptations:
       - Multi-asset ranking → apply the signal to a single representative ETF (SPY, QQQ, etc.)
       - Fundamental filter → drop it, use only the technical/price-based component
       - Cross-asset momentum → apply momentum signal to one asset class ETF
    4. If the strategy CANNOT work even after adaptation → set "skipped" to explain why
       Examples: pairs trading (needs 2 tickers), pure fundamental (no price signal at all)

    OUTPUT FORMAT — respond with ONLY a JSON object, no markdown, no explanation:
    {
        "name": "Human-readable strategy name",
        "universe": ["TICKER"],
        "timeframe": "1d",
        "entry_signal": "Plain English description of when to buy",
        "exit_signal": "Plain English description of when to sell",
        "stop_loss_pct": 0.02,
        "position_size_pct": 0.95,
        "params": {"param_name": default_value},
        "adaptations": ["what was changed and why"],
        "skipped": null
    }

    If skipped:
    {
        "name": "Strategy Name",
        "skipped": "Reason it cannot be adapted to single-ticker OHLCV backtesting"
    }

    RULES:
    - entry_signal and exit_signal must be concrete and implementable from OHLCV data
    - Do NOT invent rules that aren't grounded in the document
    - params should include indicator periods, thresholds, lookback windows
    - stop_loss_pct between 0.01 and 0.10 (1% to 10%)
    - Choose a sensible default ticker: SPY for broad equity, QQQ for tech, GLD for gold, etc.
    - Use 0 temperature thinking — be precise, not creative
""")


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def _extract_spec_llm(
    knowledge_text: str, knowledge_ref: str, provider: str,
) -> StrategySpec:
    raw = llm_call(
        SPEC_SYSTEM_PROMPT,
        f"Extract a StrategySpec from this document:\n\n{knowledge_text}",
        provider,
    )
    return _parse_spec_json(raw, knowledge_ref)


def _parse_spec_json(raw: str, knowledge_ref: str) -> StrategySpec:
    """Parse LLM JSON output into a StrategySpec."""
    data = parse_llm_json(raw)

    # Handle skipped strategies
    if data.get("skipped"):
        return StrategySpec(
            name=data.get("name", "Unknown"),
            knowledge_ref=knowledge_ref,
            universe=[],
            timeframe="1d",
            entry_signal="",
            exit_signal="",
            stop_loss_pct=0,
            position_size_pct=0,
            skipped=data["skipped"],
        )

    return StrategySpec(
        name=data["name"],
        knowledge_ref=knowledge_ref,
        universe=data["universe"],
        timeframe=data.get("timeframe", "1d"),
        entry_signal=data["entry_signal"],
        exit_signal=data["exit_signal"],
        stop_loss_pct=data.get("stop_loss_pct", 0.02),
        position_size_pct=data.get("position_size_pct", 0.95),
        params=data.get("params", {}),
        adaptations=data.get("adaptations", []),
    )


def extract_spec(knowledge_path: str, provider: str = "openai") -> StrategySpec:
    """Read a knowledge doc and extract a StrategySpec via LLM."""
    path = Path(knowledge_path)
    if not path.exists():
        # Try relative to knowledge dir
        path = KNOWLEDGE_DIR / knowledge_path
    if not path.exists():
        raise FileNotFoundError(f"Knowledge doc not found: {knowledge_path}")

    knowledge_text = path.read_text()
    path = path.resolve()
    knowledge_ref = str(path.relative_to(PROJECT_ROOT))

    print(f"Reading: {knowledge_ref}")
    print(f"Extracting StrategySpec via {provider}...")
    return _extract_spec_llm(knowledge_text, knowledge_ref, provider)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_ticker(ticker: str) -> bool:
    """Check that a ticker exists on yfinance."""
    try:
        info = yf.Ticker(ticker).fast_info
        return info.get("lastPrice", 0) > 0
    except Exception:
        return False


def validate_spec(spec: StrategySpec) -> list[str]:
    """Validate a StrategySpec. Returns list of errors (empty = valid)."""
    errors = []
    if not spec.universe:
        errors.append("No ticker in universe")
    elif not validate_ticker(spec.universe[0]):
        errors.append(f"Ticker '{spec.universe[0]}' not found on yfinance")
    if not spec.entry_signal:
        errors.append("No entry signal")
    if not spec.exit_signal:
        errors.append("No exit signal")
    if spec.stop_loss_pct < 0 or spec.stop_loss_pct > 0.5:
        errors.append(f"stop_loss_pct={spec.stop_loss_pct} out of range [0, 0.5]")
    return errors
