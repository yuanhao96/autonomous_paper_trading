"""Core primitives: FactorSpec, LLM calls, codegen, evaluation."""

import json
from dataclasses import dataclass, field
from typing import Any, Callable
from textwrap import dedent

import pandas as pd
import yfinance as yf
from backtesting import Strategy


# ---------------------------------------------------------------------------
# FactorSpec
# ---------------------------------------------------------------------------


@dataclass
class FactorSpec:
    name: str
    formula: str
    interpretation: str
    params: dict[str, Any] = field(default_factory=dict)
    param_ranges: dict[str, list] = field(default_factory=dict)
    category: str = ""
    source: str = ""
    factor_ref: str = ""
    factor_type: str = "time_series"


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
# Code generation: FactorSpec → backtesting.py code
# ---------------------------------------------------------------------------

FACTOR_CODE_SYSTEM_PROMPT = dedent("""\
    You are a Python code generator for backtesting.py strategies.

    You will receive an alpha factor formula and must output a SINGLE Python class that:
    - Inherits from backtesting.Strategy
    - Computes the alpha factor value from OHLCV data
    - Buys when alpha > 0, sells (goes flat) when alpha <= 0
    - Has class-level parameter attributes (for optimization)
    - Implements init() using self.I() to create the alpha indicator
    - Implements next() with entry/exit logic

    backtesting.py API reference:
    - self.data.Open, .High, .Low, .Close, .Volume — numpy-like arrays
    - self.I(func, *args) — wraps a function as an indicator. func receives raw arrays.
      Data passed to self.I() are numpy arrays, NOT pandas Series.
      To use pandas rolling/ewm, wrap with: pd.Series(values).rolling(n).mean()
    - self.buy() / self.sell() — market orders. Optional params: sl=, tp=, size=
    - self.position — current position. .close() to exit. .is_long / .is_short

    Operator reference (use these to translate the formula):
    - delay(x, d) → pd.Series(x).shift(d)
    - delta(x, d) → pd.Series(x).diff(d)
    - sma(x, d) → pd.Series(x).rolling(d).mean()
    - stddev(x, d) → pd.Series(x).rolling(d).std()
    - correlation(x, y, d) → pd.Series(x).rolling(d).corr(pd.Series(y))
    - ts_min(x, d) → pd.Series(x).rolling(d).min()
    - ts_max(x, d) → pd.Series(x).rolling(d).max()
    - ts_rank(x, d) → pd.Series(x).rolling(d).apply(lambda s: s.rank().iloc[-1]/len(s))
    - sum(x, d) → pd.Series(x).rolling(d).sum()
    - decay_linear(x, d) → pd.Series(x).rolling(d).apply(lambda s: np.dot(s, np.arange(1,d+1))/np.arange(1,d+1).sum())
    - sign(x) → np.sign(x)
    - log(x) → np.log(x)
    - where(cond, a, b) → np.where(cond, a, b)

    Rules:
    1. Output ONLY the Python code. No markdown, no explanation, no ```python blocks.
    2. Start with necessary imports (pandas, numpy, etc.)
    3. The class must be named GeneratedStrategy.
    4. Use class-level params matching the spec's params dict.
    5. In init(), define a helper function that computes the alpha from raw arrays,
       then wrap it with self.I().
    6. In next(), buy when alpha > 0 and not already long.
       Set stop-loss: sl=self.data.Close[-1] * (1 - 0.02).
       Close position when alpha <= 0 and currently long.
    7. Guard against division by zero with + 1e-8 in denominators.
    8. Keep it simple. Translate the formula directly.
    9. Cast volume to float: pd.Series(volume).astype(float).
""")


def _build_factor_code_prompt(spec: FactorSpec) -> str:
    return dedent(f"""\
        Generate a backtesting.py Strategy class for this alpha factor:

        Name: {spec.name}
        Formula: {spec.formula}
        Parameters: {spec.params}

        The strategy:
        - Computes the alpha factor value each day
        - Goes LONG (buy) when alpha > 0
        - Goes FLAT (close position) when alpha <= 0
        - Uses 2% stop-loss below entry: sl=self.data.Close[-1] * 0.98
        - Position size: 95% of equity (size=0.95)

        Remember:
        - Class name must be GeneratedStrategy
        - self.I() receives numpy arrays, use pd.Series() wrapper for rolling operations
        - No markdown fences, just raw Python code
    """)


def generate_factor_code(spec: FactorSpec, provider: str = "openai") -> str:
    """Generate a Strategy class from a FactorSpec using the chosen LLM."""
    print(f"Generating factor code via {provider}...")
    code = llm_call(
        FACTOR_CODE_SYSTEM_PROMPT, _build_factor_code_prompt(spec),
        provider, max_tokens=2000,
    )
    print(f"Generated {len(code.splitlines())} lines of code.\n")
    return code


# ---------------------------------------------------------------------------
# Code execution
# ---------------------------------------------------------------------------


def load_strategy(code: str) -> type[Strategy]:
    """Execute generated code and extract the GeneratedStrategy class."""
    # Strip markdown fences the LLM may have included
    code = strip_markdown_fences(code)

    # Compile first to catch syntax errors with clear messages
    try:
        compile(code, "<generated>", "exec")
    except SyntaxError as e:
        raise RuntimeError(f"Generated code has syntax error: {e}") from e

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


# ---------------------------------------------------------------------------
# Cross-sectional code generation
# ---------------------------------------------------------------------------

