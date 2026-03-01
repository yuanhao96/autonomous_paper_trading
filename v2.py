"""v2: LLM reads a knowledge doc and produces a StrategySpec.

What's new vs v1:
- LLM reads a knowledge base markdown doc and extracts a StrategySpec (JSON)
- StrategySpec gains 'adaptations' and 'skipped' fields
- Validation: check ticker exists, check zero trades
- Two LLM calls: knowledge doc → spec, spec → code

What's still manual: you pick which knowledge doc to feed it.

Usage:
    python v2.py knowledge/strategies/momentum/momentum-effect-in-stocks.md
    python v2.py knowledge/strategies/technical-and-other/ichimoku-cloud.md --provider anthropic
    python v2.py knowledge/strategies/calendar-anomalies/pre-holiday-effect.md
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent

import pandas as pd
import yfinance as yf
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from dotenv import load_dotenv

load_dotenv()

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

# ---------------------------------------------------------------------------
# StrategySpec — extended with adaptations tracking
# ---------------------------------------------------------------------------


@dataclass
class StrategySpec:
    name: str
    knowledge_ref: str
    universe: list[str]
    timeframe: str
    entry_signal: str
    exit_signal: str
    stop_loss_pct: float
    position_size_pct: float
    params: dict = field(default_factory=dict)
    adaptations: list[str] = field(default_factory=list)
    skipped: str | None = None


# ---------------------------------------------------------------------------
# Step 1: Knowledge doc → StrategySpec (NEW in v2)
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


def _extract_spec_openai(knowledge_text: str, knowledge_ref: str) -> StrategySpec:
    import openai

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-5.2",
        max_completion_tokens=1500,
        temperature=0,
        messages=[
            {"role": "system", "content": SPEC_SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract a StrategySpec from this document:\n\n{knowledge_text}"},
        ],
    )
    raw = response.choices[0].message.content or ""
    return _parse_spec_json(raw, knowledge_ref)


def _extract_spec_anthropic(knowledge_text: str, knowledge_ref: str) -> StrategySpec:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        temperature=0,
        system=SPEC_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Extract a StrategySpec from this document:\n\n{knowledge_text}"},
        ],
    )
    raw = response.content[0].text
    return _parse_spec_json(raw, knowledge_ref)


def _parse_spec_json(raw: str, knowledge_ref: str) -> StrategySpec:
    """Parse LLM JSON output into a StrategySpec."""
    # Strip markdown fences if the LLM added them despite instructions
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()

    data = json.loads(cleaned)

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
    knowledge_ref = str(path.relative_to(Path(__file__).resolve().parent))

    print(f"Reading: {knowledge_ref}")
    print(f"Extracting StrategySpec via {provider}...")

    if provider == "openai":
        return _extract_spec_openai(knowledge_text, knowledge_ref)
    elif provider == "anthropic":
        return _extract_spec_anthropic(knowledge_text, knowledge_ref)
    else:
        raise ValueError(f"Unknown provider: {provider}")


# ---------------------------------------------------------------------------
# Step 2: StrategySpec → code (reused from v1)
# ---------------------------------------------------------------------------

CODE_SYSTEM_PROMPT = dedent("""\
    You are a Python code generator for backtesting.py strategies.

    You will receive a StrategySpec and must output a SINGLE Python class that:
    - Inherits from backtesting.Strategy
    - Has class-level parameter attributes (for optimization)
    - Implements init() using self.I() to create indicators
    - Implements next() with entry/exit logic using self.buy(), self.sell(), self.position.close()

    backtesting.py API reference:
    - self.data.Open, .High, .Low, .Close, .Volume — numpy-like arrays
    - self.I(func, *args) — wraps a function as an indicator. func receives raw arrays.
      Data passed to self.I() are numpy arrays, NOT pandas Series.
      To use pandas rolling/ewm, wrap with: pd.Series(values).rolling(n).mean()
    - self.buy() / self.sell() — market orders. Optional params: sl=, tp=, size=
    - self.position — current position. .close() to exit. .is_long / .is_short
    - crossover(series1, series2) — True if series1 just crossed above series2

    Rules:
    1. Output ONLY the Python code. No markdown, no explanation, no ```python blocks.
    2. Start with necessary imports (pandas, numpy, etc.)
    3. Import crossover from backtesting.lib if needed.
    4. The class must be named GeneratedStrategy.
    5. Use helper functions for indicators (def sma(values, n): return pd.Series(values)...).
    6. Class-level params must match the spec's params dict.
    7. Implement stop-loss via sl= parameter in buy()/sell() if stop_loss_pct > 0.
    8. Keep it simple. No unnecessary complexity.
""")


def _build_code_prompt(spec: StrategySpec) -> str:
    return dedent(f"""\
        Generate a backtesting.py Strategy class for this spec:

        Name: {spec.name}
        Entry signal: {spec.entry_signal}
        Exit signal: {spec.exit_signal}
        Stop loss: {spec.stop_loss_pct:.1%} below entry
        Position size: {spec.position_size_pct:.0%} of equity
        Parameters: {spec.params}

        Remember:
        - Class name must be GeneratedStrategy
        - self.I() receives numpy arrays, use pd.Series() wrapper for rolling operations
        - Use crossover() from backtesting.lib for crossover signals
    """)


def _generate_code_openai(spec: StrategySpec) -> str:
    import openai

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-5.2",
        max_completion_tokens=2000,
        temperature=0,
        messages=[
            {"role": "system", "content": CODE_SYSTEM_PROMPT},
            {"role": "user", "content": _build_code_prompt(spec)},
        ],
    )
    return response.choices[0].message.content or ""


def _generate_code_anthropic(spec: StrategySpec) -> str:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        temperature=0,
        system=CODE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_code_prompt(spec)}],
    )
    return response.content[0].text


def generate_strategy_code(spec: StrategySpec, provider: str = "openai") -> str:
    """Generate a Strategy class from a spec using the chosen LLM provider."""
    print(f"Generating strategy code via {provider}...")
    if provider == "openai":
        code = _generate_code_openai(spec)
    elif provider == "anthropic":
        code = _generate_code_anthropic(spec)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    print(f"Generated {len(code.splitlines())} lines of code.\n")
    return code


# ---------------------------------------------------------------------------
# Code execution
# ---------------------------------------------------------------------------


def load_strategy(code: str) -> type[Strategy]:
    """Execute generated code and extract the GeneratedStrategy class."""
    namespace: dict = {}
    exec(code, namespace)

    strategy_cls = namespace.get("GeneratedStrategy")
    if strategy_cls is None:
        raise RuntimeError(
            "Generated code does not define 'GeneratedStrategy'.\n"
            f"Defined names: {[k for k in namespace if not k.startswith('_')]}"
        )
    if not (isinstance(strategy_cls, type) and issubclass(strategy_cls, Strategy)):
        raise RuntimeError(
            f"GeneratedStrategy is not a backtesting.Strategy subclass: {type(strategy_cls)}"
        )
    return strategy_cls


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


# ---------------------------------------------------------------------------
# Data + backtest
# ---------------------------------------------------------------------------


def download_data(ticker: str, start: str = "2020-01-01", end: str = "2025-12-31") -> pd.DataFrame:
    """Download OHLCV data, flatten multi-level columns from yfinance."""
    print(f"Downloading {ticker} daily data...")
    df = yf.download(ticker, start=start, end=end, progress=False)
    if hasattr(df.columns, "levels") and df.columns.nlevels > 1:
        df = df.droplevel(level=1, axis=1)
    print(f"Data: {len(df)} bars, {df.index[0].date()} to {df.index[-1].date()}\n")
    return df


def run_backtest(strategy_cls: type[Strategy], df: pd.DataFrame, spec: StrategySpec) -> dict:
    """Run backtest and return stats dict. Also prints results."""
    bt = Backtest(
        df,
        strategy_cls,
        cash=100_000,
        commission=0.001,
        exclusive_orders=True,
    )
    stats = bt.run()

    n_trades = stats["# Trades"]

    print("=" * 55)
    print(f"  {spec.name}")
    print(f"  Ticker: {spec.universe[0]}  |  {df.index[0].date()} to {df.index[-1].date()}")
    print("=" * 55)

    if n_trades == 0:
        print("  ** ZERO TRADES — strategy never triggered **")
    else:
        print(f"  Total Return:    {stats['Return [%]']:.2f}%")
        print(f"  Buy & Hold:      {stats['Buy & Hold Return [%]']:.2f}%")
        print(f"  Sharpe Ratio:    {stats['Sharpe Ratio']:.2f}")
        print(f"  Max Drawdown:    {stats['Max. Drawdown [%]']:.2f}%")
        print(f"  # Trades:        {n_trades}")
        print(f"  Win Rate:        {stats['Win Rate [%]']:.1f}%")
        print(f"  Avg Trade:       {stats['Avg. Trade [%]']:.2f}%")
        print(f"  Exposure Time:   {stats['Exposure Time [%]']:.1f}%")

    if spec.adaptations:
        print("-" * 55)
        print("  Adaptations from original strategy:")
        for a in spec.adaptations:
            print(f"    - {a}")

    print("=" * 55)
    return dict(stats)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="v2: LLM reads a knowledge doc → StrategySpec → code → backtest"
    )
    parser.add_argument("knowledge_doc", help="Path to a knowledge base markdown file")
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic"],
        default="openai",
        help="LLM provider (default: openai)",
    )
    args = parser.parse_args()

    # Step 1: Knowledge doc → StrategySpec
    spec = extract_spec(args.knowledge_doc, provider=args.provider)

    if spec.skipped:
        print(f"\n** SKIPPED: {spec.name} **")
        print(f"   Reason: {spec.skipped}")
        sys.exit(0)

    print(f"\n--- Extracted Spec ---")
    print(f"  Name:           {spec.name}")
    print(f"  Ticker:         {spec.universe}")
    print(f"  Entry:          {spec.entry_signal}")
    print(f"  Exit:           {spec.exit_signal}")
    print(f"  Stop Loss:      {spec.stop_loss_pct:.1%}")
    print(f"  Position Size:  {spec.position_size_pct:.0%}")
    print(f"  Params:         {spec.params}")
    if spec.adaptations:
        print(f"  Adaptations:    {spec.adaptations}")
    print(f"--- End Spec ---\n")

    # Step 1b: Validate spec
    errors = validate_spec(spec)
    if errors:
        print("** Spec validation failed:")
        for e in errors:
            print(f"   - {e}")
        sys.exit(1)

    # Step 2: StrategySpec → code
    code = generate_strategy_code(spec, provider=args.provider)
    print("--- Generated Code ---")
    print(code)
    print("--- End Generated Code ---\n")

    # Step 3: Load strategy
    try:
        strategy_cls = load_strategy(code)
    except Exception as e:
        print(f"** Code loading failed: {e}")
        sys.exit(1)

    # Step 4: Download data and run backtest
    df = download_data(spec.universe[0])
    run_backtest(strategy_cls, df, spec)


if __name__ == "__main__":
    main()
