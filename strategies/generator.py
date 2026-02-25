"""LLM-driven strategy generation.

Generates ``StrategySpec`` instances by prompting the LLM with knowledge
context, past winners, and auditor feedback.  The LLM outputs JSON that
is parsed into the declarative spec schema — never raw Python.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from core.llm import call_llm, load_prompt_template
from strategies.spec import StrategySpec

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class GenerationContext:
    """Input context for strategy generation."""

    knowledge_summary: str = ""
    past_winners: list[dict] = field(default_factory=list)
    past_feedback: list[str] = field(default_factory=list)
    preferences_summary: str = ""
    exhaustion_notes: str = ""


@dataclass
class GenerationResult:
    """Output of a batch generation run."""

    specs: list[StrategySpec] = field(default_factory=list)
    raw_responses: list[str] = field(default_factory=list)
    parse_failures: int = 0


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class StrategyGenerator:
    """Generate StrategySpec instances via LLM."""

    def __init__(self, batch_size: int = 10) -> None:
        self._batch_size = batch_size

    def generate_batch(self, context: GenerationContext) -> GenerationResult:
        """Generate a batch of strategy specs.

        Calls the LLM ``batch_size`` times with increasing diversity indices.
        Each response is parsed as JSON and validated.
        """
        template = load_prompt_template("strategy_generation")
        result = GenerationResult()

        for i in range(1, self._batch_size + 1):
            prompt = template.format(
                knowledge_summary=context.knowledge_summary or "(none)",
                past_winners=json.dumps(context.past_winners[:5], indent=2)
                if context.past_winners
                else "(none)",
                past_feedback="\n".join(context.past_feedback[:10])
                if context.past_feedback
                else "(none)",
                preferences_summary=context.preferences_summary or "(default)",
                variant_index=i,
                batch_size=self._batch_size,
            )

            try:
                raw = call_llm(prompt)
                result.raw_responses.append(raw)

                spec = self._parse_response(raw)
                if spec is not None:
                    # Deduplicate names by appending variant index.
                    spec.name = f"{spec.name}_v{i}"
                    spec.metadata["variant_index"] = i
                    result.specs.append(spec)
                else:
                    result.parse_failures += 1
            except Exception:
                logger.exception("LLM call failed for variant %d", i)
                result.parse_failures += 1

        logger.info(
            "Generation batch: %d specs, %d failures out of %d attempts",
            len(result.specs),
            result.parse_failures,
            self._batch_size,
        )
        return result

    def mutate(self, spec: StrategySpec, feedback: str) -> StrategySpec | None:
        """Mutate a strategy spec based on auditor feedback."""
        template = load_prompt_template("strategy_mutation")
        prompt = template.format(
            spec_json=json.dumps(spec.to_dict(), indent=2),
            feedback=feedback,
        )

        try:
            raw = call_llm(prompt)
            return self._parse_response(raw)
        except Exception:
            logger.exception("Mutation LLM call failed")
            return None

    @staticmethod
    def _parse_response(raw: str) -> StrategySpec | None:
        """Extract a StrategySpec from an LLM response string."""
        # Try to find JSON in the response (strip markdown fences if present).
        json_str = raw.strip()
        if json_str.startswith("```"):
            json_str = re.sub(r"^```(?:json)?\s*", "", json_str)
            json_str = re.sub(r"\s*```$", "", json_str)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # Try to extract JSON object from mixed text.
            match = re.search(r"\{[\s\S]*\}", json_str)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    logger.warning("Could not parse JSON from LLM response")
                    return None
            else:
                logger.warning("No JSON found in LLM response")
                return None

        try:
            spec = StrategySpec.from_dict(data)
        except (KeyError, TypeError) as exc:
            logger.warning("Failed to construct StrategySpec from dict: %s", exc)
            return None

        errors = spec.validate()
        if errors:
            logger.warning("Generated spec failed validation: %s", errors)
            return None

        return spec
