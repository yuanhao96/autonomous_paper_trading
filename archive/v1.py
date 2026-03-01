"""v1: LLM generates a backtesting.py strategy class from a StrategySpec.

What's new vs v0:
- StrategySpec dataclass (hardcoded, you pick it)
- LLM call (OpenAI or Anthropic) that turns a spec into a Strategy class
- exec() the generated code, run the backtest

What's still manual: you write the spec, you judge the results.

Usage:
    python v1.py                # Uses OpenAI (default)
    python v1.py --provider openai
    python v1.py --provider anthropic
"""

import argparse
import os
from dataclasses import dataclass, field
from textwrap import dedent

import pandas as pd
import yfinance as yf
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# StrategySpec — the minimal description of a strategy
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


# ---------------------------------------------------------------------------
# LLM code generation
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = dedent("""\
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


def _build_user_prompt(spec: StrategySpec) -> str:
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


def _generate_openai(spec: StrategySpec) -> str:
    import openai

    client = openai.OpenAI()
    user_prompt = _build_user_prompt(spec)

    print("Calling OpenAI to generate strategy code...")
    response = client.chat.completions.create(
        model="gpt-5.2",
        max_completion_tokens=2000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content or ""


def _generate_anthropic(spec: StrategySpec) -> str:
    import anthropic

    client = anthropic.Anthropic()
    user_prompt = _build_user_prompt(spec)

    print("Calling Claude to generate strategy code...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


def generate_strategy_code(spec: StrategySpec, provider: str = "openai") -> str:
    """Generate a Strategy class from a spec using the chosen LLM provider."""
    if provider == "openai":
        code = _generate_openai(spec)
    elif provider == "anthropic":
        code = _generate_anthropic(spec)
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'openai' or 'anthropic'.")

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


def run_backtest(strategy_cls: type[Strategy], df: pd.DataFrame, spec: StrategySpec) -> None:
    """Run backtest and print results."""
    bt = Backtest(
        df,
        strategy_cls,
        cash=100_000,
        commission=0.001,
        exclusive_orders=True,
    )
    stats = bt.run()

    print("=" * 50)
    print(f"{spec.name}")
    print("=" * 50)
    print(f"Total Return:    {stats['Return [%]']:.2f}%")
    print(f"Buy & Hold:      {stats['Buy & Hold Return [%]']:.2f}%")
    print(f"Sharpe Ratio:    {stats['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown:    {stats['Max. Drawdown [%]']:.2f}%")
    print(f"# Trades:        {stats['# Trades']}")
    print(f"Win Rate:        {stats['Win Rate [%]']:.1f}%")
    print(f"Avg Trade:       {stats['Avg. Trade [%]']:.2f}%")
    print(f"Exposure Time:   {stats['Exposure Time [%]']:.1f}%")
    print("=" * 50)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="v1: LLM-generated backtesting.py strategy")
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic"],
        default="openai",
        help="LLM provider (default: openai)",
    )
    args = parser.parse_args()

    # Hardcoded spec — same SMA crossover as v0 so we can compare
    spec = StrategySpec(
        name="SMA Crossover (20/50)",
        knowledge_ref="strategies/momentum/momentum-effect-in-stocks.md",
        universe=["SPY"],
        timeframe="1d",
        entry_signal="SMA(20) crosses above SMA(50)",
        exit_signal="SMA(20) crosses below SMA(50)",
        stop_loss_pct=0.02,
        position_size_pct=0.95,
        params={"fast_period": 20, "slow_period": 50},
    )

    # Step 1: LLM generates strategy code
    code = generate_strategy_code(spec, provider=args.provider)
    print("--- Generated Code ---")
    print(code)
    print("--- End Generated Code ---\n")

    # Step 2: Load the generated class
    strategy_cls = load_strategy(code)

    # Step 3: Download data and run backtest
    df = download_data(spec.universe[0])
    run_backtest(strategy_cls, df, spec)


if __name__ == "__main__":
    main()
