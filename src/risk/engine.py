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

    def check_leverage(self, total_exposure: float, equity: float) -> list[RiskViolation]:
        """Check if leverage exceeds the max_leverage limit.

        Args:
            total_exposure: Sum of absolute position values.
            equity: Current account equity.
        """
        violations: list[RiskViolation] = []
        if equity <= 0:
            return violations
        leverage = total_exposure / equity
        if leverage > self._limits.max_leverage:
            violations.append(RiskViolation(
                rule="max_leverage",
                limit=self._limits.max_leverage,
                actual=round(leverage, 2),
                message=(
                    f"Leverage {leverage:.2f}x exceeds "
                    f"limit {self._limits.max_leverage:.2f}x"
                ),
            ))
        return violations

    def check_cash_reserve(self, cash: float, equity: float) -> list[RiskViolation]:
        """Check if cash reserve falls below min_cash_reserve_pct.

        Args:
            cash: Current cash balance.
            equity: Current account equity (cash + positions).
        """
        violations: list[RiskViolation] = []
        if equity <= 0:
            return violations
        cash_pct = cash / equity
        if cash_pct < self._limits.min_cash_reserve_pct:
            violations.append(RiskViolation(
                rule="min_cash_reserve_pct",
                limit=self._limits.min_cash_reserve_pct,
                actual=round(cash_pct, 4),
                message=(
                    f"Cash reserve {cash_pct:.1%} below "
                    f"minimum {self._limits.min_cash_reserve_pct:.1%}"
                ),
            ))
        return violations

    def check_asset_class(self, asset_class: str) -> list[RiskViolation]:
        """Check if an asset class is in the allowed list."""
        violations: list[RiskViolation] = []
        if not self.is_asset_class_allowed(asset_class):
            violations.append(RiskViolation(
                rule="allowed_asset_classes",
                limit=", ".join(self._prefs.allowed_asset_classes),
                actual=asset_class,
                message=(
                    f"Asset class '{asset_class}' not in allowed list: "
                    f"{self._prefs.allowed_asset_classes}"
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
