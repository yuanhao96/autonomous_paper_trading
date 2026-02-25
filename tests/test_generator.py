"""Tests for LLM strategy generation."""

from __future__ import annotations

import json
from unittest.mock import patch

from strategies.generator import GenerationContext, StrategyGenerator
from strategies.spec import (
    CompositeCondition,
    ConditionSpec,
    IndicatorSpec,
    StrategySpec,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_spec_json() -> str:
    """Return a valid StrategySpec as a JSON string."""
    spec = StrategySpec(
        name="test_sma_rsi",
        version="0.1.0",
        description="SMA + RSI combo",
        indicators=[
            IndicatorSpec(name="sma", params={"period": 20}, output_key="sma_short"),
            IndicatorSpec(name="sma", params={"period": 50}, output_key="sma_long"),
            IndicatorSpec(name="rsi", params={"period": 14}, output_key="rsi_val"),
        ],
        entry_conditions=CompositeCondition(
            logic="ALL_OF",
            conditions=[
                ConditionSpec(operator="cross_above", left="sma_short", right="sma_long"),
                ConditionSpec(operator="less_than", left="rsi_val", right="30.0"),
            ],
        ),
        exit_conditions=CompositeCondition(
            logic="ALL_OF",
            conditions=[
                ConditionSpec(operator="cross_below", left="sma_short", right="sma_long"),
            ],
        ),
    )
    return json.dumps(spec.to_dict())


def _invalid_json() -> str:
    return "This is not valid JSON { broken"


def _valid_but_bad_spec_json() -> str:
    """Valid JSON but fails validation (unknown indicator)."""
    return json.dumps({
        "name": "bad",
        "version": "0.1.0",
        "description": "bad spec",
        "indicators": [{"name": "fake_indicator", "params": {}, "output_key": "x"}],
        "entry_conditions": {"logic": "ALL_OF", "conditions": []},
        "exit_conditions": {"logic": "ALL_OF", "conditions": []},
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestParseResponse:
    def test_valid_json(self) -> None:
        result = StrategyGenerator._parse_response(_valid_spec_json())
        assert result is not None
        assert result.name == "test_sma_rsi"

    def test_json_in_markdown_fences(self) -> None:
        raw = f"```json\n{_valid_spec_json()}\n```"
        result = StrategyGenerator._parse_response(raw)
        assert result is not None

    def test_invalid_json(self) -> None:
        result = StrategyGenerator._parse_response(_invalid_json())
        assert result is None

    def test_valid_json_invalid_spec(self) -> None:
        result = StrategyGenerator._parse_response(_valid_but_bad_spec_json())
        assert result is None  # Should fail validation.

    def test_json_embedded_in_text(self) -> None:
        raw = f"Here is the strategy:\n{_valid_spec_json()}\nDone."
        result = StrategyGenerator._parse_response(raw)
        assert result is not None


class TestGenerateBatch:
    @patch("strategies.generator.call_llm")
    @patch("strategies.generator.load_prompt_template")
    def test_all_valid(self, mock_template, mock_llm) -> None:
        mock_template.return_value = (
            "{variant_index} {batch_size} {knowledge_summary} "
            "{past_winners} {past_feedback} {preferences_summary}"
        )
        mock_llm.return_value = _valid_spec_json()

        gen = StrategyGenerator(batch_size=3)
        ctx = GenerationContext(knowledge_summary="test knowledge")
        result = gen.generate_batch(ctx)

        assert len(result.specs) == 3
        assert result.parse_failures == 0
        assert all("_v" in s.name for s in result.specs)

    @patch("strategies.generator.call_llm")
    @patch("strategies.generator.load_prompt_template")
    def test_mixed_valid_invalid(self, mock_template, mock_llm) -> None:
        mock_template.return_value = (
            "{variant_index} {batch_size} {knowledge_summary} "
            "{past_winners} {past_feedback} {preferences_summary}"
        )

        # First call returns valid, second returns invalid.
        mock_llm.side_effect = [_valid_spec_json(), _invalid_json(), _valid_spec_json()]

        gen = StrategyGenerator(batch_size=3)
        result = gen.generate_batch(GenerationContext())

        assert len(result.specs) == 2
        assert result.parse_failures == 1

    @patch("strategies.generator.call_llm")
    @patch("strategies.generator.load_prompt_template")
    def test_llm_exception_counted(self, mock_template, mock_llm) -> None:
        mock_template.return_value = (
            "{variant_index} {batch_size} {knowledge_summary} "
            "{past_winners} {past_feedback} {preferences_summary}"
        )
        mock_llm.side_effect = RuntimeError("API down")

        gen = StrategyGenerator(batch_size=2)
        result = gen.generate_batch(GenerationContext())

        assert len(result.specs) == 0
        assert result.parse_failures == 2


class TestMutate:
    @patch("strategies.generator.call_llm")
    @patch("strategies.generator.load_prompt_template")
    def test_successful_mutation(self, mock_template, mock_llm) -> None:
        mock_template.return_value = "Improve: {spec_json}\nFeedback: {feedback}"
        mock_llm.return_value = _valid_spec_json()

        gen = StrategyGenerator()
        original = StrategySpec.from_dict(json.loads(_valid_spec_json()))
        mutated = gen.mutate(original, "Use shorter lookback periods")

        assert mutated is not None

    @patch("strategies.generator.call_llm")
    @patch("strategies.generator.load_prompt_template")
    def test_failed_mutation(self, mock_template, mock_llm) -> None:
        mock_template.return_value = "{spec_json} {feedback}"
        mock_llm.return_value = _invalid_json()

        gen = StrategyGenerator()
        original = StrategySpec.from_dict(json.loads(_valid_spec_json()))
        mutated = gen.mutate(original, "feedback")

        assert mutated is None