XS_FACTOR_CODE_SYSTEM_PROMPT = dedent("""\
    You are a Python code generator for cross-sectional alpha factors.

    You will receive an alpha factor formula and must output a SINGLE Python function:

    ```
    def compute_alpha(universe_data: dict[str, pd.DataFrame], **params) -> pd.DataFrame:
        \"\"\"Returns DataFrame(index=dates, columns=tickers, values=alpha).\"\"\"
    ```

    The function receives:
    - universe_data: dict mapping ticker -> DataFrame with columns [Open, High, Low, Close, Volume]
    - **params: keyword arguments matching the factor's parameter dict

    How to build panels from universe_data:
    - close = pd.DataFrame({t: d["Close"] for t, d in universe_data.items()})
    - open_ = pd.DataFrame({t: d["Open"] for t, d in universe_data.items()})
    - high = pd.DataFrame({t: d["High"] for t, d in universe_data.items()})
    - low = pd.DataFrame({t: d["Low"] for t, d in universe_data.items()})
    - volume = pd.DataFrame({t: d["Volume"] for t, d in universe_data.items()}).astype(float)

    Operator reference (translate the formula using these):
    - rank(x) → x.rank(axis=1, pct=True)  # ranks across tickers at each date
    - delay(x, d) → x.shift(d)            # shift forward in time (per column)
    - delta(x, d) → x.diff(d)             # difference over d periods (per column)
    - returns → close.pct_change(1)
    - sma(x, d) → x.rolling(d).mean()
    - stddev(x, d) → x.rolling(d).std()
    - correlation(x, y, d) → x.rolling(d).corr(y)  # per-column rolling corr
    - covariance(x, y, d) → x.rolling(d).cov(y)    # per-column rolling cov
    - ts_min(x, d) → x.rolling(d).min()
    - ts_max(x, d) → x.rolling(d).max()
    - ts_rank(x, d) → x.rolling(d).apply(lambda s: s.rank().iloc[-1] / len(s), raw=False)
    - ts_argmax(x, d) → x.rolling(d).apply(lambda s: s.argmax(), raw=True)
    - sum(x, d) → x.rolling(d).sum()
    - decay_linear(x, d) → x.rolling(d).apply(
        lambda s: np.dot(s, np.arange(1, d+1)) / np.arange(1, d+1).sum(), raw=True)
    - sign(x) → np.sign(x)
    - log(x) → np.log(x)
    - abs(x) → np.abs(x) or x.abs()
    - where(cond, a, b) → np.where(cond, a, b)  (wrap result with pd.DataFrame if needed)
    - SignedPower(x, e) → np.sign(x) * np.abs(x)**e
    - product(x, d) → x.rolling(d).apply(np.prod, raw=True)
    - max(x, d) → x.rolling(d).max()  (when used as ts_max)
    - min(x, d) → x.rolling(d).min()  (when used as ts_min)

    IMPORTANT:
    - Time-series ops (shift, diff, rolling) apply per-column as usual.
    - Cross-sectional ops (rank) apply across columns (axis=1) at each date.
    - The returned DataFrame must have shape (dates × tickers) matching the input panels.
    - Guard against division by zero with + 1e-8 in denominators.
    - Cast volume to float.

    Rules:
    1. Output ONLY the Python code. No markdown, no explanation, no ```python blocks.
    2. Start with necessary imports (pandas, numpy).
    3. The function must be named compute_alpha.
    4. Use **params to accept parameter overrides. Extract with params.get("name", default).
    5. Keep it simple. Translate the formula directly.
    6. Align panels on shared index before operations: use .dropna() at the end if needed.
""")


def _build_xs_factor_code_prompt(spec: FactorSpec) -> str:
    return dedent(f"""\
        Generate a compute_alpha function for this cross-sectional alpha factor:

        Name: {spec.name}
        Formula: {spec.formula}
        Parameters: {spec.params}

        The function signature:
        def compute_alpha(universe_data: dict[str, pd.DataFrame], **params) -> pd.DataFrame:

        Remember:
        - Function name must be compute_alpha
        - rank(x) = x.rank(axis=1, pct=True) — cross-sectional ranking
        - Time-series ops apply per-column
        - No markdown fences, just raw Python code
    """)


def generate_xs_factor_code(spec: FactorSpec, provider: str = "openai") -> str:
    """Generate a compute_alpha function from a FactorSpec using the chosen LLM."""
    print(f"Generating cross-sectional factor code via {provider}...")
    code = llm_call(
        XS_FACTOR_CODE_SYSTEM_PROMPT, _build_xs_factor_code_prompt(spec),
        provider, max_tokens=2000,
    )
    print(f"Generated {len(code.splitlines())} lines of code.\n")
    return code


def load_xs_alpha(code: str) -> Callable:
    """Execute generated code and extract the compute_alpha function."""
    code = strip_markdown_fences(code)

    try:
        compile(code, "<generated>", "exec")
    except SyntaxError as e:
        raise RuntimeError(f"Generated code has syntax error: {e}") from e

    namespace: dict = {}
    exec(code, namespace)

    fn = namespace.get("compute_alpha")
    if fn is None:
        raise RuntimeError(
            "Generated code does not define 'compute_alpha'.\n"
            f"Defined names: {[k for k in namespace if not k.startswith('_')]}"
        )
    if not callable(fn):
        raise RuntimeError(f"compute_alpha is not callable: {type(fn)}")
    return fn  # type: ignore[no-any-return]
