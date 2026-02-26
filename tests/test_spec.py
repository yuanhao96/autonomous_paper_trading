"""Tests for the declarative strategy spec schema."""

from __future__ import annotations

from strategies.spec import (
    CompositeCondition,
    ConditionSpec,
    IndicatorSpec,
    RiskParams,
    StrategySpec,
)


def _make_sma_crossover_spec() -> StrategySpec:
    """Build a minimal SMA crossover spec for testing."""
    return StrategySpec(
        name="sma_crossover_template",
        version="1.0.0",
        description="SMA crossover via template",
        indicators=[
            IndicatorSpec(name="sma", params={"period": 20}, output_key="sma_short"),
            IndicatorSpec(name="sma", params={"period": 50}, output_key="sma_long"),
        ],
        entry_conditions=CompositeCondition(
            logic="ALL_OF",
            conditions=[
                ConditionSpec(operator="cross_above", left="sma_short", right="sma_long"),
            ],
        ),
        exit_conditions=CompositeCondition(
            logic="ALL_OF",
            conditions=[
                ConditionSpec(operator="cross_below", left="sma_short", right="sma_long"),
            ],
        ),
    )


class TestRoundTrip:
    def test_to_dict_from_dict(self) -> None:
        spec = _make_sma_crossover_spec()
        d = spec.to_dict()
        restored = StrategySpec.from_dict(d)

        assert restored.name == spec.name
        assert restored.version == spec.version
        assert len(restored.indicators) == 2
        assert restored.indicators[0].name == "sma"
        assert restored.entry_conditions.logic == "ALL_OF"
        assert len(restored.entry_conditions.conditions) == 1
        assert restored.entry_conditions.conditions[0].operator == "cross_above"

    def test_nested_composite_round_trip(self) -> None:
        spec = StrategySpec(
            name="nested_test",
            version="0.1.0",
            description="test nested composites",
            indicators=[
                IndicatorSpec(name="rsi", params={"period": 14}, output_key="rsi_val"),
                IndicatorSpec(name="sma", params={"period": 20}, output_key="sma_val"),
            ],
            entry_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(operator="less_than", left="rsi_val", right="30.0"),
                ],
                nested=[
                    CompositeCondition(
                        logic="ANY_OF",
                        conditions=[
                            ConditionSpec(operator="greater_than", left="sma_val", right="100.0"),
                        ],
                    ),
                ],
            ),
            exit_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(operator="greater_than", left="rsi_val", right="70.0"),
                ],
            ),
        )
        d = spec.to_dict()
        restored = StrategySpec.from_dict(d)

        assert len(restored.entry_conditions.nested) == 1
        assert restored.entry_conditions.nested[0].logic == "ANY_OF"

    def test_risk_params_round_trip(self) -> None:
        risk = RiskParams(stop_loss_pct=3.0, take_profit_pct=8.0, max_positions=10)
        d = risk.to_dict()
        restored = RiskParams.from_dict(d)
        assert restored.stop_loss_pct == 3.0
        assert restored.max_positions == 10

    def test_metadata_preserved(self) -> None:
        spec = _make_sma_crossover_spec()
        spec.metadata = {"source": "llm", "cycle": 5}
        d = spec.to_dict()
        restored = StrategySpec.from_dict(d)
        assert restored.metadata["source"] == "llm"
        assert restored.metadata["cycle"] == 5


