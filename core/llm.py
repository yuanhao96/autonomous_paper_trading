"""Centralized LLM wrapper with logging, retries, and prompt template loading."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import anthropic
import yaml
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Project root is two levels up from this file (core/llm.py -> project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _load_settings() -> dict[str, Any]:
    """Load runtime settings from config/settings.yaml."""
    settings_path = _PROJECT_ROOT / "config" / "settings.yaml"
    if not settings_path.exists():
        logger.warning("settings.yaml not found at %s; using defaults", settings_path)
        return {}
    with open(settings_path, "r") as f:
        return yaml.safe_load(f) or {}


def _get_llm_settings() -> dict[str, Any]:
    """Return the llm section of settings with defaults."""
    settings = _load_settings()
    llm_conf = settings.get("llm", {})
    return {
        "model": llm_conf.get("model", "claude-sonnet-4-6"),
        "max_retries": int(llm_conf.get("max_retries", 3)),
        "retry_base_delay": float(llm_conf.get("retry_base_delay", 1.0)),
    }


def _get_log_file() -> Path:
    """Return the path to the LLM call log file."""
    settings = _load_settings()
    log_conf = settings.get("logging", {})
    rel_path = log_conf.get("llm_log_file", "logs/llm_calls.jsonl")
    return _PROJECT_ROOT / rel_path


# ---------------------------------------------------------------------------
# Client singleton
# ---------------------------------------------------------------------------

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    """Return a cached Anthropic client instance."""
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file or export it as an environment variable."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log_call(
    *,
    prompt_hash: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
) -> None:
    """Append a structured JSON line to the LLM call log."""
    log_file = _get_log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "prompt_hash": prompt_hash,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": round(latency_ms, 2),
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _hash_prompt(prompt: str) -> str:
    """Return the SHA-256 hex digest of the first 500 characters of the prompt."""
    return hashlib.sha256(prompt[:500].encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def call_llm(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
) -> str:
    """Send a request to the Anthropic API and return the assistant's text response.

    Parameters
    ----------
    prompt:
        The user message to send.
    system_prompt:
        Optional system-level instruction.
    model:
        Override the default model from settings.yaml.

    Returns
    -------
    str
        The text content of the assistant's response.

    Raises
    ------
    anthropic.APIError
        If all retries are exhausted.
    """
    llm_settings = _get_llm_settings()
    resolved_model: str = model or llm_settings["model"]
    max_retries: int = llm_settings["max_retries"]
    base_delay: float = llm_settings["retry_base_delay"]

    client = _get_client()
    prompt_hash = _hash_prompt(prompt)

    messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]

    kwargs: dict[str, Any] = {
        "model": resolved_model,
        "max_tokens": 4096,
        "messages": messages,
    }
    if system_prompt is not None:
        kwargs["system"] = system_prompt

    last_exception: Exception | None = None

    for attempt in range(max_retries):
        start_ms = time.monotonic() * 1000
        try:
            response = client.messages.create(**kwargs)
            latency_ms = time.monotonic() * 1000 - start_ms

            _log_call(
                prompt_hash=prompt_hash,
                model=resolved_model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=latency_ms,
            )

            # Extract text from the first text content block
            text_parts = [
                block.text
                for block in response.content
                if block.type == "text"
            ]
            return "\n".join(text_parts)

        except anthropic.RateLimitError as exc:
            last_exception = exc
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "Rate limited (attempt %d/%d). Retrying in %.1fs ...",
                attempt + 1,
                max_retries,
                delay,
            )
            time.sleep(delay)

        except anthropic.APIStatusError as exc:
            # Retry on transient server errors (5xx)
            if exc.status_code >= 500:
                last_exception = exc
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "Server error %d (attempt %d/%d). Retrying in %.1fs ...",
                    exc.status_code,
                    attempt + 1,
                    max_retries,
                    delay,
                )
                time.sleep(delay)
            else:
                raise

    # All retries exhausted
    raise last_exception  # type: ignore[misc]


def load_prompt_template(name: str) -> str:
    """Load a prompt template from config/prompts/<name>.

    If *name* does not include a file extension, ``.txt`` is assumed.

    Parameters
    ----------
    name:
        File name (with or without extension) inside ``config/prompts/``.

    Returns
    -------
    str
        The raw template text.

    Raises
    ------
    FileNotFoundError
        If the template file does not exist.
    """
    prompts_dir = _PROJECT_ROOT / "config" / "prompts"
    path = prompts_dir / name
    if not path.suffix:
        path = path.with_suffix(".txt")

    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")

    return path.read_text(encoding="utf-8")
