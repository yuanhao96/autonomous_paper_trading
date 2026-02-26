"""Declarative strategy specification schema.

Defines the JSON-serializable dataclasses that describe a trading strategy
without any executable Python.  The template engine compiles a
``StrategySpec`` into an executable ``TemplateStrategy``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from strategies.indicators import INDICATOR_REGISTRY, MULTI_OUTPUT_INDICATORS

# ---------------------------------------------------------------------------
# Condition operators recognised by the template engine
# ---------------------------------------------------------------------------

VALID_OPERATORS: set[str] = {
    "cross_above",
    "cross_below",
    "greater_than",
    "less_than",
    "between",
    "slope_positive",
    "percent_change",
}

VALID_LOGIC: set[str] = {"ALL_OF", "ANY_OF"}

# Raw OHLCV columns that can be referenced in conditions alongside
# indicator output_keys (the template engine resolves them from the DataFrame).
PRICE_COLUMNS: set[str] = {"Open", "High", "Low", "Close", "Volume"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class IndicatorSpec:
    """Specification for one indicator computation.

    Parameters
    ----------
    name:
        Indicator function name (must exist in ``INDICATOR_REGISTRY``).
    params:
        Keyword arguments forwarded to the indicator function.
        If ``params["source"]`` matches another indicator's ``output_key``,
        the engine computes the dependency first (one nesting level).
    output_key:
        Name used to reference this indicator's result elsewhere in the spec.
    """

    name: str
    params: dict[str, Any]
    output_key: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "params": dict(self.params), "output_key": self.output_key}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IndicatorSpec:
        return cls(name=d["name"], params=dict(d.get("params", {})), output_key=d["output_key"])


@dataclass
class ConditionSpec:
    """A single boolean condition comparing indicator values.

    ``left`` and ``right`` reference ``output_key`` names or are float
    constants (encoded as strings like ``"30.0"``).
    """

    operator: str
    left: str
    right: str = ""
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"operator": self.operator, "left": self.left}
        if self.right:
            d["right"] = self.right
        if self.params:
            d["params"] = dict(self.params)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ConditionSpec:
        return cls(
            operator=d["operator"],
            left=d["left"],
            right=d.get("right", ""),
            params=dict(d.get("params", {})),
        )


@dataclass
class CompositeCondition:
    """A composite boolean expression combining conditions.

    ``logic`` is ``"ALL_OF"`` (all must be true) or ``"ANY_OF"`` (any true).
    One level of ``nested`` composites is allowed.
    """

    logic: str
    conditions: list[ConditionSpec] = field(default_factory=list)
    nested: list[CompositeCondition] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "logic": self.logic,
            "conditions": [c.to_dict() for c in self.conditions],
        }
        if self.nested:
            d["nested"] = [n.to_dict() for n in self.nested]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CompositeCondition:
        conditions = [ConditionSpec.from_dict(c) for c in d.get("conditions", [])]
        nested = [CompositeCondition.from_dict(n) for n in d.get("nested", [])]
        return cls(logic=d["logic"], conditions=conditions, nested=nested)


@dataclass
class RiskParams:
    """Risk management parameters attached to a strategy spec."""

    stop_loss_pct: float = 5.0
    take_profit_pct: float = 10.0
    trailing_stop_pct: float = 0.0
    max_holding_days: int = 0
    position_size_method: str = "equal_weight"
    max_positions: int = 5

    def to_dict(self) -> dict[str, Any]:
        return {
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "trailing_stop_pct": self.trailing_stop_pct,
            "max_holding_days": self.max_holding_days,
            "position_size_method": self.position_size_method,
            "max_positions": self.max_positions,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RiskParams:
        return cls(
            stop_loss_pct=float(d.get("stop_loss_pct", 5.0)),
            take_profit_pct=float(d.get("take_profit_pct", 10.0)),
            trailing_stop_pct=float(d.get("trailing_stop_pct", 0.0)),
            max_holding_days=int(d.get("max_holding_days", 0)),
            position_size_method=str(d.get("position_size_method", "equal_weight")),
            max_positions=int(d.get("max_positions", 5)),
        )


@dataclass
class StrategySpec:
    """Complete declarative strategy specification.

    This is the contract between the LLM generator and the template engine.
    """

    name: str
    version: str
    description: str
    indicators: list[IndicatorSpec]
    entry_conditions: CompositeCondition
    exit_conditions: CompositeCondition
    risk: RiskParams = field(default_factory=RiskParams)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "indicators": [i.to_dict() for i in self.indicators],
            "entry_conditions": self.entry_conditions.to_dict(),
            "exit_conditions": self.exit_conditions.to_dict(),
            "risk": self.risk.to_dict(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> StrategySpec:
        return cls(
            name=d["name"],
            version=d.get("version", "0.1.0"),
            description=d.get("description", ""),
            indicators=[IndicatorSpec.from_dict(i) for i in d["indicators"]],
            entry_conditions=CompositeCondition.from_dict(d["entry_conditions"]),
            exit_conditions=CompositeCondition.from_dict(d["exit_conditions"]),
            risk=RiskParams.from_dict(d.get("risk", {})),
            metadata=dict(d.get("metadata", {})),
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> list[str]:
        """Validate the spec and return a list of error messages (empty = valid)."""
        errors: list[str] = []

        if not self.name or not self.name.strip():
            errors.append("Strategy name is required.")

        # Check indicator names.
        output_keys: set[str] = set()
        for ind in self.indicators:
            if ind.name not in INDICATOR_REGISTRY:
                errors.append(
                    f"Unknown indicator '{ind.name}'. "
                    f"Valid: {sorted(INDICATOR_REGISTRY.keys())}."
                )
            if not ind.output_key:
                errors.append("Indicator output_key is required.")
            if ind.output_key in output_keys:
                errors.append(f"Duplicate output_key '{ind.output_key}'.")
            output_keys.add(ind.output_key)

            # Multi-output indicators expand with suffixes.
            if ind.name in MULTI_OUTPUT_INDICATORS:
                _multi_keys = _get_multi_output_keys(ind.name)
                for sub in _multi_keys:
                    output_keys.add(f"{ind.output_key}_{sub}")

        # Validate conditions.  OHLCV columns are valid operands too.
        valid_refs = output_keys | PRICE_COLUMNS
        errors.extend(self._validate_composite(self.entry_conditions, valid_refs, "entry"))
        errors.extend(self._validate_composite(self.exit_conditions, valid_refs, "exit"))

        return errors

    def _validate_composite(
        self,
        comp: CompositeCondition,
        output_keys: set[str],
        label: str,
    ) -> list[str]:
        errors: list[str] = []
        if comp.logic not in VALID_LOGIC:
            errors.append(f"{label}: invalid logic '{comp.logic}'. Must be ALL_OF or ANY_OF.")

        for cond in comp.conditions:
            errors.extend(self._validate_condition(cond, output_keys, label))

        for nested in comp.nested:
            errors.extend(self._validate_composite(nested, output_keys, label))

        return errors

    def _validate_condition(
        self,
        cond: ConditionSpec,
        output_keys: set[str],
        label: str,
    ) -> list[str]:
        errors: list[str] = []
        if cond.operator not in VALID_OPERATORS:
            errors.append(
                f"{label}: unknown operator '{cond.operator}'. "
                f"Valid: {sorted(VALID_OPERATORS)}."
            )

        # left must be an output_key or float constant.
        if not _is_float_str(cond.left) and cond.left not in output_keys:
            errors.append(
                f"{label}: condition left '{cond.left}' is not a known "
                f"output_key or numeric constant."
            )

        # right (if present) must also be valid.
        if cond.right and not _is_float_str(cond.right) and cond.right not in output_keys:
            errors.append(
                f"{label}: condition right '{cond.right}' is not a known "
                f"output_key or numeric constant."
            )

        return errors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_float_str(s: str) -> bool:
    """Return True if *s* can be parsed as a float."""
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def _get_multi_output_keys(indicator_name: str) -> list[str]:
    """Return the sub-keys for a multi-output indicator."""
    if indicator_name == "macd":
        return ["line", "signal", "histogram"]
    if indicator_name == "bollinger_bands":
        return ["upper", "middle", "lower"]
    return []
