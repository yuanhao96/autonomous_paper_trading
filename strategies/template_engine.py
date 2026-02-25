"""Template engine that compiles declarative StrategySpec into executable Strategy.

The LLM generates JSON specs; this module turns them into real strategies
compatible with the existing backtester and execution pipeline.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from strategies.base import Strategy
from strategies.indicators import INDICATOR_REGISTRY, MULTI_OUTPUT_INDICATORS
from strategies.spec import (
    CompositeCondition,
    ConditionSpec,
    StrategySpec,
)
from trading.executor import Signal

logger = logging.getLogger(__name__)


class TemplateStrategy(Strategy):
    """Strategy compiled from a declarative ``StrategySpec``."""

    def __init__(self, spec: StrategySpec) -> None:
        errors = spec.validate()
        if errors:
            raise ValueError(f"Invalid StrategySpec: {errors}")
        self._spec = spec

    @property
    def name(self) -> str:
        return self._spec.name

    @property
    def version(self) -> str:
        return self._spec.version

    @property
    def spec(self) -> StrategySpec:
        return self._spec

    def describe(self) -> str:
        return self._spec.description or f"Template strategy: {self._spec.name}"

    _REQUIRED_COLUMNS = {"Open", "High", "Low", "Close", "Volume"}

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Compute indicators and evaluate entry/exit conditions."""
        if len(data) < 2:
            return []

        missing = self._REQUIRED_COLUMNS - set(data.columns)
        if missing:
            logger.warning("Data missing required columns %s; returning no signals", missing)
            return []

        # 1. Compute all indicators.
        values = self._compute_indicators(data)

        # 2. Evaluate entry and exit conditions.
        ticker = data.attrs.get("ticker", "UNKNOWN")

        signals: list[Signal] = []
        entry_met, entry_strength = self._evaluate_composite(
            self._spec.entry_conditions, values, data
        )
        exit_met, exit_strength = self._evaluate_composite(
            self._spec.exit_conditions, values, data
        )

        if entry_met:
            signals.append(
                Signal(
                    ticker=ticker,
                    action="buy",
                    strength=max(0.01, min(entry_strength, 1.0)),
                    reason=f"{self.name} entry conditions met",
                    strategy_name=self.name,
                )
            )
        elif exit_met:
            signals.append(
                Signal(
                    ticker=ticker,
                    action="sell",
                    strength=max(0.01, min(exit_strength, 1.0)),
                    reason=f"{self.name} exit conditions met",
                    strategy_name=self.name,
                )
            )

        return signals

    # ------------------------------------------------------------------
    # Indicator computation
    # ------------------------------------------------------------------

    def _compute_indicators(self, data: pd.DataFrame) -> dict[str, pd.Series]:
        """Compute all declared indicators, handling one level of nesting."""
        values: dict[str, pd.Series] = {}

        # Build a mapping from output_key to IndicatorSpec for dependency resolution.
        spec_map = {ind.output_key: ind for ind in self._spec.indicators}

        for ind in self._spec.indicators:
            self._compute_single(ind, data, values, spec_map)

        return values

    def _compute_single(
        self,
        ind: "strategies.spec.IndicatorSpec",  # noqa: F821
        data: pd.DataFrame,
        values: dict[str, pd.Series],
        spec_map: dict,
    ) -> None:
        """Compute one indicator, resolving nested source dependencies."""
        if ind.output_key in values:
            return  # Already computed.

        func = INDICATOR_REGISTRY.get(ind.name)
        if func is None:
            logger.warning("Indicator '%s' not found in registry; skipping", ind.name)
            values[ind.output_key] = pd.Series(dtype=float)
            return

        params = dict(ind.params)

        # Handle nesting: if source references another indicator's output_key.
        source = params.get("source", "")
        if isinstance(source, str) and source in spec_map and source not in values:
            # Compute the dependency first.
            self._compute_single(spec_map[source], data, values, spec_map)

        try:
            if isinstance(source, str) and source in values:
                # Build a temporary DataFrame with the dependent indicator as the source column.
                temp_data = data.copy()
                temp_data[source] = values[source]
                params["source"] = source
                result = func(temp_data, **params)
            else:
                result = func(data, **params)
        except Exception:
            logger.warning(
                "Indicator '%s' (output_key='%s') computation failed; using empty series",
                ind.name, ind.output_key, exc_info=True,
            )
            values[ind.output_key] = pd.Series(dtype=float)
            return

        if ind.name in MULTI_OUTPUT_INDICATORS:
            # Multi-output: store each sub-key with suffix.
            for sub_key, series in result.items():
                values[f"{ind.output_key}_{sub_key}"] = series
        else:
            values[ind.output_key] = result

    # ------------------------------------------------------------------
    # Condition evaluation
    # ------------------------------------------------------------------

    def _evaluate_composite(
        self,
        composite: CompositeCondition,
        values: dict[str, pd.Series],
        data: pd.DataFrame,
    ) -> tuple[bool, float]:
        """Evaluate a composite condition, returning (met, strength)."""
        results: list[tuple[bool, float]] = []

        for cond in composite.conditions:
            met, strength = self._evaluate_condition(cond, values, data)
            results.append((met, strength))

        for nested in composite.nested:
            met, strength = self._evaluate_composite(nested, values, data)
            results.append((met, strength))

        if not results:
            return False, 0.0

        if composite.logic == "ALL_OF":
            all_met = all(r[0] for r in results)
            avg_strength = sum(r[1] for r in results) / len(results) if all_met else 0.0
            return all_met, avg_strength
        else:  # ANY_OF
            any_met = any(r[0] for r in results)
            if any_met:
                met_strengths = [r[1] for r in results if r[0]]
                return True, sum(met_strengths) / len(met_strengths)
            return False, 0.0

    def _evaluate_condition(
        self,
        cond: ConditionSpec,
        values: dict[str, pd.Series],
        data: pd.DataFrame,
    ) -> tuple[bool, float]:
        """Evaluate a single condition, returning (met, strength in [0,1])."""
        try:
            left = self._resolve_operand(cond.left, values, data)
            right = self._resolve_operand(cond.right, values, data) if cond.right else None

            if cond.operator == "cross_above":
                return self._cross_above(left, right)
            elif cond.operator == "cross_below":
                return self._cross_below(left, right)
            elif cond.operator == "greater_than":
                return self._greater_than(left, right)
            elif cond.operator == "less_than":
                return self._less_than(left, right)
            elif cond.operator == "between":
                low = float(cond.params.get("low", 0))
                high = float(cond.params.get("high", 100))
                return self._between(left, low, high)
            elif cond.operator == "slope_positive":
                lookback = int(cond.params.get("lookback", 5))
                return self._slope_positive(left, lookback)
            elif cond.operator == "percent_change":
                lookback = int(cond.params.get("lookback", 5))
                threshold = float(cond.params.get("threshold", 0.0))
                return self._percent_change(left, lookback, threshold)
            else:
                logger.warning("Unknown condition operator: %s", cond.operator)
                return False, 0.0
        except Exception:
            logger.debug("Condition evaluation failed for %s", cond.operator, exc_info=True)
            return False, 0.0

    @staticmethod
    def _resolve_operand(
        ref: str,
        values: dict[str, pd.Series],
        data: pd.DataFrame,
    ) -> pd.Series | float:
        """Resolve an operand to a Series or a float constant."""
        if ref in values:
            return values[ref]
        try:
            return float(ref)
        except (ValueError, TypeError):
            # Fall back to a data column.
            if ref in data.columns:
                return data[ref]
            raise ValueError(f"Cannot resolve operand '{ref}'")

    # ------------------------------------------------------------------
    # Operator implementations
    # ------------------------------------------------------------------

    @staticmethod
    def _to_float(val: pd.Series | float, idx: int = -1) -> float:
        """Extract a scalar from a Series or return the float directly."""
        if isinstance(val, (int, float)):
            return float(val)
        v = val.iloc[idx]
        return float(v) if not pd.isna(v) else float("nan")

    @staticmethod
    def _cross_above(
        left: pd.Series | float, right: pd.Series | float
    ) -> tuple[bool, float]:
        l_cur = TemplateStrategy._to_float(left, -1)
        l_prev = TemplateStrategy._to_float(left, -2)
        r_cur = TemplateStrategy._to_float(right, -1)
        r_prev = TemplateStrategy._to_float(right, -2)

        if any(np.isnan(v) for v in [l_cur, l_prev, r_cur, r_prev]):
            return False, 0.0

        met = l_prev <= r_prev and l_cur > r_cur
        if met and r_cur != 0:
            strength = min(abs(l_cur - r_cur) / abs(r_cur), 1.0)
        else:
            strength = 0.5 if met else 0.0
        return met, strength

    @staticmethod
    def _cross_below(
        left: pd.Series | float, right: pd.Series | float
    ) -> tuple[bool, float]:
        l_cur = TemplateStrategy._to_float(left, -1)
        l_prev = TemplateStrategy._to_float(left, -2)
        r_cur = TemplateStrategy._to_float(right, -1)
        r_prev = TemplateStrategy._to_float(right, -2)

        if any(np.isnan(v) for v in [l_cur, l_prev, r_cur, r_prev]):
            return False, 0.0

        met = l_prev >= r_prev and l_cur < r_cur
        if met and r_cur != 0:
            strength = min(abs(r_cur - l_cur) / abs(r_cur), 1.0)
        else:
            strength = 0.5 if met else 0.0
        return met, strength

    @staticmethod
    def _greater_than(
        left: pd.Series | float, right: pd.Series | float
    ) -> tuple[bool, float]:
        lv = TemplateStrategy._to_float(left)
        rv = TemplateStrategy._to_float(right)
        if np.isnan(lv) or np.isnan(rv):
            return False, 0.0
        met = lv > rv
        if met and rv != 0:
            strength = min(abs(lv - rv) / abs(rv), 1.0)
        else:
            strength = 0.5 if met else 0.0
        return met, strength

    @staticmethod
    def _less_than(
        left: pd.Series | float, right: pd.Series | float
    ) -> tuple[bool, float]:
        lv = TemplateStrategy._to_float(left)
        rv = TemplateStrategy._to_float(right)
        if np.isnan(lv) or np.isnan(rv):
            return False, 0.0
        met = lv < rv
        if met and rv != 0:
            strength = min(abs(rv - lv) / abs(rv), 1.0)
        else:
            strength = 0.5 if met else 0.0
        return met, strength

    @staticmethod
    def _between(
        left: pd.Series | float, low: float, high: float
    ) -> tuple[bool, float]:
        lv = TemplateStrategy._to_float(left)
        if np.isnan(lv):
            return False, 0.0
        met = low <= lv <= high
        if met and (high - low) > 0:
            mid = (high + low) / 2.0
            strength = 1.0 - abs(lv - mid) / ((high - low) / 2.0)
            strength = max(0.0, min(strength, 1.0))
        else:
            strength = 0.0
        return met, strength

    @staticmethod
    def _slope_positive(left: pd.Series | float, lookback: int) -> tuple[bool, float]:
        if isinstance(left, (int, float)):
            return False, 0.0
        if len(left) < lookback:
            return False, 0.0

        segment = left.iloc[-lookback:].dropna()
        if len(segment) < 2:
            return False, 0.0

        x = np.arange(len(segment), dtype=float)
        y = segment.values.astype(float)
        slope = np.polyfit(x, y, 1)[0]

        met = slope > 0
        # Normalize strength by the mean of the segment.
        mean_val = np.mean(np.abs(y))
        if mean_val > 0:
            strength = min(abs(slope) / mean_val, 1.0)
        else:
            strength = 0.5
        return met, strength

    @staticmethod
    def _percent_change(
        left: pd.Series | float, lookback: int, threshold: float
    ) -> tuple[bool, float]:
        if isinstance(left, (int, float)):
            return False, 0.0
        if len(left) < lookback:
            return False, 0.0

        cur = float(left.iloc[-1])
        prev = float(left.iloc[-lookback])
        if pd.isna(cur) or pd.isna(prev) or prev == 0:
            return False, 0.0

        pct = (cur - prev) / abs(prev)
        met = pct > threshold
        strength = min(abs(pct - threshold), 1.0) if met else 0.0
        return met, strength


def compile_spec(spec: StrategySpec) -> TemplateStrategy:
    """Convenience: validate and compile a spec into an executable strategy."""
    return TemplateStrategy(spec)
