"""Shared primitives: StrategySpec, LLM calls, codegen, evaluation."""

import json
from dataclasses import dataclass, field
from textwrap import dedent

import pandas as pd
import yfinance as yf
from backtesting import Strategy


# ---------------------------------------------------------------------------
# StrategySpec
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
# Unified LLM call
# ---------------------------------------------------------------------------


def llm_call(
    system: str, user: str, provider: str = "openai", max_tokens: int = 1500,
) -> str:
    """Call OpenAI or Anthropic with system+user messages. Returns text."""
    if provider == "openai":
        import openai

        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-5.2",
            max_completion_tokens=max_tokens,
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""
    elif provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            temperature=0,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text
    else:
        raise ValueError(f"Unknown provider: {provider}")


# ---------------------------------------------------------------------------
# Code generation: StrategySpec → backtesting.py code
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


def generate_strategy_code(spec: StrategySpec, provider: str = "openai") -> str:
    """Generate a Strategy class from a spec using the chosen LLM provider."""
    print(f"Generating strategy code via {provider}...")
    code = llm_call(CODE_SYSTEM_PROMPT, _build_code_prompt(spec), provider, max_tokens=2000)
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
# Data download
# ---------------------------------------------------------------------------


def download_data(
    ticker: str, start: str = "2020-01-01", end: str = "2025-12-31",
) -> pd.DataFrame:
    """Download OHLCV data, flatten multi-level columns from yfinance."""
    print(f"Downloading {ticker} daily data...")
    df = yf.download(ticker, start=start, end=end, progress=False)
    if hasattr(df.columns, "levels") and df.columns.nlevels > 1:
        df = df.droplevel(level=1, axis=1)
    print(f"Data: {len(df)} bars, {df.index[0].date()} to {df.index[-1].date()}\n")
    return df


# ---------------------------------------------------------------------------
# Evaluation thresholds
# ---------------------------------------------------------------------------

THRESHOLDS = {
    "min_trades_fail": 3,
    "min_trades_pass": 3,
    "sharpe_fail": 0.0,
    "sharpe_pass": 0.3,
    "max_drawdown_fail": -50.0,
    "max_drawdown_pass": -30.0,
    "return_fail": 0.0,
    "return_pass": 0.0,
}


def evaluate(stats: dict) -> tuple[str, list[str]]:
    """Evaluate backtest stats. Returns (verdict, reasons).

    Verdict: "PASS", "MARGINAL", or "FAIL".
    """
    reasons = []
    n_trades = stats.get("# Trades", 0)
    sharpe = stats.get("Sharpe Ratio", float("nan"))
    max_dd = stats.get("Max. Drawdown [%]", 0)
    total_return = stats.get("Return [%]", 0)

    # --- Hard fails ---
    if n_trades < THRESHOLDS["min_trades_fail"]:
        reasons.append(f"FAIL: only {n_trades} trades (min {THRESHOLDS['min_trades_fail']})")

    if sharpe < THRESHOLDS["sharpe_fail"]:
        reasons.append(f"FAIL: Sharpe {sharpe:.2f} < {THRESHOLDS['sharpe_fail']}")

    if max_dd < THRESHOLDS["max_drawdown_fail"]:
        reasons.append(f"FAIL: drawdown {max_dd:.1f}% < {THRESHOLDS['max_drawdown_fail']}%")

    if total_return < THRESHOLDS["return_fail"]:
        reasons.append(f"FAIL: return {total_return:.1f}% < {THRESHOLDS['return_fail']}%")

    if any(r.startswith("FAIL") for r in reasons):
        return "FAIL", reasons

    # --- Pass checks ---
    is_pass = True

    if n_trades < THRESHOLDS["min_trades_pass"]:
        reasons.append(f"MARGINAL: {n_trades} trades")
        is_pass = False

    if sharpe < THRESHOLDS["sharpe_pass"]:
        reasons.append(f"MARGINAL: Sharpe {sharpe:.2f} < {THRESHOLDS['sharpe_pass']}")
        is_pass = False

    if max_dd < THRESHOLDS["max_drawdown_pass"]:
        reasons.append(f"MARGINAL: drawdown {max_dd:.1f}% < {THRESHOLDS['max_drawdown_pass']}%")
        is_pass = False

    if is_pass:
        reasons.append(
            f"Sharpe {sharpe:.2f}, {n_trades} trades, "
            f"dd {max_dd:.1f}%, return {total_return:.1f}%"
        )
        return "PASS", reasons
    else:
        return "MARGINAL", reasons


# ---------------------------------------------------------------------------
# Reconstruct StrategySpec from dict
# ---------------------------------------------------------------------------


def spec_from_dict(d: dict) -> StrategySpec:
    """Reconstruct a StrategySpec from a serialized dict."""
    return StrategySpec(
        name=d["name"],
        knowledge_ref=d["knowledge_ref"],
        universe=d["universe"],
        timeframe=d.get("timeframe", "1d"),
        entry_signal=d["entry_signal"],
        exit_signal=d["exit_signal"],
        stop_loss_pct=d.get("stop_loss_pct", 0.02),
        position_size_pct=d.get("position_size_pct", 0.95),
        params=d.get("params", {}),
        adaptations=d.get("adaptations", []),
        skipped=d.get("skipped"),
    )


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------


def strip_markdown_fences(raw: str) -> str:
    """Strip markdown code fences from LLM output."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    return cleaned.strip()


def parse_llm_json(raw: str) -> dict:
    """Parse JSON from LLM output, stripping markdown fences."""
    return json.loads(strip_markdown_fences(raw))
