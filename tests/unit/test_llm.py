"""Tests for LLM client wrapper."""

from unittest.mock import MagicMock

import pytest

from src.core.llm import LLMClient, LLMSession, LLMUsage


class TestLLMUsage:
    def test_usage_defaults(self):
        u = LLMUsage()
        assert u.input_tokens == 0
        assert u.output_tokens == 0
        assert u.model == ""

    def test_usage_values(self):
        u = LLMUsage(input_tokens=100, output_tokens=50, model="gpt-4o")
        assert u.input_tokens == 100
        assert u.output_tokens == 50


class TestLLMSession:
    def test_empty_session(self):
        s = LLMSession()
        assert s.total_calls == 0
        assert s.total_input_tokens == 0
        assert s.total_output_tokens == 0

    def test_session_tracking(self):
        s = LLMSession()
        s.calls.append(LLMUsage(input_tokens=100, output_tokens=50))
        s.calls.append(LLMUsage(input_tokens=200, output_tokens=80))
        assert s.total_calls == 2
        assert s.total_input_tokens == 300
        assert s.total_output_tokens == 130

    def test_session_summary(self):
        s = LLMSession()
        s.calls.append(LLMUsage(input_tokens=100, output_tokens=50))
        summary = s.summary()
        assert "1 calls" in summary
        assert "100" in summary


class TestLLMClient:
    def test_client_init_with_explicit_provider(self):
        settings = MagicMock()
        settings.get.side_effect = lambda key, default=None: {
            "llm.provider": "anthropic",
            "llm.model": "claude-sonnet-4-20250514",
            "llm.max_tokens": 4096,
            "llm.temperature": 0.7,
        }.get(key, default)
        client = LLMClient(settings=settings)
        assert client.provider == "anthropic"
        assert client.model == "claude-sonnet-4-20250514"
        assert client.session.total_calls == 0

    def test_anthropic_no_api_key_raises_default(self, monkeypatch):
        """Without ANTHROPIC_API_KEY, Anthropic provider should raise RuntimeError."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr("src.core.llm._load_env_key", lambda key: None)
        settings = MagicMock()
        settings.get.side_effect = lambda key, default=None: {
            "llm.provider": "anthropic",
            "llm.model": "claude-sonnet-4-20250514",
            "llm.max_tokens": 4096,
            "llm.temperature": 0.7,
        }.get(key, default)
        client = LLMClient(settings=settings)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            client.chat("test")

    def test_anthropic_no_api_key_raises(self, monkeypatch):
        """Without ANTHROPIC_API_KEY, Anthropic provider should raise."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # Create settings mock that returns anthropic provider
        settings = MagicMock()
        settings.get.side_effect = lambda key, default=None: {
            "llm.provider": "anthropic",
            "llm.model": "claude-sonnet-4-20250514",
            "llm.max_tokens": 4096,
            "llm.temperature": 0.7,
        }.get(key, default)
        client = LLMClient(settings=settings)
        assert client.provider == "anthropic"
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            client.chat("test")

    def test_unknown_provider_raises(self):
        settings = MagicMock()
        settings.get.side_effect = lambda key, default=None: {
            "llm.provider": "unknown_provider",
            "llm.model": "some-model",
            "llm.max_tokens": 4096,
            "llm.temperature": 0.7,
        }.get(key, default)
        client = LLMClient(settings=settings)
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            client.chat("test")

    def test_default_model_per_provider(self):
        # Anthropic default
        settings_ant = MagicMock()
        settings_ant.get.side_effect = lambda key, default=None: {
            "llm.provider": "anthropic",
            "llm.max_tokens": 4096,
            "llm.temperature": 0.7,
        }.get(key, default)
        client_ant = LLMClient(settings=settings_ant)
        assert client_ant.provider == "anthropic"
        assert client_ant.model == "claude-sonnet-4-20250514"

        # OpenAI default
        settings_oai = MagicMock()
        settings_oai.get.side_effect = lambda key, default=None: {
            "llm.provider": "openai",
            "llm.max_tokens": 4096,
            "llm.temperature": 0.7,
        }.get(key, default)
        client_oai = LLMClient(settings=settings_oai)
        assert client_oai.provider == "openai"
        assert client_oai.model == "gpt-4o"