class TestValidation:
    def test_valid_spec_no_errors(self) -> None:
        spec = _make_sma_crossover_spec()
        errors = spec.validate()
        assert errors == []

    def test_empty_name(self) -> None:
        spec = _make_sma_crossover_spec()
        spec.name = ""
        errors = spec.validate()
        assert any("name" in e.lower() for e in errors)

    def test_unknown_indicator(self) -> None:
        spec = _make_sma_crossover_spec()
        spec.indicators.append(
            IndicatorSpec(name="unknown_ind", params={}, output_key="bad")
        )
        errors = spec.validate()
        assert any("unknown_ind" in e for e in errors)

    def test_duplicate_output_key(self) -> None:
        spec = _make_sma_crossover_spec()
        spec.indicators[1] = IndicatorSpec(
            name="sma", params={"period": 50}, output_key="sma_short"
        )
        errors = spec.validate()
        assert any("duplicate" in e.lower() for e in errors)

    def test_unknown_operator(self) -> None:
        spec = _make_sma_crossover_spec()
        spec.entry_conditions.conditions[0].operator = "magic_cross"
        errors = spec.validate()
        assert any("magic_cross" in e for e in errors)

    def test_invalid_left_reference(self) -> None:
        spec = _make_sma_crossover_spec()
        spec.entry_conditions.conditions[0].left = "nonexistent_key"
        errors = spec.validate()
        assert any("nonexistent_key" in e for e in errors)

    def test_float_constant_accepted(self) -> None:
        spec = StrategySpec(
            name="const_test",
            version="0.1.0",
            description="test float constants",
            indicators=[
                IndicatorSpec(name="rsi", params={"period": 14}, output_key="rsi_val"),
            ],
            entry_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(operator="less_than", left="rsi_val", right="30.0"),
                ],
            ),
            exit_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(operator="greater_than", left="rsi_val", right="70.0"),
                ],
            ),
        )
        errors = spec.validate()
        assert errors == []

    def test_multi_output_expanded_keys(self) -> None:
        """MACD sub-keys (macd_val_line, etc.) should be accepted in conditions."""
        spec = StrategySpec(
            name="macd_test",
            version="0.1.0",
            description="test multi-output",
            indicators=[
                IndicatorSpec(name="macd", params={}, output_key="macd_val"),
            ],
            entry_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(
                        operator="cross_above",
                        left="macd_val_line",
                        right="macd_val_signal",
                    ),
                ],
            ),
            exit_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(
                        operator="cross_below",
                        left="macd_val_line",
                        right="macd_val_signal",
                    ),
                ],
            ),
        )
        errors = spec.validate()
        assert errors == []

    def test_ohlcv_columns_accepted_in_conditions(self) -> None:
        """Price columns (Close, Open, etc.) should be valid condition operands."""
        spec = StrategySpec(
            name="price_ref_test",
            version="0.1.0",
            description="test OHLCV column references",
            indicators=[
                IndicatorSpec(name="sma", params={"period": 20}, output_key="sma_val"),
                IndicatorSpec(
                    name="bollinger_bands", params={"period": 20}, output_key="bb",
                ),
            ],
            entry_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(
                        operator="greater_than", left="Close", right="sma_val",
                    ),
                    ConditionSpec(
                        operator="less_than", left="Close", right="bb_upper",
                    ),
                ],
            ),
            exit_conditions=CompositeCondition(
                logic="ALL_OF",
                conditions=[
                    ConditionSpec(
                        operator="less_than", left="Close", right="sma_val",
                    ),
                ],
            ),
        )
        errors = spec.validate()
        assert errors == []

    def test_all_ohlcv_columns_accepted(self) -> None:
        """All 5 OHLCV columns should pass validation."""
        for col in ("Open", "High", "Low", "Close", "Volume"):
            spec = StrategySpec(
                name=f"{col.lower()}_test",
                version="0.1.0",
                description=f"test {col} reference",
                indicators=[
                    IndicatorSpec(name="sma", params={"period": 20}, output_key="sma_val"),
                ],
                entry_conditions=CompositeCondition(
                    logic="ALL_OF",
                    conditions=[
                        ConditionSpec(
                            operator="greater_than", left=col, right="sma_val",
                        ),
                    ],
                ),
                exit_conditions=CompositeCondition(
                    logic="ALL_OF",
                    conditions=[
                        ConditionSpec(
                            operator="less_than", left=col, right="sma_val",
                        ),
                    ],
                ),
            )
            errors = spec.validate()
            assert errors == [], f"{col} should be accepted but got: {errors}"

    def test_invalid_logic(self) -> None:
        spec = _make_sma_crossover_spec()
        spec.entry_conditions.logic = "SOME_OF"
        errors = spec.validate()
        assert any("SOME_OF" in e for e in errors)
