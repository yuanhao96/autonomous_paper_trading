"""LLM client — supports OpenAI (default) and Anthropic providers.

Configurable via settings.yaml:
  llm.provider: "openai" or "anthropic"
  llm.model: model name (provider-specific)
  llm.max_tokens: max response tokens
  llm.temperature: sampling temperature

API keys via environment variable or .env file:
  OpenAI:    OPENAI_API_KEY
  Anthropic: ANTHROPIC_API_KEY
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field

from src.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class LLMUsage:
    """Token usage tracking for a single call."""

    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    duration_seconds: float = 0.0


@dataclass
class LLMSession:
    """Cumulative usage tracking across multiple calls."""

    calls: list[LLMUsage] = field(default_factory=list)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def total_calls(self) -> int:
        return len(self.calls)

    def summary(self) -> str:
        return (
            f"LLM Session: {self.total_calls} calls, "
            f"{self.total_input_tokens:,} in / {self.total_output_tokens:,} out tokens"
        )


def _load_env_key(key_name: str) -> str | None:
    """Load an API key from environment or .env file."""
    value = os.environ.get(key_name)
    if not value:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            value = os.environ.get(key_name)
        except ImportError:
            pass
    return value


class LLMClient:
    """Unified LLM client supporting OpenAI and Anthropic.

    Provider is selected via settings.yaml `llm.provider` (default: "openai").

    Usage:
        client = LLMClient()
        response = client.chat("What is momentum investing?")
        response = client.chat_with_system("system prompt", "user message")
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._provider = self._settings.get("llm.provider", "openai")
        self._model = self._settings.get("llm.model", self._default_model())
        self._max_tokens = self._settings.get("llm.max_tokens", 4096)
        self._temperature = self._settings.get("llm.temperature", 0.7)
        self._session = LLMSession()
        self._client = None

    def _default_model(self) -> str:
        if self._provider == "anthropic":
            return "claude-sonnet-4-20250514"
        return "gpt-5"

    def _get_client(self):
        """Lazy-init the provider client."""
        if self._client is not None:
            return self._client

        if self._provider == "openai":
            self._client = self._init_openai()
        elif self._provider == "anthropic":
            self._client = self._init_anthropic()
        else:
            raise ValueError(f"Unknown LLM provider: {self._provider}. Use 'openai' or 'anthropic'.")
        return self._client

    def _init_openai(self):
        import openai

        api_key = _load_env_key("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set. Set it via environment variable or .env file."
            )
        return openai.OpenAI(api_key=api_key)

    def _init_anthropic(self):
        import anthropic

        api_key = _load_env_key("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. Set it via environment variable or .env file."
            )
        return anthropic.Anthropic(api_key=api_key)

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    @property
    def session(self) -> LLMSession:
        return self._session

    def chat(
        self,
        user_message: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a simple user message and get a text response."""
        return self.chat_with_system("", user_message, temperature=temperature, max_tokens=max_tokens)

    def chat_with_system(
        self,
        system_prompt: str,
        user_message: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a message with system prompt and get a text response.

        Args:
            system_prompt: System instruction (empty string = no system prompt).
            user_message: User message content.
            temperature: Override default temperature.
            max_tokens: Override default max_tokens.

        Returns:
            The assistant's text response.
        """
        client = self._get_client()
        temp = temperature if temperature is not None else self._temperature
        tokens = max_tokens or self._max_tokens

        t0 = time.time()
        max_retries = 3
        last_err = None

        for attempt in range(max_retries):
            try:
                if self._provider == "openai":
                    text, usage = self._call_openai(client, system_prompt, user_message, temp, tokens)
                else:
                    text, usage = self._call_anthropic(client, system_prompt, user_message, temp, tokens)

                usage.duration_seconds = time.time() - t0
                self._session.calls.append(usage)

                logger.info(
                    "LLM call (%s/%s): %d in / %d out tokens, %.1fs",
                    self._provider, self._model,
                    usage.input_tokens, usage.output_tokens, usage.duration_seconds,
                )
                return text

            except Exception as e:
                last_err = e
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "LLM call failed (attempt %d/%d): %s. Retrying in %ds...",
                        attempt + 1, max_retries, e, wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error("LLM call failed after %d attempts: %s", max_retries, e)

        raise RuntimeError(f"LLM call failed after {max_retries} attempts: {last_err}")

    def _call_openai(self, client, system_prompt: str, user_message: str,
                     temperature: float, max_tokens: int) -> tuple[str, LLMUsage]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = response.choices[0].message.content
        usage = LLMUsage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            model=self._model,
        )
        return text, usage

    def _call_anthropic(self, client, system_prompt: str, user_message: str,
                        temperature: float, max_tokens: int) -> tuple[str, LLMUsage]:
        kwargs = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": user_message}],
            "temperature": temperature,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = client.messages.create(**kwargs)
        text = response.content[0].text
        usage = LLMUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self._model,
        )
        return text, usage
