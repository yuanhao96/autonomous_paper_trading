"""Centralized LLM wrapper with logging, retries, and prompt template loading.

Uses Kimi Code API (https://api.kimi.com/coding/) via the Anthropic-compatible
SDK. Set KIMI_CODE_API_KEY and optionally KIMI_CODE_BASE_URL in .env.
"""

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

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

KIMI_CODE_BASE_URL = "https://api.kimi.com/coding/"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _load_settings() -> dict[str, Any]:
    settings_path = _PROJECT_ROOT / "config" / "settings.yaml"
    if not settings_path.exists():
        return {}
    with open(settings_path, "r") as f:
        return yaml.safe_load(f) or {}


def _get_llm_settings() -> dict[str, Any]:
    settings = _load_settings()
    llm_conf = settings.get("llm", {})
    return {
        "model": llm_conf.get("model", "claude-sonnet-4-5"),
        "max_retries": int(llm_conf.get("max_retries", 3)),
        "retry_base_delay": float(llm_conf.get("retry_base_delay", 1.0)),
    }


def _get_log_file() -> Path:
    settings = _load_settings()
    log_conf = settings.get("logging", {})
    rel_path = log_conf.get("llm_log_file", "logs/llm_calls.jsonl")
    return _PROJECT_ROOT / rel_path


# ---------------------------------------------------------------------------
# Client singleton
# ---------------------------------------------------------------------------

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("KIMI_CODE_API_KEY")
        if api_key:
            base_url = os.getenv("KIMI_CODE_BASE_URL", KIMI_CODE_BASE_URL)
            _client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
            logger.info("Using Kimi Code API")
        else:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise EnvironmentError(
                    "No LLM API key found. Set KIMI_CODE_API_KEY or "
                    "ANTHROPIC_API_KEY in your .env file."
                )
            _client = anthropic.Anthropic(api_key=api_key)
            logger.info("Using Anthropic API")
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
    return hashlib.sha256(prompt[:500].encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def call_llm(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
) -> str:
    """Send a request to Kimi Code API and return the assistant's text.

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
    """
    llm_settings = _get_llm_settings()
    resolved_model: str = model or llm_settings["model"]
    max_retries: int = llm_settings["max_retries"]
    base_delay: float = llm_settings["retry_base_delay"]

    client = _get_client()
    prompt_hash = _hash_prompt(prompt)

    kwargs: dict[str, Any] = {
        "model": resolved_model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_prompt:
        kwargs["system"] = system_prompt

    last_exception: Exception | None = None

    for attempt in range(max_retries):
        start_ms = time.monotonic() * 1000
        try:
            response = client.messages.create(**kwargs)
            latency_ms = time.monotonic() * 1000 - start_ms

            usage = response.usage
            _log_call(
                prompt_hash=prompt_hash,
                model=resolved_model,
                input_tokens=usage.input_tokens if usage else 0,
                output_tokens=usage.output_tokens if usage else 0,
                latency_ms=latency_ms,
            )

            return response.content[0].text if response.content else ""

        except anthropic.RateLimitError as exc:
            last_exception = exc
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "Rate limited (attempt %d/%d). Retrying in %.1fs ...",
                attempt + 1, max_retries, delay,
            )
            time.sleep(delay)

        except anthropic.APIStatusError as exc:
            if exc.status_code >= 500:
                last_exception = exc
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "Server error %d (attempt %d/%d). Retrying in %.1fs ...",
                    exc.status_code, attempt + 1, max_retries, delay,
                )
                time.sleep(delay)
            else:
                raise

    raise last_exception  # type: ignore[misc]


def load_prompt_template(name: str) -> str:
    """Load a prompt template from config/prompts/<name>."""
    prompts_dir = _PROJECT_ROOT / "config" / "prompts"
    path = prompts_dir / name
    if not path.suffix:
        path = path.with_suffix(".txt")
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")
