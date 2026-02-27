"""Tests for the LLM strategy generator.

Uses mocked LLM responses to test parsing and validation logic
without requiring an API key.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.agent.generator import (
    AVAILABLE_UNIVERSES,
    SUPPORTED_TEMPLATES,
    StrategyGenerator,
)
from src.core.llm import LLMClient
from src.strategies.spec import RiskParams, StrategyResult, StrategySpec


def _mock_llm_response(template="momentum/time-series-momentum", **kwargs):
    """Build a valid JSON response as the LLM would produce."""
    import json

    data = {
        "template": template,
        "parameters": kwargs.get("parameters", {"lookback": 126, "threshold": 0.01}),
        "universe_id": kwargs.get("universe_id", "sector_etfs"),
        "risk": {
            "max_position_pct": 0.10,
            "max_positions": 5,
            "stop_loss_pct": None,
            "position_size_method": "equal_weight",
        },
        "reasoning": "Testing momentum with moderate lookback",
    }
    data.update({k: v for k, v in kwargs.items() if k not in ("parameters", "universe_id")})
    return json.dumps(data)


@pytest.fixture
def mock_llm():
    """Create a generator with mocked LLM client."""
    client = MagicMock(spec=LLMClient)
    client.session = MagicMock()
    return client


@pytest.fixture
def generator(mock_llm):
    return StrategyGenerator(llm_client=mock_llm)


class TestStrategyGenerator:
    def test_explore_generates_spec(self, generator, mock_llm):
        mock_llm.chat_with_system.return_value = _mock_llm_response()
        spec = generator.explore()
        assert spec.template == "momentum/time-series-momentum"
        assert spec.parameters == {"lookback": 126, "threshold": 0.01}
        assert spec.created_by == "llm_explore"
        assert spec.universe_id == "sector_etfs"

    def test_exploit_generates_spec(self, generator, mock_llm):
        mock_llm.chat_with_system.return_value = _mock_llm_response(
            template="momentum/time-series-momentum",
            parameters={"lookback": 200, "threshold": 0.02},
        )
        parent = StrategySpec(
            template="momentum/time-series-momentum",
            parameters={"lookback": 126, "threshold": 0.01},
            universe_id="sector_etfs",
            risk=RiskParams(max_position_pct=0.10, max_positions=5),
        )
        parent_result = StrategyResult(spec_id=parent.id, phase="screen", sharpe_ratio=0.8)

        spec = generator.exploit(parent_spec=parent, screen_result=parent_result)
        assert spec.created_by == "llm_exploit"
        assert spec.parent_id == parent.id
        assert spec.generation == 1

    def test_parse_json_with_markdown_blocks(self, generator, mock_llm):
        """LLM often wraps JSON in ```json blocks."""
        mock_llm.chat_with_system.return_value = (
            "```json\n" + _mock_llm_response() + "\n```"
        )
        spec = generator.explore()
        assert spec.template == "momentum/time-series-momentum"

    def test_parse_json_with_extra_text(self, generator, mock_llm):
        """LLM sometimes adds explanation before/after JSON."""
        mock_llm.chat_with_system.return_value = (
            "Here is my recommendation:\n" + _mock_llm_response() + "\nThis should work well."
        )
        spec = generator.explore()
        assert spec.template == "momentum/time-series-momentum"

    def test_unknown_template_corrected(self, generator, mock_llm):
        """Unknown template should be corrected to closest match."""
        mock_llm.chat_with_system.return_value = _mock_llm_response(
            template="momentum/some-unknown-strategy"
        )
        spec = generator.explore()
        # Should fall back to a supported template
        assert spec.template in SUPPORTED_TEMPLATES

    def test_unknown_universe_corrected(self, generator, mock_llm):
        mock_llm.chat_with_system.return_value = _mock_llm_response(
            universe_id="unknown_universe"
        )
        spec = generator.explore()
        assert spec.universe_id == "sector_etfs"  # fallback

    def test_risk_params_clamped(self, generator, mock_llm):
        """Risk params should be clamped to safe limits."""
        import json
        data = {
            "template": "momentum/time-series-momentum",
            "parameters": {"lookback": 126},
            "universe_id": "sector_etfs",
            "risk": {
                "max_position_pct": 0.50,  # Too high — should be clamped to 0.10
                "max_positions": 100,       # Too high — should be clamped to 20
                "position_size_method": "equal_weight",
            },
        }
        mock_llm.chat_with_system.return_value = json.dumps(data)
        spec = generator.explore()
        assert spec.risk.max_position_pct <= 0.10
        assert spec.risk.max_positions <= 20

    def test_invalid_json_raises(self, generator, mock_llm):
        mock_llm.chat_with_system.return_value = "This is not JSON at all"
        with pytest.raises(ValueError, match="No JSON"):
            generator.explore()

    def test_malformed_json_raises(self, generator, mock_llm):
        mock_llm.chat_with_system.return_value = '{"template": "broken}'
        with pytest.raises(ValueError, match="Invalid JSON"):
            generator.explore()

    def test_explore_with_history(self, generator, mock_llm):
        """History should be passed to the LLM for context."""
        mock_llm.chat_with_system.return_value = _mock_llm_response(
            template="technical/breakout"
        )
        history = [
            (
                StrategySpec(
                    template="momentum/time-series-momentum",
                    parameters={"lookback": 126},
                    universe_id="sector_etfs",
                ),
                StrategyResult(spec_id="old", phase="screen", sharpe_ratio=0.5),
            )
        ]
        spec = generator.explore(history=history)
        # Verify LLM was called with history context
        call_args = mock_llm.chat_with_system.call_args
        user_msg = call_args[0][1]
        assert "EVOLUTION HISTORY" in user_msg

    def test_exploit_includes_diagnostics(self, generator, mock_llm):
        mock_llm.chat_with_system.return_value = _mock_llm_response()
        parent = StrategySpec(
            template="momentum/time-series-momentum",
            parameters={"lookback": 126},
            universe_id="sector_etfs",
        )
        screen = StrategyResult(
            spec_id=parent.id, phase="screen",
            sharpe_ratio=0.8, failure_reason="min_trades",
        )
        generator.exploit(parent_spec=parent, screen_result=screen)
        call_args = mock_llm.chat_with_system.call_args
        user_msg = call_args[0][1]
        assert "SCREENING RESULT" in user_msg
        assert "min_trades" in user_msg


class TestSupportedTemplates:
    def test_all_templates_valid_format(self):
        for t in SUPPORTED_TEMPLATES:
            assert "/" in t, f"Template {t} should have category/slug format"

    def test_universes_available(self):
        assert len(AVAILABLE_UNIVERSES) > 0
        assert "sector_etfs" in AVAILABLE_UNIVERSES
