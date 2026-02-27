"""Risk engine — enforces hard limits from preferences.yaml at runtime."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.config import Preferences, RiskLimits, load_preferences
from src.strategies.spec import RiskParams, StrategySpec


@dataclass
class RiskViolation:
    """A single risk limit violation."""

    rule: str
    limit: float | int | str
    actual: float | int | str
    message: str


class RiskEngine:
    """Enforces immutable risk limits from preferences.yaml.

    This engine is a hard safety layer — it cannot be overridden by
    the LLM or runtime configuration. Every strategy must pass risk
    checks before screening, validation, or live deployment.
    """

    def __init__(self, preferences: Preferences | None = None) -> None:
        self._prefs = preferences or load_preferences()
        self._limits = self._prefs.risk_limits

    @property
    def limits(self) -> RiskLimits:
        return self._limits

    def check_spec(self, spec: StrategySpec) -> list[RiskViolation]:
        """Validate a StrategySpec against risk limits.

        Returns empty list if all checks pass.
        """
        violations: list[RiskViolation] = []

        # Position size check
        if spec.risk.max_position_pct > self._limits.max_position_pct:
            violations.append(RiskViolation(
                rule="max_position_pct",
                limit=self._limits.max_position_pct,
                actual=spec.risk.max_position_pct,
                message=(
                    f"Position size {spec.risk.max_position_pct:.1%} exceeds "
                    f"limit {self._limits.max_position_pct:.1%}"
                ),
            ))

        # Max positions check
        if spec.risk.max_positions > self._limits.max_positions:
            violations.append(RiskViolation(
                rule="max_positions",
                limit=self._limits.max_positions,
                actual=spec.risk.max_positions,
                message=(
                    f"Max positions {spec.risk.max_positions} exceeds "
                    f"limit {self._limits.max_positions}"
                ),
            ))

        return violations

    def check_result_drawdown(self, max_drawdown: float) -> list[RiskViolation]:
        """Check if a backtest result's drawdown exceeds limits."""
        violations: list[RiskViolation] = []
        if abs(max_drawdown) > self._limits.max_portfolio_drawdown:
            violations.append(RiskViolation(
                rule="max_portfolio_drawdown",
                limit=self._limits.max_portfolio_drawdown,
                actual=abs(max_drawdown),
                message=(
                    f"Max drawdown {abs(max_drawdown):.1%} exceeds "
                    f"limit {self._limits.max_portfolio_drawdown:.1%}"
                ),
            ))
        return violations

    def clamp_spec(self, spec: StrategySpec) -> StrategySpec:
        """Return a new spec with risk params clamped to limits.

        Does not modify the original spec.
        """
        clamped_risk = RiskParams(
            stop_loss_pct=spec.risk.stop_loss_pct,
            take_profit_pct=spec.risk.take_profit_pct,
            trailing_stop_pct=spec.risk.trailing_stop_pct,
            max_position_pct=min(spec.risk.max_position_pct, self._limits.max_position_pct),
            max_positions=min(spec.risk.max_positions, self._limits.max_positions),
            position_size_method=spec.risk.position_size_method,
        )
        return StrategySpec(
            id=spec.id,
            name=spec.name,
            template=spec.template,
            version=spec.version,
            parameters=spec.parameters,
            universe_id=spec.universe_id,
            risk=clamped_risk,
            combination=spec.combination,
            combination_method=spec.combination_method,
            parent_id=spec.parent_id,
            generation=spec.generation,
            created_at=spec.created_at,
            created_by=spec.created_by,
        )

    def is_asset_class_allowed(self, asset_class: str) -> bool:
        """Check if an asset class is allowed by preferences."""
        return asset_class in self._prefs.allowed_asset_classes
